"""平台无关的 Agent / IM Gateway stdio JSON Lines 适配层。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.image_candidates import CandidateStore
from backend.service import CalorieService, ServiceError, TZ_NAME


def normalize_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ServiceError("请求必须是 JSON 对象")
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise ServiceError("message 必须是非空文本")
    request_id = payload.get("request_id")
    if request_id is not None and (not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 256):
        raise ServiceError("request_id 必须是长度不超过 256 的非空文本")
    timezone = payload.get("timezone", TZ_NAME)
    if timezone != TZ_NAME:
        raise ServiceError(f"当前仅支持 timezone={TZ_NAME}")
    message_at = payload.get("message_at")
    if message_at is not None and (not isinstance(message_at, str) or len(message_at) > 64):
        raise ServiceError("message_at 必须是长度不超过 64 的文本")
    attachments = payload.get("attachments", [])
    if not isinstance(attachments, list) or len(attachments) > 10:
        raise ServiceError("attachments 必须是最多 10 项的数组")
    safe_attachments = []
    for item in attachments:
        if not isinstance(item, dict):
            raise ServiceError("attachment 必须是对象")
        kind = item.get("kind")
        reference = item.get("reference")
        if kind not in {"image", "file", "other"} or not isinstance(reference, str) or not reference or len(reference) > 128:
            raise ServiceError("attachment 只能包含 kind 和有限长度的 reference")
        safe_attachments.append({"kind": kind, "reference": reference})
    return {"message": message.strip(), "request_id": request_id.strip() if request_id else None, "message_at": message_at, "timezone": timezone, "attachments": safe_attachments}


def process_payload(service: CalorieService, payload: Any) -> dict[str, Any]:
    try:
        if not isinstance(payload, dict):
            raise ServiceError("请求必须是 JSON 对象")
        operation = payload.get("operation", "message")
        if operation == "candidate_submit":
            stored = CandidateStore(service).submit(payload.get("candidate"), payload.get("request_id"))
            return {"ok": True, "markdown": "已生成候选，等待用户确认或修正后才会写入记录。", "event_ids": [], "duplicate": stored["duplicate"], "error": None, "kind": "candidate_pending", "pending_id": stored["pending_id"], "candidate": stored["candidate"]}
        if operation == "candidate_confirm":
            result = CandidateStore(service).confirm(payload.get("pending_id", ""), payload.get("corrections"), payload.get("request_id"))
            return {"ok": True, "markdown": "已按确认后的候选写入饮食记录。", "event_ids": result["event_ids"], "duplicate": result["duplicate"], "error": None, "kind": "food"}
        request = normalize_request(payload)
        result = service.handle_message(request["message"], request["request_id"], html_enabled=False)
        return {"ok": result.ok, "markdown": result.markdown, "event_ids": result.event_ids or [], "duplicate": result.duplicate, "error": None if result.ok else result.markdown, "kind": result.kind}
    except ServiceError as exc:
        return {"ok": False, "markdown": "", "event_ids": [], "duplicate": False, "error": str(exc), "kind": "error"}


def main() -> int:
    parser = argparse.ArgumentParser(description="读取 stdin JSONL 的通用减脂记录 Agent 适配器")
    parser.add_argument("--root", help="测试或本地项目根目录")
    args = parser.parse_args()
    service = CalorieService(Path(args.root) if args.root else None)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            response = {"ok": False, "markdown": "", "event_ids": [], "duplicate": False, "error": "请求必须是有效 JSON", "kind": "error"}
        else:
            response = process_payload(service, payload)
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
