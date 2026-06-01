# P115StrgmSub 插件开发规范

> 基于 MoviePilot 插件框架的 115 网盘订阅追更插件开发指南。

---

## 项目概述

本项目是 MoviePilot 媒体管理系统的 v2 插件，自动化 115 网盘资源搜索与转存流程。

**核心工作流**: MoviePilot 订阅 → 搜索网盘资源 → 转存到个人 115 网盘 → 更新订阅状态

---

## 规范索引

| 指南 | 说明 | 状态 |
|------|------|------|
| [目录结构](./directory-structure.md) | 模块组织与文件布局 | 已填充 |
| [插件生命周期](./plugin-lifecycle.md) | init_plugin / get_service / stop_service 等必备方法 | 已填充 |
| [客户端开发](./client-guidelines.md) | 外部服务客户端封装模式 | 已填充 |
| [处理器开发](./handler-guidelines.md) | 业务逻辑处理器模式 | 已填充 |
| [配置与 UI](./config-and-ui.md) | 配置管理、表单和页面生成 | 已填充 |
| [数据访问](./data-access.md) | 数据库操作与 ORM 使用 | 已填充 |
| [事件系统](./event-system.md) | MoviePilot 事件订阅与发布 | 已填充 |
| [质量规范](./quality-guidelines.md) | 代码标准、禁止模式、防风控要求 | 已填充 |

---

## 思维指南

| 指南 | 用途 | 使用场景 |
|------|------|----------|
| [代码复用思维](../guides/code-reuse-thinking-guide.md) | 识别重复模式，减少冗余 | 发现重复代码时 |
| [跨层思维](../guides/cross-layer-thinking-guide.md) | 跨模块数据流分析 | 涉及多模块的功能 |

---

## 快速参考

### MoviePilot 插件框架核心依赖

```python
from app.plugins import _PluginBase          # 插件基类
from app.core.config import settings          # 全局配置
from app.core.event import Event, eventmanager # 事件系统
from app.db import SessionFactory             # 数据库会话
from app.db.subscribe_oper import SubscribeOper # 订阅操作
from app.log import logger                    # 日志
from app.schemas.types import EventType, MediaType, NotificationType
```

### 必备方法

每个 MoviePilot v2 插件必须实现:
- `init_plugin(config)` - 初始化
- `get_state()` - 返回启用状态
- `get_form()` - 返回配置表单 schema
- `get_page()` - 返回详情页面 schema
- `get_api()` - 返回 API 端点列表
- `get_service()` - 返回定时服务列表
- `get_command()` - 返回远程命令列表
- `stop_service()` - 停止服务
