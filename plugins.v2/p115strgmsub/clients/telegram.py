"""
Telegram 频道搜索客户端
支持 HTTP 抓取公开频道和 MTProto 搜索全量历史消息两种模式
"""
import asyncio
import json
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional, Tuple

from app.core.config import settings
from app.log import logger

from ..utils.message_parser import MessageParser


class TelegramClient:
    """双模式 Telegram 客户端"""

    # HTTP 抓取相关常量
    _TELEGRAM_WEB_BASE = "https://t.me/s"
    _HTTP_FETCH_LIMIT = 500
    _REQUEST_TIMEOUT = 30

    def __init__(
        self,
        channels: List[str],
        mode: str = "http",
        api_id: str = "",
        api_hash: str = "",
        session_file: str = "",
        proxy=None,
        db_path: str = "",
    ):
        """
        初始化 Telegram 客户端

        :param channels: 频道名列表
        :param mode: 搜索模式 "http" 或 "mtproto"
        :param api_id: Telegram API ID (MTProto 模式)
        :param api_hash: Telegram API Hash (MTProto 模式)
        :param session_file: Telethon session 文件路径 (MTProto 模式)
        :param proxy: 代理配置
        :param db_path: SQLite 数据库路径，为空则使用默认路径
        """
        self._channels = channels
        self._mode = mode
        self._api_id = api_id
        self._api_hash = api_hash
        self._session_file = session_file
        self._api_call_count = 0
        self._db_lock = Lock()

        # 代理配置（httpx 使用单个 URL 字符串）
        self._proxy = proxy if isinstance(proxy, str) else (proxy.get("http") or proxy.get("https")) if isinstance(proxy, dict) else None

        # 初始化 SQLite
        if not db_path:
            # 使用 MoviePilot 配置目录或临时目录
            base = getattr(settings, 'CONFIG_PATH', None) or getattr(settings, 'TEMP_PATH', None) or Path("/tmp")
            db_path = str(Path(base) / "plugins" / "p115strgmsub_tg.db")
        self._db_path = db_path
        self._init_db()

    # ------------------------------------------------------------------
    # SQLite 管理
    # ------------------------------------------------------------------

    def _init_db(self):
        """初始化 SQLite 数据库和表结构"""
        try:
            # 确保目录存在
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self._db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tg_messages (
                    channel_name TEXT NOT NULL,
                    message_id   INTEGER NOT NULL,
                    text         TEXT,
                    date         TEXT,
                    urls         TEXT,
                    PRIMARY KEY (channel_name, message_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tg_text ON tg_messages(text)
            """)
            conn.commit()
            conn.close()
            logger.info(f"Telegram SQLite 数据库初始化完成: {self._db_path}")
        except Exception as e:
            logger.error(f"Telegram SQLite 初始化失败: {e}")

    def _get_db(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _get_max_message_id(self, channel: str) -> int:
        """获取频道中已索引的最大 message_id"""
        try:
            conn = self._get_db()
            row = conn.execute(
                "SELECT MAX(message_id) FROM tg_messages WHERE channel_name = ?",
                (channel,)
            ).fetchone()
            conn.close()
            return row[0] if row and row[0] else 0
        except Exception:
            return 0

    def _store_messages(self, channel: str, messages: List[dict]):
        """
        批量存储消息到 SQLite

        :param channel: 频道名
        :param messages: 消息列表 [{"message_id": ..., "text": ..., "date": ..., "urls": [...]}]
        """
        if not messages:
            return

        with self._db_lock:
            try:
                conn = self._get_db()
                conn.executemany(
                    """INSERT OR IGNORE INTO tg_messages (channel_name, message_id, text, date, urls)
                       VALUES (?, ?, ?, ?, ?)""",
                    [
                        (
                            channel,
                            msg["message_id"],
                            msg.get("text", ""),
                            msg.get("date", ""),
                            json.dumps(msg.get("urls", []), ensure_ascii=False),
                        )
                        for msg in messages
                    ]
                )
                conn.commit()
                conn.close()
            except Exception as e:
                logger.error(f"存储 Telegram 消息失败 ({channel}): {e}")

    # ------------------------------------------------------------------
    # 统一搜索接口
    # ------------------------------------------------------------------

    async def search(self, keyword: str, channels: List[str] = None) -> List[Dict]:
        """
        统一搜索接口

        :param keyword: 搜索关键词
        :param channels: 指定搜索频道列表，为空则使用默认列表
        :return: [{"url": ..., "title": ..., "update_time": ..., "channel": ..., "raw_text": ...}]
        """
        self._api_call_count += 1
        target_channels = channels or self._channels

        if self._mode == "mtproto" and self._api_id and self._api_hash:
            return await self._search_mtproto(keyword, target_channels)
        else:
            return await self._search_http(keyword, target_channels)

    async def _search_http(self, keyword: str, channels: List[str]) -> List[Dict]:
        """
        HTTP 模式搜索：先增量抓取频道消息存入 SQLite，再本地关键词搜索

        :param keyword: 搜索关键词
        :param channels: 频道列表
        :return: 搜索结果
        """
        results = []

        for channel in channels:
            try:
                # 增量抓取最新消息
                await self._fetch_channel_messages_http(channel)
            except Exception as e:
                logger.warning(f"HTTP 抓取频道 {channel} 失败: {e}，尝试使用已缓存数据")

        # 本地搜索
        results = await self._search_local_index(keyword, channels)
        return results

    async def _fetch_channel_messages_http(self, channel: str, limit: int = 0) -> List[dict]:
        """
        通过 t.me/s/<channel> 抓取公开频道消息，增量获取

        :param channel: 频道名
        :param limit: 最大抓取消息数，0 表示使用默认值
        :return: 抓取的消息列表
        """
        import httpx
        from bs4 import BeautifulSoup

        if limit <= 0:
            limit = self._HTTP_FETCH_LIMIT

        max_existing_id = self._get_max_message_id(channel)
        url = f"{self._TELEGRAM_WEB_BASE}/{channel}"
        all_messages = []
        before_id = 0  # 用于分页

        try:
            headers = {
                "User-Agent": getattr(settings, 'USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            }

            async with httpx.AsyncClient(
                proxy=self._proxy,
                timeout=self._REQUEST_TIMEOUT,
                follow_redirects=True,
            ) as client:
                page = 1
                max_pages = 5  # 最多翻5页，每页约20条

                while page <= max_pages:
                    page_url = url
                    if before_id > 0:
                        page_url = f"{url}?before={before_id}"

                    try:
                        resp = await client.get(page_url, headers=headers)
                        resp.raise_for_status()
                    except Exception as e:
                        logger.warning(f"HTTP 请求失败 {page_url}: {e}")
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    message_divs = soup.select(".tgme_widget_message_wrap")

                    if not message_divs:
                        break

                    page_messages = []
                    for div in message_divs:
                        try:
                            msg = self._parse_message_div(div, channel)
                            if msg:
                                page_messages.append(msg)
                        except Exception as e:
                            logger.debug(f"解析消息元素失败: {e}")
                            continue

                    if not page_messages:
                        break

                    all_messages.extend(page_messages)

                    # 获取最小 message_id 用于下一页分页
                    min_id = min(m["message_id"] for m in page_messages)

                    # 如果已到达已索引的位置，停止抓取
                    if min_id <= max_existing_id:
                        break

                    before_id = min_id
                    page += 1

                    # 请求间隔，避免频繁抓取
                    await asyncio.sleep(0.5)

            # 过滤掉已存在的消息
            new_messages = [m for m in all_messages if m["message_id"] > max_existing_id]

            if new_messages:
                self._store_messages(channel, new_messages)
                logger.info(f"Telegram HTTP 抓取频道 {channel}: 新增 {len(new_messages)} 条消息")
            else:
                logger.debug(f"Telegram HTTP 频道 {channel}: 无新消息")

            return new_messages

        except Exception as e:
            logger.error(f"Telegram HTTP 抓取频道 {channel} 异常: {e}")
            return []

    def _parse_message_div(self, div, channel: str) -> Optional[dict]:
        """
        解析单个消息 div 元素

        :param div: BeautifulSoup 元素
        :param channel: 频道名
        :return: 解析后的消息字典
        """
        # 提取 message_id
        msg_id_attr = div.get("data-post", "")
        if not msg_id_attr:
            return None

        # data-post 格式: "channel/123"
        parts = msg_id_attr.split("/")
        if len(parts) < 2:
            return None

        try:
            message_id = int(parts[-1])
        except ValueError:
            return None

        # 提取消息文本
        text_elem = div.select_one(".tgme_widget_message_text")
        text = text_elem.get_text(separator="\n") if text_elem else ""

        # 提取日期
        date_elem = div.select_one(".tgme_widget_message_date time")
        date_str = date_elem.get("datetime", "") if date_elem else ""

        # 提取 115 链接
        urls = MessageParser.extract_115_urls(text)

        # 同时检查链接元素中的 href
        link_elems = div.select("a[href]")
        for link in link_elems:
            href = link.get("href", "")
            if MessageParser.is_115_url(href):
                if href not in urls:
                    urls.append(href)

        if not urls:
            return None

        return {
            "message_id": message_id,
            "text": text,
            "date": date_str,
            "urls": urls,
        }

    async def _search_local_index(self, keyword: str, channels: List[str]) -> List[Dict]:
        """
        查询本地 SQLite 索引

        :param keyword: 搜索关键词
        :param channels: 频道列表
        :return: 搜索结果
        """
        results = []
        try:
            conn = self._get_db()
            placeholders = ",".join(["?" for _ in channels])
            query = f"""
                SELECT channel_name, message_id, text, date, urls
                FROM tg_messages
                WHERE channel_name IN ({placeholders})
                AND text LIKE ?
                ORDER BY message_id DESC
                LIMIT 50
            """
            params = channels + [f"%{keyword}%"]
            rows = conn.execute(query, params).fetchall()
            conn.close()

            for row in rows:
                channel_name, message_id, text, date_str, urls_json = row
                try:
                    urls = json.loads(urls_json) if urls_json else []
                except json.JSONDecodeError:
                    urls = []

                for url in urls:
                    title = MessageParser.extract_title(text, url)
                    if title:
                        results.append({
                            "url": url,
                            "title": title,
                            "update_time": date_str,
                            "channel": channel_name,
                            "raw_text": text,
                        })

        except Exception as e:
            logger.error(f"Telegram SQLite 搜索失败: {e}")

        return results

    # ------------------------------------------------------------------
    # MTProto 模式
    # ------------------------------------------------------------------

    async def _search_mtproto(self, keyword: str, channels: List[str]) -> List[Dict]:
        """
        MTProto 模式搜索，通过 Telethon iter_messages 进行服务端搜索

        :param keyword: 搜索关键词
        :param channels: 频道列表
        :return: 搜索结果
        """
        results = []

        try:
            from telethon import TelegramClient as TelethonClient
        except ImportError:
            logger.error("Telethon 未安装，请运行: pip install telethon")
            return results

        if not self._api_id or not self._api_hash:
            logger.error("MTProto 模式需要配置 API ID 和 API Hash")
            return results

        session = self._session_file or "p115strgmsub_tg"
        client = TelethonClient(session, int(self._api_id), self._api_hash)

        try:
            await client.start()

            for channel in channels:
                try:
                    entity = await client.get_entity(channel)
                    messages = client.iter_messages(
                        entity,
                        search=keyword,
                        limit=50,
                    )

                    async for msg in messages:
                        if not msg.text:
                            continue

                        urls = MessageParser.extract_115_urls(msg.text)
                        if not urls:
                            continue

                        for url in urls:
                            title = MessageParser.extract_title(msg.text, url)
                            if title:
                                results.append({
                                    "url": url,
                                    "title": title,
                                    "update_time": msg.date.isoformat() if msg.date else "",
                                    "channel": channel,
                                    "raw_text": msg.text,
                                })

                except Exception as e:
                    logger.warning(f"MTProto 搜索频道 {channel} 失败: {e}")
                    continue

        except Exception as e:
            logger.error(f"MTProto 搜索异常: {e}")
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

        return results

    async def qr_login(self) -> str:
        """
        生成 MTProto QR 码登录 URL

        :return: QR 码 URL 字符串，失败返回空字符串
        """
        try:
            from telethon import TelegramClient as TelethonClient

            if not self._api_id or not self._api_hash:
                logger.error("MTProto 模式需要配置 API ID 和 API Hash")
                return ""

            session = self._session_file or "p115strgmsub_tg"
            client = TelethonClient(session, int(self._api_id), self._api_hash)
            await client.connect()

            qr_login = await client.qr_login()
            return qr_login.url

        except Exception as e:
            logger.error(f"QR 登录生成失败: {e}")
            return ""

    # ------------------------------------------------------------------
    # 计数器
    # ------------------------------------------------------------------

    def get_api_call_count(self) -> int:
        return self._api_call_count

    def reset_api_call_count(self):
        self._api_call_count = 0
