# Issue #3 — 通用 Agent / IM Gateway 接入协议

## 目标

定义平台无关的本地调用协议。用户自己的 IM Gateway 或 AI Agent 负责平台鉴权、收发消息；本项目只规范化消息、调用 `backend/service.py` 并返回结果。

## 契约

请求 JSON：`message`（原文）、可选稳定 `request_id`、可选 `message_at`、`timezone`、可选安全 `attachments` 元数据。没有稳定消息 ID 时省略 `request_id`，不得伪造。

响应 JSON：`ok`、`markdown`、`event_ids`、`duplicate`、`error`、`kind`。适配层不保存 Token、chat ID、原始平台标识或原始消息日志。

## 边界

- 适配层复用 `CalorieService.handle_message`，不复制营养或 JSONL 逻辑。
- 只提供 stdio JSON Lines CLI；不扩展 dashboard HTTP 写路由。
- 闲聊或意图不明确的消息由 service 返回 ignored，不能写入。
- 重试必须复用调用方提供的稳定 request_id。
- 附件只保留最小元数据，供 Issue #4 的候选识别流使用；不保存图片二进制或公网永久 URL。
