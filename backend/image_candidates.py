"""Provider-neutral food image candidate confirmation flow; no model SDK or image storage."""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any

from backend.service import CalorieService, ServiceError, TZ_NAME

SOURCES = {"meal_photo", "nutrition_label", "menu_screenshot"}
CONFIDENCE = {"high", "medium", "low"}
MEALS = {"早餐", "午餐", "晚餐", "加餐", "放纵餐"}


class CandidateStore:
    def __init__(self, service: CalorieService):
        self.service = service
        self.path = service.root / "runtime" / "pending-candidates.json"

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ServiceError("待确认候选文件损坏，请清理 runtime 后重试") from exc
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".pending-", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, separators=(",", ":")); fh.flush(); os.fsync(fh.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def _prune(self, data: dict[str, Any]) -> dict[str, Any]:
        now = self.service.now()
        return {key: value for key, value in data.items() if dt.datetime.fromisoformat(value["expires_at"]) > now}

    def submit(self, candidate: dict[str, Any], request_id: str | None = None) -> dict[str, Any]:
        normalized = validate_candidate(candidate)
        data = self._prune(self._load())
        if request_id:
            for pending_id, old in data.items():
                if old.get("request_id") == request_id:
                    return {"pending_id": pending_id, "candidate": old["candidate"], "duplicate": True}
        pending_id = uuid.uuid4().hex
        now = self.service.now()
        data[pending_id] = {"candidate": normalized, "request_id": request_id, "created_at": now.isoformat(), "expires_at": (now + dt.timedelta(hours=24)).isoformat()}
        self._save(data)
        return {"pending_id": pending_id, "candidate": normalized, "duplicate": False}

    def confirm(self, pending_id: str, corrections: dict[str, Any] | None, request_id: str | None = None) -> dict[str, Any]:
        data = self._prune(self._load())
        entry = data.get(pending_id)
        if not entry:
            raise ServiceError("待确认候选不存在或已过期")
        candidate = dict(entry["candidate"])
        if corrections:
            candidate.update(corrections)
        candidate = validate_candidate(candidate)
        rid = request_id or entry.get("request_id")
        if rid and self.service.find_request(rid):
            existing = self.service.find_request(rid)
            return {"event_ids": [event["id"] for event in existing], "duplicate": True}
        event = self.service._event_base("food", "图片候选确认", rid)
        now = self.service.now()
        date = candidate.get("date") or now.date().isoformat()
        time = candidate.get("time") or now.strftime("%H:%M")
        items = [{"name": item["name"], "quantity": item["quantity"], "estimated_calories": item["estimated_calories"], "estimated_protein_g": item["estimated_protein_g"], "confidence": candidate["confidence"], "nutrition_source": "image_candidate", "notes": "; ".join(candidate["assumptions"])} for item in candidate["items"]]
        event.update({"date": date, "time": time, "meal_label": candidate.get("meal_label") or "加餐", "items": items, "estimated_total_calories": sum(item["estimated_calories"] for item in items), "estimated_total_protein_g": sum(item["estimated_protein_g"] for item in items), "confidence": candidate["confidence"], "nutrition_source": "image_candidate", "notes": "图片候选经用户确认；假设：" + "; ".join(candidate["assumptions"])})
        saved = self.service.append_event(event)
        self.service.rebuild_derived(saved["date"])
        data.pop(pending_id, None); self._save(data)
        return {"event_ids": [saved["id"]], "duplicate": False}


def validate_candidate(candidate: Any) -> dict[str, Any]:
    if not isinstance(candidate, dict) or candidate.get("source_type") not in SOURCES or candidate.get("confidence") not in CONFIDENCE:
        raise ServiceError("候选必须包含有效 source_type 和 confidence")
    items = candidate.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 20:
        raise ServiceError("候选 items 必须为 1–20 项")
    clean_items = []
    for item in items:
        if not isinstance(item, dict) or not all(isinstance(item.get(key), str) and item[key].strip() for key in ("name", "quantity")):
            raise ServiceError("候选食物必须有名称和份量")
        for key, maximum in (("estimated_calories", 10000), ("estimated_protein_g", 1000)):
            value = item.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= maximum:
                raise ServiceError("候选营养数值无效")
        clean_items.append({"name": item["name"].strip()[:120], "quantity": item["quantity"].strip()[:120], "estimated_calories": float(item["estimated_calories"]), "estimated_protein_g": float(item["estimated_protein_g"])})
    assumptions = candidate.get("assumptions", [])
    if not isinstance(assumptions, list) or any(not isinstance(item, str) or len(item) > 200 for item in assumptions):
        raise ServiceError("assumptions 必须是有限长度文本数组")
    result = {"source_type": candidate["source_type"], "confidence": candidate["confidence"], "items": clean_items, "assumptions": assumptions}
    if candidate.get("meal_label") in MEALS: result["meal_label"] = candidate["meal_label"]
    for key in ("date", "time"):
        if candidate.get(key): result[key] = str(candidate[key])
    return result
