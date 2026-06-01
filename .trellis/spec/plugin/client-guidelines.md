# 客户端开发

> 外部服务客户端的封装模式和开发规范。

---

## 设计原则

- 每个外部服务对应 `clients/` 下一个文件
- 封装所有 HTTP 请求细节，调用方不需要知道 API 地址和认证方式
- 统一返回字典格式，不返回原始 `requests.Response`
- 必须内置速率限制和重试机制（115 网盘风控严格）

---

## 115 客户端 (`P115ClientManager`)

**参考**: `plugins.v2/p115strgmsub/clients/p115.py`

### 核心组件

| 组件 | 用途 |
|------|------|
| `RateLimiter` | API 请求间隔控制（基础间隔 + 随机抖动） |
| `PathCache` | 路径到 CID 的 TTL 缓存 |
| `retry_on_failure` | 指数退避重试装饰器 |

### 速率限制器

```python
class RateLimiter:
    def __init__(self, min_interval: float = 1.5, jitter_ratio: float = 0.3):
        """基础间隔 ± 30% 随机抖动，避免固定节奏触发风控"""

    def wait(self):
        """带线程锁的等待，确保并发安全"""
```

**关键配置**:
- `DEFAULT_MIN_INTERVAL = 1.5` 秒（基础间隔）
- `DEFAULT_JITTER_RATIO = 0.3`（±30% 随机浮动）
- `DEFAULT_MAX_RETRIES = 3`
- `DEFAULT_PATH_CACHE_TTL = 3600` 秒

### 批量转存

批量转存使用 `transfer_files_batch`，分批处理并添加批次间隔：

```python
def transfer_files_batch(
    self, share_url: str, file_ids: List[str], save_path: str,
    batch_size: int = 20, batch_interval: float = 3.0
) -> Tuple[List[str], List[str]]:
```

- 使用逗号分隔多个 `file_id` 进行批量提交
- 批次失败时降级为逐个转存
- 批次间添加随机间隔避免风控

**参考**: `plugins.v2/p115strgmsub/clients/p115.py:717-808`

---

## PanSou 客户端 (`PanSouClient`)

**参考**: `plugins.v2/p115strgmsub/clients/pansou.py`

### 认证机制

支持 Token 认证，Token 自动刷新（提前 5 分钟）：

```python
def _get_token(self) -> Optional[str]:
    """登录获取 Token，过期自动刷新"""
```

### 关键词匹配

PanSou 搜索结果需要二次过滤，确保标题匹配搜索关键词：

```python
@classmethod
def _title_matches_search_key(cls, key: str, title: str) -> bool:
    """原串子串 → 规范化子串 → 紧凑子串，三级匹配"""
```

**规范逻辑**: NFKC 归一化 → 全角转半角 → 去标点空白 → casefold

---

## Nullbr 客户端 (`NullbrClient`)

**参考**: `plugins.v2/p115strgmsub/clients/nullbr.py`

基于 TMDB ID 精准查询，通过 HTTP Header 传递认证：

```python
self.headers = {
    "X-APP-ID": app_id,
    "X-API-KEY": api_key
}
```

---

## 代理支持

所有客户端支持 MoviePilot 全局代理配置：

```python
proxy = settings.PROXY
if proxy:
    self._proxies = proxy if isinstance(proxy, dict) else {"http": proxy, "https": proxy}
```

**参考**: `plugins.v2/p115strgmsub/clients/pansou.py:62-65`

---

## 新增客户端模板

```python
"""
<服务名> 客户端
"""
from app.core.config import settings
from app.log import logger

class NewClient:
    def __init__(self, ..., proxy=None):
        self._api_call_count = 0
        # 代理兼容字符串和字典
        if proxy:
            self._proxies = proxy if isinstance(proxy, dict) else {"http": proxy, "https": proxy}
        else:
            self._proxies = None

    def get_api_call_count(self) -> int:
        return self._api_call_count

    def reset_api_call_count(self):
        self._api_call_count = 0
```

---

## 反模式

- 不要在客户端中包含业务逻辑（如订阅匹配）→ 放在 `handlers/`
- 不要忽略速率限制 → 115 网盘风控严格
- 不要返回原始 `Response` 对象 → 统一返回字典
- 不要在客户端中使用 `logger.info` 打印敏感信息（Cookie、Token 完整值）
