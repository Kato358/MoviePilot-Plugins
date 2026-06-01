# 事件系统

> MoviePilot 事件订阅与发布机制。

---

## 事件监听

使用 `@eventmanager.register` 装饰器订阅事件:

```python
from app.core.event import Event, eventmanager
from app.schemas.types import EventType

@eventmanager.register(EventType.SubscribeAdded)
def on_subscribe_added(self, event: Event):
    """新订阅创建时触发"""
    sid = self._get_subscribe_id_from_event(event)
    if not sid:
        return
    # 处理逻辑...
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:473-501`

---

## 本插件使用的事件

| 事件 | 触发时机 | 处理逻辑 |
|------|----------|----------|
| `EventType.SubscribeAdded` | 新订阅创建 | 根据屏蔽状态设置订阅站点 |
| `EventType.SubscribeModified` | 订阅修改 | 仅日志记录，不做自动拉回 |
| `EventType.PluginAction` | 远程命令触发 | 执行同步任务 |

---

## 远程命令

通过 `get_command` 定义可被消息触发的命令:

```python
@staticmethod
def get_command() -> List[Dict[str, Any]]:
    return [{
        "cmd": "/p115_sub_action",
        "event": EventType.PluginAction,
        "desc": "115网盘订阅追更",
        "category": "订阅",
        "data": {"action": "p115_sub_action"}
    }]
```

命令触发时通过事件处理:

```python
@eventmanager.register(EventType.PluginAction)
def remote_sync(self, event: Event):
    event_data = event.event_data
    if not event_data or event_data.get("action") != "p115_sub_action":
        return
    self.sync_subscribes()
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:1172-1197`

---

## 事件数据提取

从事件中提取订阅 ID 的通用方法:

```python
def _get_subscribe_id_from_event(self, event: Event) -> Optional[int]:
    data = event.event_data or {}
    subscribe_id = data.get("subscribe_id") or data.get("id")
    if not subscribe_id and isinstance(data.get("subscribe"), dict):
        subscribe_id = data["subscribe"].get("id")
    try:
        return int(subscribe_id) if subscribe_id is not None else None
    except Exception:
        return None
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:461-471`

---

## 消息通知

使用 `post_message` 发送通知:

```python
self.post_message(
    mtype=NotificationType.Plugin,
    title="【115网盘订阅追更】转存完成",
    text=f"本次共转存 {total_count} 个文件",
    channel=event_data.get("channel"),  # 可选：指定回复渠道
    userid=event_data.get("user")        # 可选：指定回复用户
)
```

---

## 反模式

- 不要在事件处理函数中执行长时间操作 → 异步调度或线程执行
- 不要忽略事件数据的空值检查 → 兼容缺失字段
- 不要在事件处理中修改事件数据 → 事件是只读的
