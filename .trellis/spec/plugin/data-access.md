# 数据访问

> 数据库操作和 ORM 使用规范。

---

## 数据库会话管理

MoviePilot 使用 SQLAlchemy，通过 `SessionFactory` 获取会话:

```python
from app.db import SessionFactory
from sqlalchemy import text

# 方式 1：上下文管理器
with SessionFactory() as db:
    rows = db.execute(text("SELECT id, name FROM site")).fetchall()
    db.commit()

# 方式 2：传递给操作类
with SessionFactory() as db:
    subscribes = SubscribeOper(db=db).list("N,R")
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:181-186`

---

## ORM 操作类

MoviePilot 提供了标准操作类:

| 操作类 | 用途 |
|--------|------|
| `SubscribeOper` | 订阅 CRUD |
| `DownloadHistoryOper` | 下载历史记录 |
| `Site` | 站点模型 |

```python
from app.db.subscribe_oper import SubscribeOper
from app.db.downloadhistory_oper import DownloadHistoryOper

# 列表查询
subscribes = SubscribeOper(db=db).list("N,R")  # 状态过滤

# 更新
SubscribeOper(db=db).update(subscribe_id, {"lack_episode": 0, "note": new_note})

# 添加历史
DownloadHistoryOper().add(
    path=save_dir,
    type=mediainfo.type.value,
    title=mediainfo.title,
    # ...
)
```

---

## 原生 SQL

ORM 不支持的操作使用原生 SQL:

```python
with SessionFactory() as db:
    # 查询
    row = db.execute(text("SELECT id FROM site WHERE name=:n LIMIT 1"), {"n": "115网盘"}).fetchone()

    # 插入
    db.execute(text(
        "INSERT INTO site (id, name, url, is_active, limit_interval, limit_count, limit_seconds, timeout) "
        "VALUES (:id, :name, :url, :is_active, :limit_interval, :limit_count, :limit_seconds, :timeout)"
    ), {"id": -1, "name": "115网盘", ...})
    db.commit()
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:225-262`

---

## 插件数据持久化

插件私有数据使用 `_PluginBase` 提供的 key-value 存储:

```python
# 保存
self.save_data('history', history_list)
self.save_data('sub_points_history', points_dict)

# 读取
history = self.get_data('history') or []
points = self.get_data('sub_points_history') or {}
```

**适用场景**: 历史记录、统计计数、缓存数据等不需要跨查询的简单数据。

---

## 反模式

- 不要在循环中反复创建 `SessionFactory` 会话 → 复用同一个会话
- 不要忘记 `db.commit()` → 写操作后必须提交
- 不要在 `SessionFactory` 外持有 ORM 对象引用 → 对象与会话绑定
- 不要使用裸 SQL 拼接用户输入 → 使用参数化查询 (`:param`)
