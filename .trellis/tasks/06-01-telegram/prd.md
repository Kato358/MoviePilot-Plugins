# 替换搜索源为纯 Telegram 频道

## 目标

将 P115StrgmSub 插件的搜索源从 Nullbr + HDHive + PanSou 三源架构，替换为纯 Telegram 频道方案（HTTP + MTProto 双模式）。大幅简化配置和代码复杂度。

## 背景

详见 `docs/adr/0001-telegram-as-sole-search-source.md`

---

## 架构设计

### 双模式 Telegram 客户端

| 模式 | 认证 | 搜索能力 | 默认 |
|------|------|----------|------|
| HTTP | 零配置 | 抓取公开频道最近消息，SQLite 本地索引搜索 | 是 |
| MTProto | 扫码登录（Telethon QR） | 服务端搜索全部历史消息 | 否（可选增强） |

### 目标频道

| 频道名 | 说明 |
|--------|------|
| gimy115 | 剧迷热更频道 |
| QukanMovie | 115 影视资源分享频道 |
| yingshiziyuanpindao | 星河频道 |

### 搜索优先级

单一搜索源（Telegram），内部按频道优先级搜索。关键词降级策略与原 PanSou 一致。

---

## 范围

### 新建文件
- `clients/telegram.py` — 双模式 Telegram 客户端（HTTP 抓取 + MTProto 连接）
- `utils/message_parser.py` — 频道消息解析器（适配三个频道的帖子格式，提取 115 链接）

### 修改文件
- `handlers/search.py` — 移除 Nullbr/HDHive/PanSou 搜索逻辑，改为仅 Telegram
- `handlers/sync.py` — 移除 HDHive 延迟解锁逻辑
- `ui/config.py` — 移除旧搜索源配置项，新增 Telegram 配置（频道列表、模式选择、MTProto 凭据）
- `__init__.py` — 大幅精简：移除 HDHive 签到/Cookie 刷新/积分管理、移除多源初始化，新增 Telegram 客户端初始化
- `clients/__init__.py` — 更新导出
- `utils/__init__.py` — 更新导出
- `requirements.txt` — 新增 `telethon`、`beautifulsoup4`（HTTP 解析），移除不需要的依赖

### 删除文件
- `clients/pansou.py` — 被 Telegram 客户端替代
- `clients/nullbr.py` — 不再需要
- `utils/tools.py` 中的 HDHive 工具函数 — `get_hdhive_token_info`、`check_hdhive_cookie_valid`、`refresh_hdhive_cookie_with_playwright`、`hdhive_checkin_api`、`hdhive_checkin_playwright`、`get_hdhive_extension_filename`、`download_so_file`、`convert_hdhive_to_pansou_format`

### 不变
- `clients/p115.py` — 115 客户端保持不变
- `handlers/subscribe.py` — 订阅管理保持不变
- `handlers/api.py` — API 端点保持不变
- `utils/file_matcher.py` — 文件匹配逻辑保持不变

---

## 详细需求

### 1. Telegram 客户端 (`clients/telegram.py`)

```python
class TelegramClient:
    """双模式 Telegram 客户端"""

    def __init__(self, channels: List[str], mode: str = "http",
                 api_id: str = "", api_hash: str = "",
                 session_file: str = "", proxy=None):

    async def search(self, keyword: str, channels: List[str] = None) -> List[Dict]:
        """统一搜索接口，返回 [{"url": ..., "title": ..., "update_time": ..., "channel": ..., "raw_text": ...}]"""

    # HTTP 模式
    async def _fetch_channel_messages_http(self, channel: str, limit: int = 500) -> List[dict]:
        """通过 t.me/s/<channel> 抓取公开频道消息"""

    async def _search_local_index(self, keyword: str, channels: List[str]) -> List[Dict]:
        """查询本地 SQLite 索引"""

    # MTProto 模式
    async def _search_mtproto(self, keyword: str, channel: str) -> List[Dict]:
        """通过 Telethon iter_messages 搜索"""

    async def qr_login(self) -> str:
        """生成 QR 码登录 URL"""

    # 通用
    def get_api_call_count(self) -> int:
    def reset_api_call_count(self):
```

### 2. 消息解析器 (`utils/message_parser.py`)

```python
class MessageParser:
    """频道消息解析器"""

    # 115 链接正则
    PATTERN_115 = r'https?://(?:www\.)?115\.com/s/\w+'

    @staticmethod
    def parse_message(text: str, channel: str = "") -> List[Dict]:
        """从消息文本中提取 115 链接和资源标题
        返回: [{"url": "...", "title": "..."}]
        """

    @staticmethod
    def extract_title(text: str, url: str) -> str:
        """从消息文本中提取资源标题（链接前最近的非空文本行）"""
```

针对三个频道做格式适配：
- gimy115: 标题通常在消息开头，格式如 "【标题】"
- QukanMovie: 标题+链接的标准格式
- yingshiziyuanpindao: 可能包含多季打包

### 3. SQLite 本地索引

```sql
CREATE TABLE IF NOT EXISTS tg_messages (
    channel_name TEXT NOT NULL,
    message_id   INTEGER NOT NULL,
    text         TEXT,
    date         TEXT,
    urls         TEXT,     -- JSON 数组，提取的 115 链接
    PRIMARY KEY (channel_name, message_id)
);
CREATE INDEX IF NOT EXISTS idx_tg_text ON tg_messages(text);
```

- 增量抓取：记录每个频道的 `max(message_id)`，下次只抓取更新的消息
- 存储路径：使用 MoviePilot 的插件数据目录

### 4. 配置变更

新增配置项：
```python
_telegram_enabled: bool = True
_telegram_mode: str = "http"              # "http" 或 "mtproto"
_telegram_channels: str = "gimy115,QukanMovie,yingshiziyuanpindao"
_telegram_api_id: str = ""                # MTProto 模式需要
_telegram_api_hash: str = ""              # MTProto 模式需要
```

移除配置项：所有 `_pansou_*`、`_nullbr_*`、`_hdhive_*` 开头的配置

### 5. SearchHandler 改造

```python
class SearchHandler:
    def __init__(self, telegram_client, telegram_enabled, telegram_channels, ...):
        # 移除 pansou_client, nullbr_client, hdhive_client

    def get_enabled_sources(self) -> List[str]:
        # 仅返回 ["telegram"] 或 []

    def search_resources(self, mediainfo, media_type, season) -> List[Dict]:
        # 仅调用 Telegram 搜索

    def _search_telegram(self, mediainfo, media_type, season) -> List[Dict]:
        # 关键词降级策略
```

### 6. SyncHandler 精简

移除 HDHive 延迟解锁逻辑（`need_unlock`、`unlock_hdhive_resource` 等）。

---

## 依赖变更

### requirements.txt

```
p115client==0.0.8.4.6
telethon>=1.36.0
beautifulsoup4>=4.12.0
```

移除：`playwright-stealth`（原 HDHive 专用）

### 新增 Python 标准库依赖
- `sqlite3`（标准库，无需安装）
- `html.parser`（标准库，配合 BeautifulSoup 解析 t.me 页面）

---

## 验收标准

- [ ] HTTP 模式零配置可搜索三个频道的 115 资源
- [ ] MTProto 模式扫码登录后可搜索历史消息
- [ ] 搜索结果正确提取 115 链接和资源标题
- [ ] 电视剧搜索关键词降级正常（"标题+季号" → "标题"）
- [ ] 电影搜索关键词降级正常（"标题+年份" → "标题"）
- [ ] 搜索结果与 SyncHandler 正确集成，转存流程不受影响
- [ ] 洗版模式评分正常（基于 SubscribeFilter）
- [ ] 增量抓取正常（不重复抓取已索引的消息）
- [ ] 所有 Nullbr/HDHive/PanSou 相关代码已清除
- [ ] 配置页面仅显示 Telegram 相关配置项
- [ ] 版本号更新

---

## 风险

| 风险 | 缓解 |
|------|------|
| 标题匹配误命中 | 下游 `recognize_media` + `FileMatcher` 双层验证 |
| HTTP 页面格式变更导致解析失败 | 消息解析器针对各频道独立适配，一个频道失败不影响其他 |
| Telethon 依赖体积大 | 与 playwright-stealth 互换，净增量可控 |
| Telegram 风控封号 | HTTP 模式无此风险；MTProto 模式用户自行承担 |
| 三个频道帖子格式变化 | MessageParser 用正则而非硬编码格式，有一定容错性 |
