# 插件生命周期

> MoviePilot v2 插件的必备方法和生命周期管理。

---

## 插件基类

所有 MoviePilot v2 插件继承 `_PluginBase`:

```python
from app.plugins import _PluginBase

class P115StrgmSub(_PluginBase):
    plugin_name = "115网盘订阅追更"
    plugin_desc = "结合MoviePilot订阅功能，自动搜索115网盘资源并转存缺失的电影和剧集。"
    plugin_icon = "https://raw.githubusercontent.com/jxxghp/MoviePilot-Plugins/main/icons/cloud.png"
    plugin_version = "1.4.2"
    plugin_author = "mrtian2016"
    plugin_config_prefix = "p115strgmsub_"
    plugin_order = 20
    auth_level = 1
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:40-58`

---

## 必备方法

### `init_plugin(config: dict)`

插件初始化入口，MoviePilot 启动或配置更新时调用。

**职责顺序**:
1. 停止现有服务 (`stop_service`)
2. 初始化运行时资源
3. 从 `config` dict 读取配置到实例变量
4. 初始化客户端和处理器
5. 应用配置变更（如站点切换）
6. 处理 `_onlyonce` 一次性运行

**参考**: `plugins.v2/p115strgmsub/__init__.py:629-736`

### `get_state() -> bool`

返回插件是否启用。

### `get_form() -> Tuple[List[dict], Dict[str, Any]]`

返回 `(表单schema, 默认配置)` 用于插件配置页面。

### `get_page() -> Optional[List[dict]]`

返回详情页面 JSON schema（数据统计、历史记录等）。

### `get_api() -> List[Dict[str, Any]]`

返回插件提供的 HTTP API 端点列表。

### `get_service() -> List[Dict[str, Any]]`

返回定时任务列表，每个任务包含 `id/name/trigger/func/kwargs`。

**参考**: `plugins.v2/p115strgmsub/__init__.py:956-1003`

### `get_command() -> List[Dict[str, Any]]`

返回远程消息触发的命令定义。

### `stop_service()`

清理资源：停止调度器、释放连接。

---

## 调度器模式

使用 `apscheduler.schedulers.background.BackgroundScheduler`:

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

def get_service(self) -> List[Dict[str, Any]]:
    if not self._enabled:
        return []
    return [{
        "id": "P115StrgmSub",
        "name": "115网盘订阅追更服务",
        "trigger": CronTrigger.from_crontab(self._cron),
        "func": self.sync_subscribes,
        "kwargs": {}
    }]
```

**注意事项**:
- `get_service` 返回的是声明式配置，MoviePilot 框架负责创建调度器
- 主类内部也可以创建自己的 `BackgroundScheduler` 用于动态调度（如窗口切换）
- `stop_service` 中必须正确关闭所有自行创建的调度器

**参考**: `plugins.v2/p115strgmsub/__init__.py:134-147`（toggle_scheduler）

---

## 配置持久化

使用 `self.update_config(dict)` 保存配置，从 `init_plugin(config: dict)` 的参数读取配置。

```python
def __update_config(self):
    self.update_config({
        "enabled": self._enabled,
        "cron": self._cron,
        "cookies": self._cookies,
        # ... 所有配置项
    })
```

**反模式**:
- 不要在 `init_plugin` 之外的地方直接修改 `config` dict
- 不要在配置中存储运行时状态（如连接对象）
