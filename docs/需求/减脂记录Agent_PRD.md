# 减脂记录 Agent 当前版本需求文档

> 历史基线：本文件原用于 2026-07-17 的仓库规范化与 Windows-only 文档收敛，相关工作已完成并记录在 Git 历史与 `开发短计划/公开仓库通用化_完成记录.md`。

## 已完成的产品基线

- 项目定位为本地优先、单用户的饮食、运动与身体测量记录工具。
- Windows 本地目录是唯一正式源码位置；公开 README、Prompt 与 Skill 只说明 Windows 本地使用方式。
- `backend/service.py` 是唯一业务和数据写入入口；JSONL 事件保持追加式，纠错、删除与恢复均追加事件。
- 仪表盘只绑定 localhost；运行日志统一收纳到 `runtime/logs/` 并由 Git 忽略。
- GitHub Issue #1–#4 是此后逐步实现的功能路线，不属于历史规范化提交。

## 后续需求文档

后续功能以独立需求和短计划执行：

- [Issue #1 Windows 本地回归验收 PRD](Issue_1_Windows本地回归验收_PRD.md)
- Issue #2：首次启动档案与计划配置
- Issue #3：通用 IM Gateway / AI Agent 接入协议
- Issue #4：图片候选识别、确认与记录

## 持续约束

- 真实健康数据、`config.json`、`profile.json`、数据备份、摘要、卡片、运行日志和 `.env*` 必须保持本地且被 Git 忽略。
- 公开代码、README、Prompt、Skill 和测试不得包含真实 Token、chat ID、个人绝对路径或真实健康记录。
- 每个新增功能必须先有需求文档和开发短计划；测试、Git 检查与平台冒烟验证通过后才提交和推送。
- 不创建第二个 Telegram Bot；不直接编辑、删除或上传真实 JSONL 健康记录。
- 不恢复 Linux、WSL 或 macOS 的公开运行教程，除非将来另行确认产品支持范围。
