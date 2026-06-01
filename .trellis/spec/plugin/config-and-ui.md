# 配置与 UI

> 插件配置管理、表单生成和详情页面开发规范。

---

## 配置管理

### 配置读写模式

配置以字典形式存储，主类实例变量作为运行时副本:

```python
# 读取（init_plugin 中）
self._cookies = config.get("cookies", "")
self._max_transfer_per_sync = int(config.get("max_transfer_per_sync", 50) or 50)

# 写入（__update_config 中）
def __update_config(self):
    self.update_config({
        "enabled": self._enabled,
        "cookies": self._cookies,
        # ...
    })
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:629-700`（读取）、`841-889`（写入）

### 配置命名规范

- 配置 key 使用 snake_case
- 与实例变量名保持一致（去掉 `_` 前缀）
- 布尔值配置以 `enable`/`enabled` 结尾

### 配置类型转换

从 config dict 读取时必须处理类型转换和空值:

```python
# 整数转换，处理 None 和空字符串
self._max_transfer_per_sync = int(config.get("max_transfer_per_sync", 50) or 50)

# 列表配置，处理 None
self._exclude_subscribes = config.get("exclude_subscribes", []) or []

# 字符串配置，处理 None
self._pansou_url = config.get("pansou_url", "https://so.252035.xyz/")
```

---

## UI 表单 (`get_form`)

**参考**: `plugins.v2/p115strgmsub/ui/config.py`

### 表单结构

MoviePilot 使用 Vuetify 组件描述表单:

```python
form_schema = [
    {
        'component': 'VForm',
        'content': [
            {
                'component': 'VRow',
                'content': [
                    {'component': 'VCol', 'props': {'cols': 12, 'md': 2},
                     'content': [{'component': 'VSwitch', 'props': {'model': 'enabled', 'label': '启用插件'}}]},
                ]
            },
        ]
    }
]
```

### 常用组件

| 组件 | 用途 |
|------|------|
| `VSwitch` | 布尔开关 |
| `VTextField` | 文本输入 |
| `VSelect` | 下拉选择 |
| `VChipGroup` + `VChip` | 多选标签 |
| `VAlert` | 提示信息 |
| `VDivider` | 分隔线 |

### 动态选项

需要从数据库获取选项时（如订阅列表、站点列表），在静态方法中查询:

```python
@staticmethod
def get_subscribe_options() -> List[Dict[str, Any]]:
    with SessionFactory() as db:
        subscribes = SubscribeOper(db=db).list("N,R")
    # 返回 [{"title": "显示名", "value": id}, ...]
```

**参考**: `plugins.v2/p115strgmsub/ui/config.py:18-60`

---

## 详情页面 (`get_page`)

**参考**: `plugins.v2/p115strgmsub/ui/config.py`

详情页面展示插件运行数据（统计、历史记录等）。数据来源:

```python
def get_page(self) -> Optional[List[dict]]:
    history = self.get_data('history') or []
    return UIConfig.get_page(history)
```

`get_data` / `save_data` 是 `_PluginBase` 提供的持久化存储方法，基于插件配置前缀的 key-value 存储。

---

## 反模式

- 不要在 UI 模块中包含业务逻辑 → UI 仅做展示格式化
- 不要硬编码选项列表 → 从数据库动态查询
- 不要忘记配置类型的空值处理 → MoviePilot 前端可能提交空字符串或 null
