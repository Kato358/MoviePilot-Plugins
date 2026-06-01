# ADR-0001: 搜索源替换为纯 Telegram 频道

- 状态: 已接受
- 日期: 2026-06-01
- 决策者: kato

## 背景

P115StrgmSub 插件原有两个外部搜索源：

- **Nullbr**: 基于 TMDB ID 精准查询 115 网盘资源
- **HDHive**: 支持 Playwright/API 双模式，含积分解锁付费资源
- **PanSou**: 网盘聚合搜索，底层通过 Telegram 频道获取资源

这三个搜索源增加了配置复杂度（每个需要独立的 API Key/Cookie）、代码复杂度（三个客户端 + 多源回退编排）和维护负担（HDHive 的 Cookie 刷新、签到、积分管理）。

## 决策

替换全部搜索源为 **纯 Telegram 频道**方案，包含双模式：

1. **HTTP 模式（默认）**: 通过 `t.me/s/<channel_name>` 抓取公开频道消息，增量存储到 SQLite，本地关键词搜索。零配置开箱即用。
2. **MTProto 模式（增强）**: 通过 Telethon 连接 Telegram，支持服务端搜索全部历史消息。首次需扫码登录。

目标频道：
- gimy115（剧迷热更频道）
- QukanMovie（115 影视资源分享频道）
- yingshiziyuanpindao（星河频道）

## 理由

1. **简化配置**: 用户只需配置频道名称，无需多个 API Key/Cookie
2. **降低维护成本**: 移除 Nullbr/HDHive/PanSou 三个客户端及相关工具函数（Cookie 刷新、签到、积分管理）
3. **功能不损失**: PanSou 本质就是 TG 频道聚合搜索，直接从源头获取是上位替代
4. **TMDB 精准性由框架保证**: MoviePilot 的 `recognize_media` 提供下游媒体识别，不依赖搜索源的精准性
5. **双模式覆盖不同用户**: 新手零配置用 HTTP，高级用户扫码解锁 MTProto

## 后果

### 正面
- 代码量大幅减少（预计减少 ~40%）
- 配置项从 20+ 减少到 ~6 个
- 不再依赖外部付费服务（Nullbr API Key、HDHive 账号）

### 负面
- 失去 TMDB ID 精准搜索能力（Nullbr），依赖标题匹配 + 下游识别兜底
- 失去付费资源解锁能力（HDHive 积分系统）
- 失去 HDHive 签到功能
- 首次 HTTP 抓取需要时间建立本地消息索引
- MTProto 模式有 Telegram 账号风控风险

### 风险缓解
- 标题误匹配 → 下游 `recognize_media` + `FileMatcher` 双层验证
- HTTP 抓取慢 → 增量抓取，仅首次全量
- Telegram 风控 → HTTP 模式零风险，MTProto 模式用户自行承担
