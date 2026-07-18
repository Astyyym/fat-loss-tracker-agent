# Issue #2 — 首次启动档案与计划配置短计划

**需求依据：** `docs/需求/Issue_2_首次启动档案与计划配置_PRD.md`

## 任务 1：档案数据与计划计算
- 文件：`backend/service.py`、`profile.example.json`、`.gitignore`、服务测试。
- 步骤：定义 `profile.json` schema、校验、日期/周数归一化、旧 `config.json` 迁移、原子写入、损坏档案备份恢复。
- 验证：单元测试覆盖正常、错误、迁移、目标修改和 JSONL 不变。

## 任务 2：受限 localhost 配置 API
- 文件：`backend/server.py`、服务 API 测试。
- 步骤：提供档案状态读取、创建、更新和损坏档案恢复的严格 JSON 接口；保持服务绑定 127.0.0.1，不开放事件写入。
- 验证：API 正常与非法请求有 2xx/4xx 测试，响应不泄露路径或原始档案内容。

## 任务 3：首次设置与仪表盘动态渲染
- 文件：`frontend/index.html`、`frontend/app.js`、`frontend/styles.css`。
- 步骤：无档案显示向导；有档案显示动态计划数据和修改入口；移除固定默认目标；显示当前计划口径说明。
- 验证：浏览器冒烟：设置 → 刷新 → 修改目标；前端不出现 LocalStorage。

## 任务 4：文档与全量验收
- 文件：README、Prompt、Skill、需求文档与本短计划。
- 步骤：说明本地私有档案、迁移和估算建议边界；运行全量测试、差异检查、隐私扫描、Windows 启动与 API 冒烟。
- 验证：提交推送 `main` 后关闭 Issue #2，关闭说明附验证证据。
