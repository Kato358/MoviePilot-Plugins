# 搜索源迁移后清理

## Goal

清理 Telegram 搜索源迁移后遗留的冗余代码和架构不一致问题。

## Requirements

### 1. 清理 sync.py 多源迭代死代码
- `process_tv_subscribe` 中移除 `enabled_sources` 循环（L495-524）
- 直接调用 `search_handler.search_resources()` 或 `search_single_source("telegram", ...)`
- 移除 `remaining_sources` 日志和 `source_index` 索引逻辑
- 保留单源搜索的业务逻辑不变

### 2. 清理 SearchHandler HDHive 兼容桩
- 删除 `search.py` 中 4 个空桩方法：`set_data_funcs`、`reset_task_spent_points`、`reset_sub_spent_points`、`clear_sub_points`
- 删除 `__init__.py` 中对这些方法的调用（L614 `set_data_funcs`、L822 `reset_task_spent_points`）

### 3. telegram.py 用 httpx 替换 requests
- `_fetch_channel_messages_http` 改用 `httpx.AsyncClient` 替换同步 `requests.get`
- 方法签名保持 `async def`
- 移除 `search.py` 中的 ThreadPoolExecutor 事件循环桥接逻辑
- `search.py` 直接 `await telegram_client.search()`
- `requirements.txt`：`requests` 替换为 `httpx`
- `api.py` 中的 `asyncio.run()` 也需要适配

### 4. 删除 utils/tools.py
- 文件已无任何引用，仅剩空壳 docstring
- 从 `utils/__init__.py` 移除导出（如仍有）

### 5. 更新 CONTEXT.md
- "搜索源按优先级回退" 描述已过时，改为单源描述

## Acceptance Criteria

- [ ] sync.py 不再有多源迭代逻辑
- [ ] search.py 无 HDHive 兼容桩
- [ ] telegram.py HTTP 模式使用 httpx 真正异步
- [ ] search.py 无 ThreadPoolExecutor 桥接
- [ ] tools.py 已删除
- [ ] 所有 Python 文件语法检查通过
- [ ] 无残留引用
