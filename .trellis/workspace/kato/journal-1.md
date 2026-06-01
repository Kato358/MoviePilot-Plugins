# Journal - kato (Part 1)

> AI development session journal
> Started: 2026-06-01

---

## 2026-06-01 — Bootstrap Guidelines 完成

完成 `.trellis/spec/` 规范文档填充。

**关键决策**: 原始模板是前端项目（React/Vue），但实际项目是 MoviePilot Python 插件。将 `plugin/` 目录从前端规范重构为插件开发规范，删除不适用的模板文件（component-guidelines、hook-guidelines、state-management、type-safety），新增 plugin-lifecycle、client-guidelines、handler-guidelines、config-and-ui、data-access、event-system。

**产出文件** (8 个 plugin spec + 3 个 guides):
- `plugin/index.md` — 总索引
- `plugin/directory-structure.md` — 模块布局
- `plugin/plugin-lifecycle.md` — 插件必备方法
- `plugin/client-guidelines.md` — 客户端封装
- `plugin/handler-guidelines.md` — 处理器编排
- `plugin/config-and-ui.md` — 配置与 UI
- `plugin/data-access.md` — 数据库操作
- `plugin/event-system.md` — 事件机制
- `plugin/quality-guidelines.md` — 质量规范
- `guides/index.md` — 更新为项目相关内容

