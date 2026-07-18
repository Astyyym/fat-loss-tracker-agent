# Issue #4 — 图片候选确认与记录短计划

1. 新增候选模块：严格候选 schema、本地 pending 存储、TTL、HTML 安全展示与确认/修正。
2. 为图片餐、标签、菜单、多食物、错误/模糊结果、重放、恶意文本及确认前不写 JSONL 添加 fixture 测试。
3. 将通用适配器扩展为 candidate submit/confirm 两种操作；不接真实视觉 SDK 或网络。
4. 全量测试、CLI 候选→确认冒烟、Git/隐私扫描后提交、推送、关闭 Issue #4。
