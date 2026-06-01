# 质量规范

> 代码标准、禁止模式和防风控要求。

---

## 代码风格

- Python 3.12+，使用 type hints
- 中文注释和日志（面向中文用户）
- 使用 `app.log.logger` 输出日志，不用 `print`
- 模块顶部使用中文文档字符串说明用途

---

## 防风控要求

115 网盘有严格的风控机制，必须遵守:

### API 请求间隔

```python
# P115ClientManager 中的 RateLimiter
DEFAULT_MIN_INTERVAL = 1.5      # 秒
DEFAULT_JITTER_RATIO = 0.3      # ±30% 随机浮动
DEFAULT_RECURSION_DELAY = 1.0   # 递归遍历子目录延迟
```

### 批量操作限制

- 单次同步最大转存数: 50（可配置）
- 批量转存每批数量: 20（可配置）
- 批次间隔: 3 秒 ± 30%
- Cron 最小间隔: 8 小时

### HDHive 积分预算

- 全局积分上限: `_hdhive_max_unlock_points`
- 单订阅积分上限: `_hdhive_max_points_per_sub`
- 搜索阶段过滤超出预算的资源
- 积分花费持久化，跨任务累积

---

## 并发安全

```python
# 主入口使用全局锁防止重复执行
from threading import Lock
lock = Lock()

def sync_subscribes(self):
    with lock:
        self._do_sync()
```

**参考**: `plugins.v2/p115strgmsub/__init__.py:37,1142-1159`

---

## 禁止模式

| 禁止 | 原因 |
|------|------|
| 直接 `import requests` 做网盘 API 调用 | 必须通过 `clients/` 封装 |
| 硬编码 Cookie / API Key | 从配置读取 |
| 忽略 `global_vars.is_system_stopped` 检查 | 系统停止时必须中止 |
| 在配置中存储运行时对象 | 配置只存可序列化值 |
| 不处理空值的 config.get | MoviePilot 前端可能提交 null |
| 跳过速率限制器 | 触发风控封号 |
| 在日志中打印完整 Cookie/Token | 安全风险 |

---

## 必须模式

| 必须 | 原因 |
|------|------|
| `init_plugin` 开头调用 `stop_service()` | 防止重复初始化 |
| 分享链接转存前检查有效性 | 避免无效操作浪费 API 次数 |
| 所有 HTTP 请求设置 timeout | 防止挂起 |
| 代理配置兼容字符串和字典格式 | MoviePilot 代理格式不统一 |
| `sites` 字段操作前判断存储格式 | SQLite 中可能是字符串或 JSON 列表 |

---

## 版本管理

版本号在两处同步更新:
1. `plugins.v2/p115strgmsub/__init__.py`: `plugin_version`
2. `package.v2.json`: `version` 和 `history`

---

## 测试检查清单

- [ ] 115 Cookie 无效时的错误处理
- [ ] 搜索源全部禁用时的提示
- [ ] 订阅为空时的行为
- [ ] 系统停止时的中断响应
- [ ] 新增订阅的事件兜底
- [ ] 洗版模式的评分逻辑
- [ ] Cron 表达式过频繁的回退
