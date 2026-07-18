# Issue #4 — 图片候选识别、确认与记录

## 目标

项目只接收用户已有视觉 Agent 产生的 provider-neutral 候选结果；候选必须先被用户确认或修正，才调用 `backend/service.py` 写入 food 事件。

## 候选结构

- `source_type`：`meal_photo`、`nutrition_label`、`menu_screenshot`
- `items[]`：名称、份量、热量、蛋白质
- 可选餐次与业务日期/时间
- `confidence`：high / medium / low
- `assumptions[]`
- 可选最小附件 reference（不保存图片二进制或公网永久 URL）

## 确认状态机

候选提交 → 返回 pending_id 与可显示候选 → 用户确认或带修正确认 → 校验后的 food event → `service.append_event`。

无论置信度高低，都不得静默写入。`request_id` 重放只产生一次最终记录。暂存候选仅保存在本地 Git 忽略 runtime 目录，设置 TTL，并不保存原图。
