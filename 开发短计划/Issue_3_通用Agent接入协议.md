# Issue #3 — 通用 Agent 接入协议短计划

1. 新增 `backend/agent_adapter.py`：stdin JSONL → 严格 schema → `CalorieService.handle_message` → stdout JSONL。
2. 为 request_id、无 ID、重复投递、ignored 消息、附件元数据与错误 JSON 添加测试。
3. 更新 README 与公开 Skill：Windows `py -3` 调用、无 Token/平台 SDK、附件仅为元数据。
4. 全量测试、`git diff --check`、CLI 管道冒烟后提交、推送、关闭 Issue #3。
