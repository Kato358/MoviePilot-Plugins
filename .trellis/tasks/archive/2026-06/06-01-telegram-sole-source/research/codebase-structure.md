# P115StrgmSub 插件代码结构分析

## 插件根目录

`plugins.v2/p115strgmsub/`

## 文件结构 (16 文件)

```
plugins.v2/p115strgmsub/
  __init__.py                    # 主插件类 P115StrgmSub (1198行)
  requirements.txt               # 依赖: p115client, playwright-stealth
  clients/
    __init__.py                  # 导出: P115ClientManager, PanSouClient, NullbrClient
    p115.py                      # 115 客户端 (速率限制, 路径缓存, 转存)
    pansou.py                    # PanSou 聚合搜索 (354行)
    nullbr.py                    # Nullbr TMDB 查询 (201行)
  handlers/
    __init__.py                  # 导出: SearchHandler, SyncHandler, SubscribeHandler, ApiHandler
    search.py                    # 搜索编排 (637行)
    sync.py                      # 转存逻辑 (839行)
    subscribe.py                 # 订阅管理 (322行)
    api.py                       # 外部 API (128行)
  ui/
    __init__.py                  # 导出: UIConfig
    config.py                    # 配置表单 (735行)
  utils/
    __init__.py                  # 导出 file_matcher 和 tools
    file_matcher.py              # 文件匹配 + 订阅过滤 (493行)
    tools.py                     # HDHive 工具 + 格式转换 (680行)
```

## 当前三源架构

优先级: Nullbr > HDHive > PanSou

- **Nullbr**: REST API，TMDB ID 精准查询，3 个配置项
- **HDHive**: API/Playwright 双模式，积分解锁，13 个配置项
- **PanSou**: 聚合搜索，通过 `channels` 参数间接访问 TG 频道，6 个配置项

## 搜索接口统一输出格式

```python
{"url": "...", "title": "...", "update_time": "..."}
```

## 关键发现

1. 无现有 Telegram 客户端代码
2. PanSou 的 `channels` 参数已展示 TG 频道搜索模式
3. 需移除 ~20 个旧配置项，新增 ~6 个 Telegram 配置项
4. `utils/tools.py` 中 ~680 行代码大部分与 HDHive 相关，可大幅精简
