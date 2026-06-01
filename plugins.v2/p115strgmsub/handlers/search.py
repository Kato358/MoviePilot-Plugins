"""
搜索处理模块
负责所有搜索相关逻辑：Telegram 频道搜索
"""
from typing import Optional, List, Dict, Any

from app.log import logger
from app.schemas import MediaInfo
from app.schemas.types import MediaType


class SearchHandler:
    """搜索处理器（Telegram 频道）"""

    def __init__(
        self,
        telegram_client=None,
        telegram_enabled: bool = True,
        telegram_channels: str = "gimy115,QukanMovie,yingshiziyuanpindao",
        only_115: bool = True,
        **kwargs,
    ):
        """
        初始化搜索处理器

        :param telegram_client: Telegram 客户端实例
        :param telegram_enabled: 是否启用 Telegram 搜索
        :param telegram_channels: Telegram 频道列表（逗号分隔）
        :param only_115: 是否只搜索115网盘资源（保留兼容）
        """
        self._telegram_client = telegram_client
        self._telegram_enabled = telegram_enabled
        self._telegram_channels_str = telegram_channels
        self._telegram_channels = self._parse_channels(telegram_channels)
        self._only_115 = only_115

    @staticmethod
    def _parse_channels(channels_str: str) -> List[str]:
        """解析逗号分隔的频道列表"""
        if not channels_str:
            return []
        return [ch.strip() for ch in channels_str.split(",") if ch.strip()]

    def get_enabled_sources(self) -> List[str]:
        """
        获取已启用且可用的搜索源列表

        :return: 搜索源名称列表 ["telegram"] 或 []
        """
        if self._telegram_enabled and self._telegram_client:
            return ["telegram"]
        return []

    def search_resources(
        self,
        mediainfo: MediaInfo,
        media_type: MediaType,
        season: Optional[int] = None
    ) -> List[Dict]:
        """
        统一的资源搜索方法，支持电影和电视剧

        :param mediainfo: 媒体信息
        :param media_type: 媒体类型（MOVIE 或 TV）
        :param season: 季号（电视剧必需）
        :return: 115网盘资源列表
        """
        sources = self.get_enabled_sources()

        for source in sources:
            results = self.search_single_source(source, mediainfo, media_type, season)
            if results:
                return results

        return []

    def search_single_source(
        self,
        source: str,
        mediainfo: MediaInfo,
        media_type: MediaType,
        season: Optional[int] = None
    ) -> List[Dict]:
        """
        使用指定的单一搜索源查询资源

        :param source: 搜索源名称 ("telegram")
        :param mediainfo: 媒体信息
        :param media_type: 媒体类型
        :param season: 季号（电视剧时使用）
        :return: 115网盘资源列表
        """
        if source == "telegram":
            if media_type == MediaType.MOVIE:
                return self._search_telegram_movie(mediainfo)
            else:
                return self._search_telegram_tv(mediainfo, season)
        else:
            logger.warning(f"未知的搜索源: {source}")
            return []

    def _search_telegram_movie(self, mediainfo: MediaInfo) -> List[Dict]:
        """
        使用 Telegram 搜索电影资源（带降级关键词策略）

        :param mediainfo: 媒体信息
        :return: 115网盘资源列表
        """
        if not self._telegram_client:
            logger.warning("Telegram 客户端未初始化，跳过查询")
            return []

        # 电影降级策略: "标题 年份" -> "标题"
        search_keywords = [
            f"{mediainfo.title} {mediainfo.year}" if mediainfo.year else mediainfo.title,
            mediainfo.title,
        ]

        for keyword in search_keywords:
            logger.info(f"使用 Telegram 搜索电影资源: {mediainfo.title}，关键词: '{keyword}'")
            results = self._telegram_search(keyword)
            if results:
                logger.info(f"Telegram 关键词 '{keyword}' 搜索到 {len(results)} 个结果")
                return results
            else:
                logger.info(f"Telegram 关键词 '{keyword}' 无结果，尝试下一个降级关键词")

        logger.info(f"Telegram 未找到电影 {mediainfo.title} 的资源")
        return []

    def _search_telegram_tv(self, mediainfo: MediaInfo, season: int) -> List[Dict]:
        """
        使用 Telegram 搜索电视剧资源（带降级关键词策略）

        :param mediainfo: 媒体信息
        :param season: 季号
        :return: 115网盘资源列表
        """
        if not self._telegram_client:
            logger.warning("Telegram 客户端未初始化，跳过查询")
            return []

        # 电视剧降级策略: "标题S季号" -> "标题"
        search_keywords = [
            f"{mediainfo.title}{season}",
            mediainfo.title,
        ]

        for keyword in search_keywords:
            logger.info(f"使用 Telegram 搜索电视剧资源: {mediainfo.title} S{season}，关键词: '{keyword}'")
            results = self._telegram_search(keyword)
            if results:
                logger.info(f"Telegram 关键词 '{keyword}' 搜索到 {len(results)} 个结果")
                return results
            else:
                logger.info(f"Telegram 关键词 '{keyword}' 无结果，尝试下一个降级关键词")

        logger.info(f"Telegram 未找到电视剧 {mediainfo.title} S{season} 的资源")
        return []

    def _telegram_search(self, keyword: str) -> List[Dict]:
        """
        Telegram 搜索的通用逻辑

        :param keyword: 搜索关键词
        :return: 115网盘资源列表
        """
        import asyncio

        try:
            return asyncio.run(
                self._telegram_client.search(keyword, self._telegram_channels)
            )
        except Exception as e:
            logger.error(f"Telegram 搜索异常: {e}")
            return []
