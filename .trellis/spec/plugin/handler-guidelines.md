# 处理器开发

> 业务逻辑处理器的设计模式和开发规范。

---

## 设计原则

- 处理器是业务编排层，协调客户端和 MoviePilot 框架
- 通过构造函数注入依赖（客户端、配置、回调函数）
- 不直接修改插件配置，通过回调函数与主类交互
- 每个处理器职责单一

---

## Handler 列表

| Handler | 职责 | 参考文件 |
|---------|------|----------|
| `SearchHandler` | 多源搜索编排（Nullbr > HDHive > PanSou） | `handlers/search.py` |
| `SyncHandler` | 转存流程（匹配文件、批量转存、记录历史） | `handlers/sync.py` |
| `SubscribeHandler` | 订阅状态管理（完成判断、站点切换） | `handlers/subscribe.py` |
| `ApiHandler` | 外部 API 端点封装 | `handlers/api.py` |

---

## SearchHandler — 搜索编排

**参考**: `plugins.v2/p115strgmsub/handlers/search.py`

### 多源搜索优先级

搜索源按固定优先级: Nullbr > HDHive > PanSou

```python
def get_enabled_sources(self) -> List[str]:
    """返回已启用且可用的搜索源列表，按优先级排序"""
    sources = []
    if self._nullbr_enabled and self._nullbr_client:
        sources.append("nullbr")
    if self._hdhive_enabled:
        sources.append("hdhive")
    if self._pansou_enabled and self._pansou_client:
        sources.append("pansou")
    return sources
```

### 资源格式统一

不同搜索源返回格式不同，统一为:
```python
{"url": "...", "title": "...", "update_time": "..."}
```

转换函数在 `utils/tools.py` 中: `convert_nullbr_to_pansou_format` / `convert_hdhive_to_pansou_format`

### HDHive 积分管理

HDHive 支持免费和付费资源，需要双层积分预算控制:
- 全局预算: `_hdhive_max_unlock_points`
- 单订阅预算: `_hdhive_max_points_per_sub`
- 历史积分持久化: 通过 `get_data_func` / `save_data_func` 读写

**参考**: `plugins.v2/p115strgmsub/handlers/search.py:578-636`

---

## SyncHandler — 转存流程

**参考**: `plugins.v2/p115strgmsub/handlers/sync.py`

### 电影处理流程

```
检查历史记录 → 识别媒体 → 搜索资源 → 匹配文件 → 检查分享有效性
→ 执行转存 → 记录历史 → 完成订阅
```

### 电视剧处理流程

```
检查缺失集数 → 识别媒体 → 获取缺失剧集 → 过滤未播出集数
→ 逐源搜索回退 → 匹配文件 → 批量转存 → 记录历史 → 更新订阅状态
```

### 洗版模式

订阅的 `best_version=1` 启用洗版:
- 已有资源不跳过，但根据过滤条件评分
- 新资源分数更高时才替换
- 通过 `SubscribeFilter` 评分系统实现

### 关键约束

- 单次同步最大转存数: `_max_transfer_per_sync` (默认 50)
- 批量转存每批数量: `_batch_size` (默认 20)
- 检查 `global_vars.is_system_stopped` 支持系统停止中断

---

## SubscribeHandler — 订阅管理

**参考**: `plugins.v2/p115strgmsub/handlers/subscribe.py`

### 订阅完成判断

```python
def check_and_finish_subscribe(self, subscribe, mediainfo, success_episodes):
    # 1. 合并已下载集数到 note 字段
    # 2. 计算剩余缺失集数 (lack_episode)
    # 3. 缺失归零时调用 SubscribeChain().finish_subscribe_or_not() 完成订阅
```

### 站点管理

屏蔽/恢复系统订阅通过修改所有订阅的 `sites` 字段实现:

```python
def set_blocked_sites_only_115(self) -> List[int]:
    """所有订阅 sites 设为仅 115 网盘"""

def set_unblocked_sites(self, unblocked_site_names: List[str]) -> List[int]:
    """所有订阅 sites 设为用户配置的站点"""
```

**关键**: 必须处理 `sites` 字段的不同存储格式（字符串 vs 列表），通过 `_guess_sites_storage_format` 动态判断。

---

## 依赖注入模式

处理器不持有主类引用，通过构造函数注入:

```python
class SyncHandler:
    def __init__(
        self,
        p115_manager,                # 客户端实例
        search_handler: SearchHandler, # 其他 Handler
        subscribe_handler: SubscribeHandler,
        chain,                        # MediaChain
        save_path: str,               # 配置值
        notify: bool,
        post_message_func: Callable,  # 回调函数
        get_data_func: Callable,      # 持久化回调
        save_data_func: Callable,
    ):
```

---

## 反模式

- 不要在 Handler 中直接调用 `self.update_config()` → 通过回调通知主类
- 不要在 Handler 中创建自己的 `SessionFactory` → 使用注入的数据库操作
- 不要硬编码搜索源优先级 → 使用 `get_enabled_sources()` 动态获取
