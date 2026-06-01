# 搜索源替换为纯 Telegram 频道

## Goal

将 P115StrgmSub 插件的搜索源从 Nullbr + HDHive + PanSou 三源架构，替换为纯 Telegram 频道方案（HTTP + MTProto 双模式）。大幅简化配置和代码复杂度。

## 背景

ADR-0001 已被接受，决策方向明确。详细需求见 `../06-01-telegram/prd.md`（本任务与其合并）。

## 决策（ADR-lite）

**Context**: 三个搜索源增加配置复杂度、代码复杂度和维护负担
**Decision**: 替换为纯 Telegram 频道方案（HTTP 默认 + MTProto 可选增强）
**Consequences**: 代码量减少 ~40%，配置项从 20+ 减少到 ~6 个，失去 TMDB ID 精准搜索和付费资源解锁能力

## Requirements

完整需求文档: [`../06-01-telegram/prd.md`](../06-01-telegram/prd.md)

核心要点:
- 新建 `clients/telegram.py` — 双模式 Telegram 客户端（HTTP + MTProto）
- 新建 `utils/message_parser.py` — 频道消息解析器
- 改造 `handlers/search.py` — 仅 Telegram 搜索
- 精简 `handlers/sync.py` — 移除 HDHive 延迟解锁
- 更新 `ui/config.py` — Telegram 配置项
- 精简 `__init__.py` — 移除旧源初始化
- 清理 `utils/tools.py` — 移除 HDHive 工具函数
- 删除 `clients/pansou.py`, `clients/nullbr.py`

## Acceptance Criteria

- [ ] HTTP 模式零配置可搜索三个频道的 115 资源
- [ ] MTProto 模式扫码登录后可搜索历史消息
- [ ] 搜索结果正确提取 115 链接和资源标题
- [ ] 电视剧/电影搜索关键词降级正常
- [ ] 搜索结果与 SyncHandler 正确集成
- [ ] 所有 Nullbr/HDHive/PanSou 相关代码已清除
- [ ] 配置页面仅显示 Telegram 相关配置项
- [ ] 版本号更新

## Definition of Done

- Lint / type-check 通过
- 版本号更新
- 变更日志更新

## Out of Scope

- 洗版模式评分优化（由 SubscribeFilter 现有逻辑处理）
- 多频道格式自动检测（当前仅适配 gimy115/QukanMovie/yingshiziyuanpindao）

## Technical Notes

- 研究文件: [`research/codebase-structure.md`](research/codebase-structure.md)
- 插件根目录: `plugins.v2/p115strgmsub/`
- Spec 文件: `.trellis/spec/plugin/` 下的各指南文档
- 现有依赖: `p115client`, `playwright-stealth`；新增 `telethon`, `beautifulsoup4`
- 关键接口: SearchHandler 统一输出格式 `{"url", "title", "update_time"}`
