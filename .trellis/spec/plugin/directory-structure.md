# 目录结构

> 插件模块的组织方式与文件布局。

---

## 插件根目录

```
plugins.v2/p115strgmsub/
├── __init__.py              # 主插件类 P115StrgmSub，继承 _PluginBase
├── requirements.txt         # pip 依赖声明
├── clients/                 # 外部服务客户端
│   ├── __init__.py          # 统一导出 ClientManager / PanSouClient / NullbrClient
│   ├── p115.py              # P115ClientManager + 速率限制 + 路径缓存
│   ├── pansou.py            # PanSouClient 网盘搜索
│   └── nullbr.py            # NullbrClient TMDB 资源查询
├── handlers/                # 业务逻辑处理器
│   ├── __init__.py          # 统一导出所有 Handler
│   ├── search.py            # SearchHandler 搜索编排（多源回退）
│   ├── sync.py              # SyncHandler 同步/转存逻辑
│   ├── subscribe.py         # SubscribeHandler 订阅状态管理
│   └── api.py               # ApiHandler 外部 API 端点
├── ui/                      # UI 配置
│   ├── __init__.py          # 统一导出 UIConfig
│   └── config.py            # 表单 schema + 详情页面生成
└── utils/                   # 工具函数
    ├── __init__.py           # 统一导出
    ├── file_matcher.py       # FileMatcher + SubscribeFilter 文件匹配
    └── tools.py              # HDHive 工具、格式转换、Playwright 登录
```

---

## 模块职责边界

### `__init__.py` (主类)

- 继承 `_PluginBase`，实现所有必备方法
- 管理配置读写（`init_plugin` / `__update_config`）
- 初始化客户端和处理器实例
- 调度器管理（`BackgroundScheduler`）
- 事件处理（`SubscribeAdded` / `SubscribeModified` / `PluginAction`）
- 系统订阅屏蔽/恢复的状态切换

**参考**: `plugins.v2/p115strgmsub/__init__.py`

### `clients/`

- 每个外部服务一个文件
- 封装 HTTP 请求、认证、速率限制、错误处理
- 不包含业务逻辑，仅提供 API 调用能力
- 统一返回字典格式，不返回原始 response

### `handlers/`

- 业务逻辑编排层
- `SearchHandler` 协调多个搜索源，按优先级回退
- `SyncHandler` 处理转存流程（匹配文件、批量转存、记录历史）
- `SubscribeHandler` 管理订阅状态（完成判断、站点切换）
- `ApiHandler` 封装外部可调用的 API

### `utils/`

- 纯工具函数，不依赖业务状态
- `FileMatcher` 纯数据匹配（正则、文件名解析）
- `SubscribeFilter` 过滤条件评分

### `ui/`

- 仅负责生成 MoviePilot UI 所需的表单和页面 JSON schema
- 不包含业务逻辑，只做数据展示格式化

---

## 新增模块的放置规则

| 要添加的内容 | 放在哪里 |
|-------------|---------|
| 新搜索源（如新网盘） | `clients/` 新文件 + `SearchHandler` 中添加调度 |
| 新业务流程 | `handlers/` 新文件 |
| 新工具函数 | `utils/` 新文件或追加到现有文件 |
| 新 UI 配置项 | `ui/config.py` 中追加 |

---

## 反模式

- 不要在 `__init__.py` 中直接写 HTTP 请求逻辑 → 使用 `clients/`
- 不要在 `clients/` 中调用数据库 → 数据库操作放在 `handlers/` 或主类
- 不要在 `utils/` 中导入 MoviePilot 框架的业务类型 → 保持工具函数独立
