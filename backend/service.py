"""单用户减脂记录 Agent 的唯一业务与数据读写入口。仅使用 Python 标准库。"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import html
import json
import os
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

TZ_NAME = "Asia/Shanghai"
TZ = ZoneInfo(TZ_NAME)
DEFAULT_SETTINGS = {
    "program_weeks": 4,
    "calorie_target_kcal": 1800.0,
    "training_day_calorie_max_kcal": 1900.0,
    "minimum_recommended_calories_kcal": 1500.0,
    "protein_target_g": 130.0,
    "protein_min_g": 120.0,
    "protein_max_g": 140.0,
    "timezone": TZ_NAME,
}
ALLOWED_TYPES = {"food", "exercise", "body_measurement", "correction", "delete", "restore"}
CONFIDENCE = {"high", "medium", "low"}
MEALS = {"早餐", "午餐", "晚餐", "加餐", "放纵餐"}

TEMPLATES: dict[str, dict[str, Any]] = {
    "标准早餐A": {"id": "breakfast-a", "meal": "早餐", "cal": 290, "protein": 20, "confidence": "medium", "items": [("鸡蛋", "2个", 140, 12), ("燕麦", "40g", 150, 8), ("黑咖啡", "1杯", 0, 0)]},
    "标准早餐B": {"id": "breakfast-b", "meal": "早餐", "cal": 300, "protein": 18, "confidence": "medium", "items": [("鸡蛋", "2个", 140, 12), ("玉米", "1根", 160, 6), ("黑咖啡", "1杯", 0, 0)]},
    "标准早餐C": {"id": "breakfast-c", "meal": "早餐", "cal": 360, "protein": 24, "confidence": "medium", "items": [("无糖酸奶", "200g", 120, 10), ("燕麦", "40g", 150, 8), ("鸡蛋", "1个", 90, 6)]},
    "红薯早餐": {"id": "sweet-potato-breakfast", "meal": "早餐", "cal": 330, "protein": 18, "confidence": "medium", "items": [("鸡蛋", "2个", 140, 12), ("红薯", "1个", 190, 6), ("咖啡", "1杯", 0, 0)]},
    "鸡胸饭标准版": {"id": "chicken-rice-standard", "meal": "午餐", "cal": 520, "protein": 42, "confidence": "medium", "items": [("鸡胸", "150g熟重", 250, 35), ("米饭", "半碗熟重", 180, 4), ("西兰花/青菜", "1份", 90, 3)]},
    "牛肉饭标准版": {"id": "beef-rice-standard", "meal": "午餐", "cal": 580, "protein": 38, "confidence": "medium", "items": [("瘦牛肉", "150g熟重", 330, 32), ("米饭", "半碗熟重", 180, 4), ("青菜", "1份", 70, 2)]},
    "虾仁饭标准版": {"id": "shrimp-rice-standard", "meal": "午餐", "cal": 480, "protein": 36, "confidence": "medium", "items": [("虾仁", "150g熟重", 220, 30), ("米饭", "半碗熟重", 180, 4), ("西兰花", "1份", 80, 2)]},
    "鸡腿饭标准版": {"id": "chicken-leg-rice-standard", "meal": "午餐", "cal": 560, "protein": 35, "confidence": "medium", "items": [("去皮鸡腿", "150g熟重", 300, 29), ("米饭", "半碗熟重", 180, 4), ("青菜", "1份", 80, 2)]},
    "外卖减脂饭": {"id": "takeout-cutting-rice", "meal": "午餐", "cal": 650, "protein": 35, "confidence": "medium", "items": [("少饭鸡肉/牛肉饭", "1份", 650, 35)]},
    "虾仁豆腐汤": {"id": "shrimp-tofu-soup", "meal": "晚餐", "cal": 350, "protein": 35, "confidence": "medium", "items": [("虾仁豆腐汤", "1份", 350, 35)]},
    "鱼片晚餐": {"id": "fish-dinner", "meal": "晚餐", "cal": 420, "protein": 35, "confidence": "medium", "items": [("鱼片+青菜+少量主食", "1份", 420, 35)]},
    "鸡胸沙拉晚餐": {"id": "chicken-salad-dinner", "meal": "晚餐", "cal": 430, "protein": 32, "confidence": "medium", "items": [("鸡胸沙拉+红薯", "1份", 430, 32)]},
    "豆腐鸡蛋汤": {"id": "tofu-egg-soup", "meal": "晚餐", "cal": 300, "protein": 22, "confidence": "medium", "items": [("豆腐鸡蛋汤", "1份", 300, 22)]},
    "清淡收尾餐": {"id": "light-finisher", "meal": "晚餐", "cal": 350, "protein": 30, "confidence": "medium", "items": [("鱼/豆腐+蔬菜", "1份", 350, 30)]},
    "酸奶加餐": {"id": "yogurt-snack", "meal": "加餐", "cal": 120, "protein": 10, "confidence": "medium", "items": [("无糖酸奶", "200g", 120, 10)]},
    "牛奶加餐": {"id": "milk-snack", "meal": "加餐", "cal": 150, "protein": 8, "confidence": "medium", "items": [("纯牛奶", "250ml", 150, 8)]},
    "鸡蛋加餐": {"id": "egg-snack", "meal": "加餐", "cal": 70, "protein": 6, "confidence": "medium", "items": [("鸡蛋", "1个", 70, 6)]},
    "水果加餐": {"id": "fruit-snack", "meal": "加餐", "cal": 100, "protein": 1, "confidence": "low", "items": [("水果", "1个", 100, 1)]},
    "蛋白粉一份": {"id": "protein-powder-serving", "meal": "加餐", "cal": 120, "protein": 24, "confidence": "medium", "items": [("蛋白粉", "1勺", 120, 24)]},
}
TEMPLATE_VERSION = "2026-07-01"


class ServiceError(Exception):
    pass


class DataCorruptionError(ServiceError):
    def __init__(self, path: Path, line: int, detail: str):
        super().__init__(f"数据文件损坏：{path.name} 第 {line} 行无法解析（{detail}）。已停止读取，未吞掉此前有效数据。")
        self.path, self.line = path, line


@dataclass
class ServiceResult:
    ok: bool
    markdown: str
    kind: str = "message"
    data: dict[str, Any] | None = None
    event_ids: list[str] | None = None
    duplicate: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "markdown": self.markdown, "kind": self.kind, "data": self.data or {}, "event_ids": self.event_ids or [], "duplicate": self.duplicate}


class CalorieService:
    def __init__(self, root: str | Path | None = None, now_fn=None):
        self.root = Path(root) if root else Path(__file__).resolve().parents[1]
        self.now_fn = now_fn or (lambda: dt.datetime.now(TZ))
        self.data_dir = self.root / "data"
        self.summary_dir = self.root / "summaries"
        self.cards_dir = self.root / "cards"
        self.backup_dir = self.root / "backups"
        self.config_path = self.root / "config.json"
        self.settings = self._load_settings()
        self.program_weeks = int(self.settings["program_weeks"])
        self.calorie_target = float(self.settings["calorie_target_kcal"])
        self.training_calorie_max = float(self.settings["training_day_calorie_max_kcal"])
        self.minimum_calories = float(self.settings["minimum_recommended_calories_kcal"])
        self.protein_target = float(self.settings["protein_target_g"])
        self.protein_min = float(self.settings["protein_min_g"])
        self.protein_max = float(self.settings["protein_max_g"])
        for directory in (self.data_dir, self.summary_dir, self.cards_dir, self.backup_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.lock_path = self.data_dir / ".write.lock"

    def _load_settings(self) -> dict[str, Any]:
        settings = dict(DEFAULT_SETTINGS)
        if self.config_path.exists():
            try:
                loaded = json.loads(self.config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ServiceError(f"config.json 无法解析：{exc.msg}") from exc
            if not isinstance(loaded, dict):
                raise ServiceError("config.json 必须是 JSON 对象")
            settings.update(loaded)
        numeric_ranges = {
            "program_weeks": (1, 104),
            "calorie_target_kcal": (800, 5000),
            "training_day_calorie_max_kcal": (800, 6000),
            "minimum_recommended_calories_kcal": (500, 5000),
            "protein_target_g": (20, 500),
            "protein_min_g": (0, 500),
            "protein_max_g": (20, 600),
        }
        for key, (low, high) in numeric_ranges.items():
            value = settings.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= float(value) <= high:
                raise ServiceError(f"config.json 的 {key} 必须在 {low}–{high} 范围内")
        if settings.get("timezone") != TZ_NAME:
            raise ServiceError(f"当前仅支持 timezone={TZ_NAME}")
        if float(settings["protein_min_g"]) > float(settings["protein_target_g"]) or float(settings["protein_target_g"]) > float(settings["protein_max_g"]):
            raise ServiceError("蛋白质范围必须满足 protein_min_g ≤ protein_target_g ≤ protein_max_g")
        return settings

    def now(self) -> dt.datetime:
        value = self.now_fn()
        return value.astimezone(TZ) if value.tzinfo else value.replace(tzinfo=TZ)

    @contextlib.contextmanager
    def _write_lock(self, timeout: float = 15.0, stale_after: float = 120.0):
        """项目内排他锁，避免依赖平台专用锁 API。"""
        deadline = time.monotonic() + timeout
        token = f"{os.getpid()}:{uuid.uuid4().hex}"
        while True:
            try:
                fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as lock:
                    json.dump({"token": token, "pid": os.getpid(), "created_at": time.time()}, lock)
                    lock.flush()
                    os.fsync(lock.fileno())
                break
            except FileExistsError:
                try:
                    age = time.time() - self.lock_path.stat().st_mtime
                    if age > stale_after:
                        self.lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise ServiceError("数据文件正被另一个进程写入，请稍后重试")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                current = json.loads(self.lock_path.read_text(encoding="utf-8"))
                if current.get("token") == token:
                    self.lock_path.unlink(missing_ok=True)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                pass

    def _year_path(self, year: int | str) -> Path:
        return self.data_dir / f"{int(year):04d}.jsonl"

    def read_events(self, year: int | str) -> list[dict[str, Any]]:
        path = self._year_path(year)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        seen: set[str] = set()
        with path.open("r", encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    self._backup(path)
                    raise DataCorruptionError(path, number, exc.msg) from exc
                try:
                    self.validate_event(event, existing_ids=seen, reading=True)
                except ServiceError as exc:
                    self._backup(path)
                    raise DataCorruptionError(path, number, str(exc)) from exc
                if event["id"] in seen:
                    self._backup(path)
                    raise DataCorruptionError(path, number, f"重复 id {event['id']}")
                seen.add(event["id"])
                events.append(event)
        return events

    def read_all_events(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for path in sorted(self.data_dir.glob("[0-9][0-9][0-9][0-9].jsonl")):
            result.extend(self.read_events(path.stem))
        return result

    def validate_event(self, event: dict[str, Any], existing_ids: set[str] | None = None, reading: bool = False) -> None:
        required = {"id", "created_at", "timezone", "entry_type", "raw_text"}
        missing = required - set(event)
        if missing:
            raise ServiceError(f"事件缺少字段：{', '.join(sorted(missing))}")
        try:
            uuid.UUID(str(event["id"]))
        except ValueError as exc:
            raise ServiceError("事件 id 必须是 UUID") from exc
        try:
            created = dt.datetime.fromisoformat(event["created_at"])
            if created.utcoffset() is None:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ServiceError("created_at 必须是带时区偏移的 ISO 8601") from exc
        if event["timezone"] != TZ_NAME or event["entry_type"] not in ALLOWED_TYPES:
            raise ServiceError("timezone 或 entry_type 无效")
        et = event["entry_type"]
        if et in {"food", "exercise", "body_measurement"}:
            self._validate_date_time(event)
        if et == "food":
            for field in ("meal_label", "items", "estimated_total_calories", "estimated_total_protein_g", "confidence", "nutrition_source"):
                if field not in event:
                    raise ServiceError(f"food 缺少字段 {field}")
            if event["meal_label"] not in MEALS or not isinstance(event["items"], list) or not event["items"]:
                raise ServiceError("food 的餐次或 items 无效")
            self._range(event["estimated_total_calories"], 0, 10000, "热量")
            self._range(event["estimated_total_protein_g"], 0, 1000, "蛋白质")
            if event["confidence"] not in CONFIDENCE:
                raise ServiceError("置信度无效")
            for item in event["items"]:
                for field in ("name", "quantity", "estimated_calories", "estimated_protein_g", "confidence", "nutrition_source"):
                    if field not in item:
                        raise ServiceError(f"food item 缺少字段 {field}")
                self._range(item["estimated_calories"], 0, 10000, "食材热量")
                self._range(item["estimated_protein_g"], 0, 1000, "食材蛋白质")
        elif et == "exercise":
            for field in ("exercise_type", "duration_minutes", "completion_status"):
                if field not in event:
                    raise ServiceError(f"exercise 缺少字段 {field}")
            self._range(event["duration_minutes"], 0, 1440, "运动时长")
            if event["completion_status"] not in {"completed", "partial", "rest", "skipped"}:
                raise ServiceError("运动完成状态无效")
        elif et == "body_measurement":
            if event.get("measurement_type") not in {"weight", "waist"}:
                raise ServiceError("体测类型无效")
            ranges = {"weight": (25, 300, "kg"), "waist": (30, 250, "cm")}
            low, high, unit = ranges[event["measurement_type"]]
            self._range(event.get("value"), low, high, "体测数值")
            if event.get("unit") != unit:
                raise ServiceError(f"{event['measurement_type']} 单位必须是 {unit}")
        else:
            if not event.get("target_id"):
                raise ServiceError(f"{et} 缺少 target_id")
            if et == "correction" and not isinstance(event.get("patch"), dict):
                raise ServiceError("correction 缺少 patch")

    @staticmethod
    def _validate_date_time(event: dict[str, Any]) -> None:
        try:
            dt.date.fromisoformat(event["date"])
            dt.time.fromisoformat(event["time"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError("date/time 格式必须为 YYYY-MM-DD / HH:mm") from exc
        if not re.fullmatch(r"\d{2}:\d{2}", event["time"]):
            raise ServiceError("time 格式必须为 HH:mm")

    @staticmethod
    def _range(value: Any, low: float, high: float, name: str) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= float(value) <= high:
            raise ServiceError(f"{name}超出合理范围 {low}–{high}")

    def _backup(self, path: Path) -> Path | None:
        if not path.exists():
            return None
        stamp = self.now().strftime("%Y%m%d-%H%M%S-%f")
        dest_dir = self.backup_dir / path.stem
        dest_dir.mkdir(parents=True, exist_ok=True)
        # UUID 后缀避免同一时刻连续备份互相覆盖，尤其是执行恢复前的保护备份。
        dest = dest_dir / f"{path.stem}-{stamp}-{uuid.uuid4().hex[:8]}.jsonl"
        shutil.copy2(path, dest)
        backups = sorted(dest_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in backups[30:]:
            old.unlink(missing_ok=True)
        return dest

    def append_event(self, event: dict[str, Any], year: int | None = None, simulate_interrupt: bool = False,
                     allow_duplicate: bool = False) -> dict[str, Any]:
        self.validate_event(event)
        target_year = year or (int(event["date"][:4]) if "date" in event else None)
        if target_year is None:
            raise ServiceError("更正类事件必须明确写入目标记录所在年份")
        path = self._year_path(target_year)
        with self._write_lock():
            existing = self.read_events(target_year)
            request_id = str(event.get("request_id", ""))
            if request_id:
                prior = next((e for e in existing if str(e.get("request_id", "")) == request_id), None)
                if prior:
                    return prior
            ids = {e["id"] for e in existing}
            if event["id"] in ids:
                raise ServiceError("事件 id 已存在")
            if event["entry_type"] == "food" and not allow_duplicate:
                current = self.project(existing)
                event_time = dt.time.fromisoformat(event["time"])
                for old in reversed([e for e in current if e["entry_type"] == "food" and e["date"] == event["date"]]):
                    old_time = dt.time.fromisoformat(old["time"])
                    seconds = abs((dt.datetime.combine(dt.date.min, event_time) - dt.datetime.combine(dt.date.min, old_time)).total_seconds())
                    same_template = event.get("template_id") and event.get("template_id") == old.get("template_id")
                    same_content = event["raw_text"] == old["raw_text"] and event["estimated_total_calories"] == old["estimated_total_calories"]
                    if seconds <= 7200 and (same_template or same_content):
                        raise ServiceError(f"可能已记录：{old['date']} {old['time']} {old['meal_label']}，本次未重复写入。")
            if event["entry_type"] in {"correction", "delete", "restore"}:
                target = next((e for e in existing if e["id"] == event["target_id"]), None)
                if not target or target["entry_type"] not in {"food", "exercise", "body_measurement"}:
                    raise ServiceError("target_id 不存在、跨年度或类型不匹配")
                self._validate_lifecycle_action(event, existing)
            payload = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"
            fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=self.data_dir)
            try:
                with os.fdopen(fd, "wb") as out:
                    if path.exists():
                        with path.open("rb") as src:
                            shutil.copyfileobj(src, out)
                    out.write(payload.encode("utf-8"))
                    out.flush()
                    os.fsync(out.fileno())
                if simulate_interrupt:
                    raise OSError("simulated interruption before atomic replace")
                self._backup(path)
                os.replace(temp_name, path)
                self.read_events(target_year)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)
        return event

    def _validate_lifecycle_action(self, event: dict[str, Any], existing: list[dict[str, Any]]) -> None:
        target_id = event["target_id"]
        active = True
        for current in sorted(existing, key=lambda e: (e["created_at"], e["id"])):
            if current.get("target_id") != target_id:
                continue
            if current["entry_type"] == "delete": active = False
            elif current["entry_type"] == "restore": active = True
        if event["entry_type"] == "correction":
            if not active:
                raise ServiceError("目标已删除；普通更正不能使其复活，请先 restore")
            allowed = {"date", "time", "meal_label", "items", "estimated_total_calories", "estimated_total_protein_g", "confidence", "nutrition_source", "exercise_type", "duration_minutes", "completion_status", "intensity", "measurement_type", "value", "unit", "condition", "notes"}
            illegal = set(event["patch"]) - allowed
            if illegal:
                raise ServiceError(f"correction patch 包含不可修改字段：{', '.join(sorted(illegal))}")
        elif event["entry_type"] == "delete" and not active:
            raise ServiceError("目标已经删除")
        elif event["entry_type"] == "restore" and active:
            raise ServiceError("目标当前未删除，无需恢复")

    def find_request(self, request_id: str) -> list[dict[str, Any]]:
        if not request_id:
            return []
        return [e for e in self.read_all_events() if str(e.get("request_id", "")).split(":", 1)[0] == str(request_id)]

    def find_target(self, target_id: str) -> tuple[int, dict[str, Any]]:
        for path in sorted(self.data_dir.glob("[0-9][0-9][0-9][0-9].jsonl")):
            for event in self.read_events(path.stem):
                if event["id"] == target_id and event["entry_type"] in {"food", "exercise", "body_measurement"}:
                    return int(path.stem), event
        raise ServiceError("未找到目标记录")

    def project(self, events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = sorted(events, key=lambda e: (e["created_at"], e["id"]))
        base = {e["id"]: dict(e) for e in ordered if e["entry_type"] in {"food", "exercise", "body_measurement"}}
        active = {key: True for key in base}
        for event in ordered:
            target_id = event.get("target_id")
            if target_id not in base:
                continue
            if event["entry_type"] == "delete":
                active[target_id] = False
            elif event["entry_type"] == "restore":
                active[target_id] = True
            elif event["entry_type"] == "correction" and active[target_id]:
                base[target_id].update(event["patch"])
                base[target_id]["last_correction_id"] = event["id"]
        result = [value for key, value in base.items() if active[key]]
        result.sort(key=lambda e: (e.get("date", ""), e.get("time", ""), e["created_at"], e["id"]))
        return result

    def effective_events(self) -> list[dict[str, Any]]:
        return self.project(self.read_all_events())

    def _event_base(self, entry_type: str, raw_text: str, request_id: str | None = None) -> dict[str, Any]:
        now = self.now()
        event = {"id": str(uuid.uuid4()), "created_at": now.isoformat(timespec="seconds"), "timezone": TZ_NAME, "entry_type": entry_type, "raw_text": raw_text}
        if request_id is not None:
            event["request_id"] = str(request_id)
        return event

    def _business_datetime(self, text: str) -> tuple[str, str]:
        now = self.now()
        date = now.date()
        if "前天" in text: date -= dt.timedelta(days=2)
        elif "昨天" in text or "昨日" in text: date -= dt.timedelta(days=1)
        explicit = re.search(r"(?<!\d)(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text)
        if explicit:
            date = dt.date(*map(int, explicit.groups()))
        else:
            md = re.search(r"(?<!\d)(\d{1,2})月(\d{1,2})日", text)
            if md:
                date = dt.date(now.year, int(md.group(1)), int(md.group(2)))
            weekdays = {"周一": 0, "星期一": 0, "周二": 1, "星期二": 1, "周三": 2, "星期三": 2, "周四": 3, "星期四": 3, "周五": 4, "星期五": 4, "周六": 5, "星期六": 5, "周日": 6, "星期日": 6, "星期天": 6}
            for word, weekday in weekdays.items():
                if word in text:
                    date -= dt.timedelta(days=(date.weekday() - weekday) % 7)
                    break
        time_match = re.search(r"(?<!\d)([01]?\d|2[0-3]):([0-5]\d)", text)
        time = f"{int(time_match.group(1)):02d}:{time_match.group(2)}" if time_match else now.strftime("%H:%M")
        return date.isoformat(), time

    def _build_food(self, text: str, request_id: str | None) -> dict[str, Any]:
        event = self._event_base("food", text, request_id)
        date, time = self._business_datetime(text)
        meal = next((m for m in ("早餐", "午餐", "晚餐", "加餐", "放纵餐") if m in text), "加餐")
        template_name = next((name for name in TEMPLATES if name.lower() in text.lower()), None)
        explicit_cal = re.search(r"(\d+(?:\.\d+)?)\s*(?:kcal|千卡|大卡)", text, re.I)
        explicit_pro = re.search(r"(?:蛋白质?|protein)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*g?", text, re.I)
        if template_name:
            tpl = TEMPLATES[template_name]
            meal = meal if any(x in text for x in MEALS) else tpl["meal"]
            items = [{"name": n, "quantity": q, "estimated_calories": c, "estimated_protein_g": p, "confidence": tpl["confidence"], "nutrition_source": "template", "calorie_range_kcal": [max(0, round(c * .9)), round(c * 1.1)], "protein_range_g": [max(0, round(p * .9, 1)), round(p * 1.1, 1)], "notes": "按常用模板估算"} for n, q, c, p in tpl["items"]]
            event.update({"date": date, "time": time, "meal_label": meal, "items": items, "estimated_total_calories": explicit_cal and float(explicit_cal.group(1)) or tpl["cal"], "estimated_total_protein_g": explicit_pro and float(explicit_pro.group(1)) or tpl["protein"], "confidence": "high" if explicit_cal and explicit_pro else tpl["confidence"], "nutrition_source": "user_label" if explicit_cal or explicit_pro else "template", "template_id": tpl["id"], "template_version": TEMPLATE_VERSION, "notes": "使用常用餐模板；肉/鱼/虾默认熟重可食部分"})
            return event
        description = re.sub(r"^(早餐|午餐|晚餐|加餐|放纵餐)\s*", "", text).strip()
        cal, protein, confidence = self._estimate_food(description)
        if explicit_cal: cal, confidence = float(explicit_cal.group(1)), "high"
        if explicit_pro: protein, confidence = float(explicit_pro.group(1)), "high"
        source = "user_label" if explicit_cal or explicit_pro else "estimate"
        event.update({"date": date, "time": time, "meal_label": meal, "items": [{"name": description or "未命名食物", "quantity": "1份（未说明，按常见熟制份量）", "estimated_calories": cal, "estimated_protein_g": protein, "confidence": confidence, "nutrition_source": source, "calorie_range_kcal": [round(cal * .8), round(cal * 1.2)], "protein_range_g": [round(protein * .8, 1), round(protein * 1.2, 1)], "notes": "份量/生熟重未完全说明，估算含油和酱料误差"}], "estimated_total_calories": cal, "estimated_total_protein_g": protein, "confidence": confidence, "nutrition_source": source, "notes": "自然语言估算"})
        return event

    @staticmethod
    def _estimate_food(text: str) -> tuple[float, float, str]:
        lower = text.lower()
        if "奶茶" in text:
            return (575, 5, "low") if any(x in text for x in ("珍珠", "奶盖", "芋泥")) else (300, 4, "low")
        if any(x in text for x in ("炒饭", "炒面", "盖饭")):
            return 850, 25, "low"
        if any(x in text for x in ("外卖", "餐馆", "饭店")):
            return 700, 30, "low"
        known = [("鸡蛋", 70, 6), ("牛奶", 150, 8), ("酸奶", 120, 10), ("鸡胸", 300, 35), ("牛肉", 350, 30), ("虾", 220, 30), ("豆腐", 180, 15), ("米饭", 230, 4), ("苹果", 100, 1)]
        matches = [(c, p) for name, c, p in known if name in text]
        if matches:
            return sum(x[0] for x in matches), sum(x[1] for x in matches), "low"
        return 500, 20, "low"

    def _build_exercise(self, text: str, request_id: str | None) -> dict[str, Any]:
        event = self._event_base("exercise", text, request_id)
        date, time = self._business_datetime(text)
        duration = re.search(r"(\d+)\s*分钟", text)
        exercise_type = re.sub(r"^(运动|训练)\s*", "", text).strip()
        exercise_type = re.sub(r"\d+\s*分钟.*$", "", exercise_type).strip() or "未说明运动"
        status = "rest" if "休息" in text else "partial" if "部分" in text else "skipped" if any(x in text for x in ("未完成", "取消")) else "completed"
        event.update({"date": date, "time": time, "exercise_type": exercise_type, "duration_minutes": int(duration.group(1)) if duration else 0, "completion_status": status, "intensity": "moderate", "notes": "按用户文字记录"})
        return event

    def _build_measurement(self, text: str, request_id: str | None) -> dict[str, Any]:
        is_weight = "体重" in text
        pattern = r"体重\s*([0-9]+(?:\.[0-9]+)?)\s*(?:kg|公斤|千克)?" if is_weight else r"腰围\s*([0-9]+(?:\.[0-9]+)?)\s*(?:cm|厘米)?"
        match = re.search(pattern, text, re.I)
        if not match:
            raise ServiceError("未识别到体测数值，请写成“体重 72.4kg”或“腰围 82cm”")
        event = self._event_base("body_measurement", text, request_id)
        date, time = self._business_datetime(text)
        condition = "早起空腹" if "早起空腹" in text or "空腹" in text else "自然站立" if "自然站立" in text else "未说明"
        event.update({"date": date, "time": time, "measurement_type": "weight" if is_weight else "waist", "value": float(match.group(1)), "unit": "kg" if is_weight else "cm", "condition": condition})
        return event

    def _recent_food(self, date: str | None = None, include_deleted: bool = False) -> dict[str, Any]:
        records = self.effective_events() if not include_deleted else [e for e in self.read_all_events() if e["entry_type"] == "food"]
        foods = [e for e in records if e["entry_type"] == "food" and (date is None or e.get("date") == date)]
        if not foods:
            raise ServiceError("没有可定位的上一餐")
        return max(foods, key=lambda e: (e.get("date", ""), e.get("time", ""), e["created_at"]))

    def _duplicate_food(self, event: dict[str, Any]) -> dict[str, Any] | None:
        current_time = dt.time.fromisoformat(event["time"])
        for old in reversed([e for e in self.effective_events() if e["entry_type"] == "food" and e["date"] == event["date"]]):
            diff = abs((dt.datetime.combine(dt.date.min, current_time) - dt.datetime.combine(dt.date.min, dt.time.fromisoformat(old["time"]))).total_seconds())
            same_template = event.get("template_id") and event.get("template_id") == old.get("template_id")
            if diff <= 7200 and (same_template or (event["raw_text"] == old["raw_text"] and event["estimated_total_calories"] == old["estimated_total_calories"])):
                return old
        return None

    def handle_message(self, text: str, request_id: str | None = None, allow_duplicate: bool = False, html_enabled: bool = True) -> ServiceResult:
        text = (text or "").strip()
        if not text:
            return ServiceResult(False, "消息为空，未写入数据。")
        try:
            if request_id:
                existing = self.find_request(str(request_id))
                if existing:
                    return self._result_for_existing(existing, html_enabled)
            # 明确用换行、分号分开的多条记录按独立事件处理。每个子事件使用稳定的
            # request_id 后缀；整条 Telegram update 重试时，父 request_id 会一次命中全部。
            parts = [p.strip() for p in re.split(r"[\n；;]+", text) if p.strip()]
            if len(parts) > 1:
                results = [self.handle_message(part, f"{request_id}:{i}" if request_id else None,
                                               allow_duplicate, html_enabled=False)
                           for i, part in enumerate(parts, 1)]
                ids = [event_id for result in results for event_id in (result.event_ids or [])]
                return ServiceResult(all(r.ok for r in results),
                                     "\n\n---\n\n".join(r.markdown for r in results),
                                     "batch", {"results": [r.as_dict() for r in results]}, ids,
                                     any(r.duplicate for r in results))
            normalized = text.lower().strip()
            if normalized in {"today", "今天", "今日汇总", "今日饮食汇总", "减脂今天", "减脂今日汇总", "/today"}:
                return self.today_result(html_enabled=html_enabled)
            if normalized in {"本周复盘", "减脂本周复盘", "减脂周报", "周报", "/week"}:
                return ServiceResult(True, self.weekly_review(), "weekly", self.week_summary())
            if normalized in {"趋势", "减脂趋势", "graph", "/graph"}:
                data = self.trend_data(14)
                return ServiceResult(True, self.render_trend_markdown(data), "trend", data)
            if normalized in {"table", "表格", "减脂表格", "/table"}:
                data = self.recent_days(7)
                return ServiceResult(True, self.render_table_markdown(data), "table", {"days": data})
            if normalized.startswith("删除"):
                target = self._target_from_text(text)
                event = self._event_base("delete", text, request_id)
                event.update({"target_id": target["id"], "reason": "用户要求删除记录"})
                year, _ = self.find_target(target["id"])
                self.append_event(event, year)
                self.rebuild_derived()
                return ServiceResult(True, f"已删除记录：{target['date']} {target.get('meal_label', target['entry_type'])}（保留审计历史）。\n\n{self.daily_markdown(target['date'])}", "delete", event_ids=[event["id"]])
            if normalized.startswith("恢复"):
                target = self._target_from_text(text, include_deleted=True)
                event = self._event_base("restore", text, request_id)
                event.update({"target_id": target["id"], "reason": "用户要求恢复记录"})
                year, _ = self.find_target(target["id"])
                self.append_event(event, year)
                self.rebuild_derived()
                return ServiceResult(True, f"已恢复记录：{target['date']} {target.get('meal_label', target['entry_type'])}。\n\n{self.daily_markdown(target['date'])}", "restore", event_ids=[event["id"]])
            if "刚才那顿是昨天" in text or "上一餐是昨天" in text:
                target = self._recent_food()
                corrected_date = (self.now().date() - dt.timedelta(days=1)).isoformat()
                return self._correct(target, {"date": corrected_date}, text, request_id, "用户说明上一餐属于昨天")
            if normalized.startswith("改成") or normalized.startswith("修改"):
                target = self._target_from_text(text)
                patch = self._parse_patch(text, target)
                return self._correct(target, patch, text, request_id, "用户要求修改记录")
            if "体重" in text or "腰围" in text:
                event = self._build_measurement(text, request_id)
                return self._record(event, html_enabled)
            if text.startswith("运动") or text.startswith("训练") or ("分钟" in text and any(x in text for x in ("力量", "快走", "有氧", "拉伸", "核心"))):
                event = self._build_exercise(text, request_id)
                return self._record(event, html_enabled)
            if self._looks_like_food(text):
                event = self._build_food(text, request_id)
                duplicate = self._duplicate_food(event)
                if duplicate and not allow_duplicate:
                    return ServiceResult(False, f"可能已记录：{duplicate['date']} {duplicate['time']} {duplicate['meal_label']}，本次未重复写入。若确实是另一份，请明确补充时间或使用确认重复参数。", "duplicate", {"possible_duplicate_id": duplicate["id"]}, duplicate=True)
                return self._record(event, html_enabled, allow_duplicate=allow_duplicate)
            return ServiceResult(True, "这条消息未识别为饮食、运动、体测或查询指令，未写入健康数据。", "ignored")
        except DataCorruptionError as exc:
            return ServiceResult(False, f"{exc}\n\n无法安全生成实时卡片；请先检查项目内备份。", "error")
        except ServiceError as exc:
            return ServiceResult(False, str(exc), "error")

    def _looks_like_food(self, text: str) -> bool:
        return any(x in text for x in ("早餐", "午餐", "晚餐", "加餐", "吃", "喝", "奶茶", "咖啡", "鸡蛋", "米饭", "酸奶", "牛奶", "鸡胸", "牛肉", "虾", "鱼", "豆腐")) or any(name in text for name in TEMPLATES)

    def _target_from_text(self, text: str, include_deleted: bool = False) -> dict[str, Any]:
        id_match = re.search(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,36}\b", text)
        if id_match:
            _, target = self.find_target(id_match.group(0))
            return target
        if "上一餐" in text or "刚才" in text or text.startswith(("删除", "恢复", "修改", "改成")):
            return self._recent_food(include_deleted=include_deleted)
        raise ServiceError("未能定位目标记录，请提供 target_id 或说明“上一餐”")

    def _parse_patch(self, text: str, target: dict[str, Any]) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        date, time = self._business_datetime(text)
        if any(x in text for x in ("昨天", "前天", "月", "20")): patch["date"] = date
        if re.search(r"\d{1,2}:\d{2}", text): patch["time"] = time
        for meal in MEALS:
            if meal in text: patch["meal_label"] = meal
        cal = re.search(r"(\d+(?:\.\d+)?)\s*(?:kcal|千卡|大卡)", text, re.I)
        pro = re.search(r"(?:蛋白质?|protein)\s*[:：]?\s*(\d+(?:\.\d+)?)", text, re.I)
        if cal: patch["estimated_total_calories"] = float(cal.group(1))
        if pro: patch["estimated_total_protein_g"] = float(pro.group(1))
        value = re.search(r"(?:体重|腰围)\s*([0-9]+(?:\.[0-9]+)?)", text)
        if value and target["entry_type"] == "body_measurement": patch["value"] = float(value.group(1))
        if not patch:
            raise ServiceError("没有识别到可修改字段")
        return patch

    def _correct(self, target: dict[str, Any], patch: dict[str, Any], text: str, request_id: str | None, reason: str) -> ServiceResult:
        event = self._event_base("correction", text, request_id)
        event.update({"target_id": target["id"], "patch": patch, "reason": reason})
        year, _ = self.find_target(target["id"])
        self.append_event(event, year)
        self.rebuild_derived()
        effective = next(e for e in self.effective_events() if e["id"] == target["id"])
        return ServiceResult(True, f"已修改记录：{target['id']}\n- 修改内容：{json.dumps(patch, ensure_ascii=False)}\n\n{self.daily_markdown(effective['date'])}", "correction", event_ids=[event["id"]])

    def _record(self, event: dict[str, Any], html_enabled: bool, allow_duplicate: bool = False) -> ServiceResult:
        requested_id = event["id"]
        event = self.append_event(event, allow_duplicate=allow_duplicate)
        idempotent_race = event["id"] != requested_id
        view_warning = ""
        try:
            self.rebuild_derived(event["date"])
        except Exception as exc:
            view_warning = f"\n\n数据已安全保存，但派生视图生成失败（{type(exc).__name__}）；本次使用 Markdown 回复。"
        if event["entry_type"] == "food":
            summary = self.daily_summary(event["date"])
            remaining_cal = self.calorie_target - summary["calories"]
            remaining_pro = self.protein_target - summary["protein_g"]
            content = event["items"][0]["name"] if len(event["items"]) == 1 else "、".join(i["name"] for i in event["items"])
            advice = self._advice(summary)
            md = (f"已记录：{event['date']}\n\n本餐：\n- 餐次：{event['meal_label']}\n- 内容：{content}\n- 估算热量：{event['estimated_total_calories']:g} kcal\n- 估算蛋白质：{event['estimated_total_protein_g']:g} g\n- 置信度：{{'high':'高','medium':'中','low':'低'}}[{event['confidence']}]\n\n今日累计：\n- 热量：{summary['calories']:g} / {self.calorie_target:g} kcal（{self._gap(remaining_cal, 'kcal')}）\n- 蛋白质：{summary['protein_g']:g} / {self.protein_target:g}g（{self._gap(remaining_pro, 'g')}）\n\n下一步建议：\n- {advice}")
        elif event["entry_type"] == "exercise":
            md = f"已记录：{event['date']}\n\n- 运动：{event['exercise_type']}\n- 时长：{event['duration_minutes']} 分钟\n- 状态：{self._exercise_status(event)}"
        else:
            md = f"已记录：{event['date']}\n\n- {'体重' if event['measurement_type']=='weight' else '腰围'}：{event['value']:g}{event['unit']}\n- 测量条件：{event.get('condition','未说明')}"
        if idempotent_race:
            md = "该 request_id 已处理，本次未重复写入。\n\n" + self.daily_markdown(event["date"])
        return ServiceResult(True, md + view_warning, event["entry_type"], {"event": event, "view_warning": bool(view_warning)}, [event["id"]], duplicate=idempotent_race)

    def _result_for_existing(self, events: list[dict[str, Any]], html_enabled: bool) -> ServiceResult:
        event = events[-1]
        date = event.get("date")
        if not date and event.get("target_id"):
            try: _, target = self.find_target(event["target_id"]); date = target.get("date")
            except ServiceError: date = None
        md = "该 request_id 已处理，本次未重复写入。"
        if date: md += "\n\n" + self.daily_markdown(date)
        return ServiceResult(True, md, "idempotent", {"events": events}, [e["id"] for e in events], duplicate=True)

    @staticmethod
    def _gap(value: float, unit: str) -> str:
        return f"还差 {value:g}{unit}" if value >= 0 else f"超出 {abs(value):g}{unit}"

    def daily_summary(self, date: str) -> dict[str, Any]:
        records = [e for e in self.effective_events() if e.get("date") == date]
        foods = [e for e in records if e["entry_type"] == "food"]
        exercises = [e for e in records if e["entry_type"] == "exercise"]
        measurements = [e for e in records if e["entry_type"] == "body_measurement"]
        calories = sum(float(e["estimated_total_calories"]) for e in foods)
        protein = sum(float(e["estimated_total_protein_g"]) for e in foods)
        meals: dict[str, list[dict[str, Any]]] = {m: [] for m in ("早餐", "午餐", "晚餐", "加餐", "放纵餐")}
        for food in foods: meals.setdefault(food["meal_label"], []).append(food)
        return {"date": date, "calories": round(calories, 1), "protein_g": round(protein, 1), "calorie_gap": round(self.calorie_target-calories, 1), "protein_gap": round(self.protein_target-protein, 1), "foods": foods, "meals": meals, "exercises": exercises, "exercise_status": self._day_exercise_status(exercises), "weight": self._preferred_measurement(measurements, "weight"), "waist": self._preferred_measurement(measurements, "waist"), "judgement": self._advice({"calories": calories, "protein_g": protein, "foods": foods}), "targets": {"calories": self.calorie_target, "training_calorie_max": self.training_calorie_max, "protein_g": self.protein_target, "program_weeks": self.program_weeks}}

    @staticmethod
    def _preferred_measurement(records: list[dict[str, Any]], kind: str) -> dict[str, Any] | None:
        values = [e for e in records if e.get("measurement_type") == kind]
        if not values: return None
        preferred = [e for e in values if "早起空腹" in e.get("condition", "")] if kind == "weight" else [e for e in values if e.get("condition") not in {"", "未说明", None}]
        return max(preferred or values, key=lambda e: (e["time"], e["created_at"]))

    @staticmethod
    def _exercise_status(event: dict[str, Any]) -> str:
        return {"completed":"完成", "partial":"部分完成", "rest":"休息", "skipped":"未完成"}.get(event["completion_status"], "未记录")

    def _day_exercise_status(self, exercises: list[dict[str, Any]]) -> str:
        if not exercises: return "未记录"
        if any(e["completion_status"] == "completed" for e in exercises): return "完成"
        if any(e["completion_status"] == "partial" for e in exercises): return "部分完成"
        if any(e["completion_status"] == "rest" for e in exercises): return "休息"
        return "未完成"

    def _advice(self, summary: dict[str, Any]) -> str:
        if not summary.get("foods"): return "今天还没有饮食记录。"
        cal, pro = summary["calories"], summary["protein_g"]
        if cal < self.minimum_calories and pro < min(110, self.protein_min): return "后续优先补一份蛋白质和适量主食，不要靠硬饿收尾。"
        if pro < self.protein_min: return "下一餐优先补鸡蛋、牛奶、虾仁、鸡胸或豆腐。"
        if cal > self.training_calorie_max: return "下一餐清淡即可，不做补偿性绝食。"
        return "当前执行稳定，下一餐继续按计划吃。"

    def daily_markdown(self, date: str) -> str:
        s = self.daily_summary(date)
        lines = [f"今日汇总：{date}", "", f"- 总热量：{s['calories']:g} / {self.calorie_target:g} kcal", f"- 总蛋白质：{s['protein_g']:g} / {self.protein_target:g}g"]
        for meal in ("早餐", "午餐", "晚餐", "加餐", "放纵餐"):
            entries = s["meals"].get(meal, [])
            if entries:
                lines.append(f"- {meal}：{sum(e['estimated_total_calories'] for e in entries):g} kcal / {sum(e['estimated_total_protein_g'] for e in entries):g}g 蛋白")
            else:
                lines.append(f"- {meal}：未记录")
        lines += [f"- 运动：{s['exercise_status']}", "", "判断：", f"- {s['judgement']}"]
        return "\n".join(lines)

    def today_result(self, date: str | None = None, html_enabled: bool = True) -> ServiceResult:
        date = date or self.now().date().isoformat()
        try:
            summary = self.daily_summary(date)
            markdown = self.daily_markdown(date)
            html_card = self.render_today_html(summary) if html_enabled else None
            if html_card:
                self._atomic_write_derived(self.cards_dir / "today.html", html_card)
            return ServiceResult(True, markdown, "today", {"summary": summary, "html": html_card, "html_enabled": html_enabled})
        except ServiceError as exc:
            return ServiceResult(False, f"今日卡片生成失败：{exc}\n\nMarkdown 降级不可用，因为源数据未通过安全校验。", "error")

    def render_today_html(self, s: dict[str, Any]) -> str:
        cal_pct = min(100, max(0, s["calories"] / self.calorie_target * 100))
        pro_pct = min(100, max(0, s["protein_g"] / self.protein_target * 100))
        cards = []
        for meal in ("早餐", "午餐", "晚餐", "加餐", "放纵餐"):
            entries = s["meals"].get(meal, [])
            if not entries: continue
            total_c = sum(e["estimated_total_calories"] for e in entries); total_p = sum(e["estimated_total_protein_g"] for e in entries)
            details = []
            for entry in entries:
                for item in entry["items"]:
                    score = "—" if not item["estimated_calories"] else f"{item['estimated_protein_g']/item['estimated_calories']*100:.1f}g/100kcal"
                    details.append(f"{html.escape(str(item['name']))} {html.escape(str(item['quantity']))} · {item['estimated_calories']:g} kcal · {item['estimated_protein_g']:g}g · score {score}")
            cards.append(f'<section class="meal"><header><strong>{meal}</strong><span><b class="cal">{total_c:g} kcal</b> · <b class="pro">{total_p:g}g</b></span></header><div class="details">{"<br>".join(details)}</div></section>')
        empty = '<section class="meal empty">今天还没有饮食记录</section>' if not s["foods"] else ""
        style = "body{margin:0;background:#141414;color:#E0E0E0;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}.card{max-width:420px;margin:0 auto;padding:16px}.label,.details,.foot{color:#9CA3AF;font-size:12px}.title{color:#fff;font-size:22px;font-weight:700}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0 10px}.metric,.meal{background:#1A1A1A;border:1px solid rgba(255,255,255,.08);border-radius:8px;padding:12px}.value{font-size:24px;font-weight:800}.cal{color:#F472B6}.pro{color:#53BDEB}.bar{height:6px;background:#262626;border-radius:999px;overflow:hidden;margin:6px 0}.fill-cal{height:100%;background:#F472B6}.fill-pro{height:100%;background:#53BDEB}.meal{margin:10px 0}.meal header{display:flex;justify-content:space-between;gap:12px}.details{margin-top:8px;line-height:1.6}.foot{margin-top:12px;line-height:1.6}"
        return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>今日减脂记录</title><style>{style}</style><body><main class="card"><div class="label">TODAY · {self.program_weeks} WEEK PROGRAM</div><div class="title">{s["date"]}</div><div class="grid"><div class="metric"><div class="label">Calories</div><div class="value cal">{s["calories"]:g}</div><div class="label">/ {self.calorie_target:g} kcal · {html.escape(self._gap(s["calorie_gap"], "kcal"))}</div></div><div class="metric"><div class="label">Protein</div><div class="value pro">{s["protein_g"]:g}g</div><div class="label">/ {self.protein_target:g}g · {html.escape(self._gap(s["protein_gap"], "g"))}</div></div></div><div class="bar"><div class="fill-cal" style="width:{cal_pct:.1f}%"></div></div><div class="bar"><div class="fill-pro" style="width:{pro_pct:.1f}%"></div></div>{empty}{"".join(cards)}<div class="foot">运动：{html.escape(s["exercise_status"])}<br>建议：{html.escape(s["judgement"])}</div></main></body></html>'

    def recent_days(self, count: int = 7, end: dt.date | None = None) -> list[dict[str, Any]]:
        end = end or self.now().date()
        return [self.daily_summary((end - dt.timedelta(days=i)).isoformat()) for i in reversed(range(count))]

    def render_table_markdown(self, days: list[dict[str, Any]]) -> str:
        lines = ["| 日期 | 热量 | 蛋白质 | 运动 | 体重 | 备注 |", "|---|---:|---:|---|---:|---|"]
        for d in days:
            note = "未记录饮食" if not d["foods"] else "蛋白不足" if d["protein_g"] < self.protein_min else "热量偏高" if d["calories"] > self.training_calorie_max else "执行良好"
            weight = f"{d['weight']['value']:g}kg" if d["weight"] else "未记录"
            lines.append(f"| {d['date']} | {d['calories']:g} | {d['protein_g']:g}g | {d['exercise_status']} | {weight} | {note} |")
        return "\n".join(lines)

    def week_summary(self, reference: dt.date | None = None) -> dict[str, Any]:
        ref = reference or self.now().date(); start = ref - dt.timedelta(days=ref.weekday()); end = start + dt.timedelta(days=6)
        days = [self.daily_summary((start + dt.timedelta(days=i)).isoformat()) for i in range(7)]
        recorded = [d for d in days if d["foods"]]
        avg_cal = sum(d["calories"] for d in recorded) / len(recorded) if recorded else None
        avg_pro = sum(d["protein_g"] for d in recorded) / len(recorded) if recorded else None
        weights = [d["weight"] for d in days if d["weight"]]; waists = [d["waist"] for d in days if d["waist"]]
        planned = sum(1 for i in range(7) if (start + dt.timedelta(days=i)).weekday() < 6)
        completed = sum(1 for d in days if d["exercise_status"] in {"完成", "部分完成"})
        return {"start": start.isoformat(), "end": end.isoformat(), "days": days, "recorded_days": len(recorded), "average_calories": round(avg_cal,1) if avg_cal is not None else None, "average_protein_g": round(avg_pro,1) if avg_pro is not None else None, "weights": weights, "waists": waists, "exercise_completed": completed, "exercise_planned": planned}

    def weekly_review(self, reference: dt.date | None = None) -> str:
        w = self.week_summary(reference)
        avg_c = f"{w['average_calories']:g} kcal（{w['recorded_days']}/7 天有饮食记录）" if w["average_calories"] is not None else "未记录"
        avg_p = f"{w['average_protein_g']:g} g（{w['recorded_days']}/7 天有饮食记录）" if w["average_protein_g"] is not None else "未记录"
        weight = f"{w['weights'][0]['value']:g} kg → {w['weights'][-1]['value']:g} kg（{len(w['weights'])} 天样本）" if w["weights"] else "未记录"
        waist = f"{w['waists'][0]['value']:g} cm → {w['waists'][-1]['value']:g} cm（{len(w['waists'])} 天样本）" if w["waists"] else "未记录"
        good, problems, adjust = [], [], []
        if w["recorded_days"] >= 5: good.append("记录完整度较好")
        if w["average_protein_g"] and w["average_protein_g"] >= self.protein_min: good.append("平均蛋白质达到可接受范围")
        if w["average_calories"] and w["average_calories"] <= self.training_calorie_max: good.append("平均摄入控制在目标附近")
        if w["recorded_days"] < 5: problems.append("饮食记录天数偏少")
        low_pro = sum(1 for d in w["days"] if d["foods"] and d["protein_g"] < self.protein_min)
        high_cal = sum(1 for d in w["days"] if d["foods"] and d["calories"] > self.training_calorie_max)
        if low_pro: problems.append(f"蛋白不足 {low_pro} 天")
        if high_cal: problems.append(f"热量高于 {self.training_calorie_max:g} kcal 共 {high_cal} 天")
        adjust = ["继续记录食材份量和生熟重", f"优先让每日蛋白质达到 {self.protein_min:g}–{self.protein_max:g}g", "按计划完成训练，疲劳或不适时不硬压摄入"]
        return f"本周复盘：{w['start']} 至 {w['end']}\n\n1. 平均每日热量：{avg_c}\n2. 平均每日蛋白质：{avg_p}\n3. 体重变化：{weight}\n4. 腰围变化：{waist}\n5. 运动完成：{w['exercise_completed']} / {w['exercise_planned']} 次\n6. 做得好的地方：{'；'.join(good[:3]) or '有效记录不足，暂不下结论'}\n7. 主要问题：{'；'.join(problems[:3]) or '暂无明显问题'}\n8. 下周调整：\n- " + "\n- ".join(adjust[:3])

    def trend_data(self, count: int = 14, end: dt.date | None = None) -> dict[str, Any]:
        days = self.recent_days(count, end)
        weight_points = [(d["date"], d["weight"]["value"] if d["weight"] else None) for d in days]
        moving: list[dict[str, Any]] = []
        recorded_values: list[float] = []
        for date, value in weight_points:
            if value is not None:
                recorded_values.append(float(value)); recorded_values = recorded_values[-7:]
                moving.append({"date": date, "value": round(sum(recorded_values)/len(recorded_values), 2), "samples": len(recorded_values)})
            else:
                moving.append({"date": date, "value": None, "samples": 0})
        recorded_food = [d for d in days if d["foods"]]
        return {"days": days, "weight_7d_average": moving, "average_calories": round(sum(d["calories"] for d in recorded_food)/len(recorded_food),1) if recorded_food else None, "average_protein_g": round(sum(d["protein_g"] for d in recorded_food)/len(recorded_food),1) if recorded_food else None, "food_sample_days": len(recorded_food)}

    def render_trend_markdown(self, data: dict[str, Any]) -> str:
        weights = [(d["date"], d["weight"]["value"]) for d in data["days"] if d["weight"]]
        change = f"{weights[0][1]:g}kg → {weights[-1][1]:g}kg（{len(weights)} 天样本）" if weights else "无体重记录"
        return f"趋势（最近 {len(data['days'])} 天）\n\n- 平均热量：{data['average_calories'] if data['average_calories'] is not None else '未记录'} kcal（{data['food_sample_days']} 天样本）\n- 平均蛋白质：{data['average_protein_g'] if data['average_protein_g'] is not None else '未记录'} g\n- 体重变化：{change}\n- 判断：单日波动不作结论，优先看连续 7 天移动平均。"

    def rebuild_derived(self, date: str | None = None) -> None:
        date = date or self.now().date().isoformat()
        summary = self.daily_summary(date)
        self._atomic_write_derived(self.cards_dir / "today.html", self.render_today_html(summary))
        month = date[:7]
        month_days = sorted({e["date"] for e in self.effective_events() if e.get("date", "").startswith(month)})
        content = f"# {month} 月度摘要\n\n" + ("\n".join(f"## {d}\n\n{self.daily_markdown(d)}\n" for d in month_days) if month_days else "本月暂无记录。\n")
        self._atomic_write_derived(self.summary_dir / f"{month}.md", content)

    @staticmethod
    def _atomic_write_derived(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(content); fh.flush(); os.fsync(fh.fileno())
            os.replace(temp, path)
        finally:
            if os.path.exists(temp): os.unlink(temp)

    def dashboard_payload(self) -> dict[str, Any]:
        try:
            now = self.now(); today = self.daily_summary(now.date().isoformat()); days = self.recent_days(7); trend = self.trend_data(14)
            files = sorted(p.name for p in self.data_dir.glob("[0-9][0-9][0-9][0-9].jsonl"))
            return {"ok": True, "generated_at": now.isoformat(timespec="seconds"), "source_files": files or ["尚无年度数据文件"], "settings": self.settings, "today": today, "days": days, "trend": trend, "error": None}
        except ServiceError as exc:
            return {"ok": False, "generated_at": self.now().isoformat(timespec="seconds"), "source_files": [], "today": None, "days": [], "trend": None, "error": str(exc)}

    def restore_backup(self, backup_path: str | Path) -> str:
        backup = Path(backup_path).resolve()
        if self.backup_dir.resolve() not in backup.parents or not re.fullmatch(r"\d{4}-.*\.jsonl", backup.name):
            raise ServiceError("只能恢复项目 backups/ 内的年度 JSONL 备份")
        year = backup.name[:4]
        # Validate without changing the live source.
        events = []
        with backup.open("r", encoding="utf-8") as fh:
            for number, line in enumerate(fh, 1):
                if not line.strip(): continue
                try: event = json.loads(line)
                except json.JSONDecodeError as exc: raise DataCorruptionError(backup, number, exc.msg) from exc
                self.validate_event(event, reading=True); events.append(event)
        if len({e["id"] for e in events}) != len(events): raise ServiceError("备份包含重复 id，拒绝恢复")
        target = self._year_path(year)
        with self._write_lock():
            self._backup(target)
            fd, temp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".restore", dir=self.data_dir)
            try:
                with os.fdopen(fd, "wb") as out, backup.open("rb") as src:
                    shutil.copyfileobj(src, out); out.flush(); os.fsync(out.fileno())
                os.replace(temp, target)
            finally:
                if os.path.exists(temp): os.unlink(temp)
        self.read_events(year); self.rebuild_derived()
        return f"已从 {backup.name} 恢复 {target.name}，恢复时间 {self.now().isoformat(timespec='seconds')}。"


def main() -> int:
    parser = argparse.ArgumentParser(description="减脂记录 Agent 后端服务")
    parser.add_argument("message", nargs="?", help="要处理的自然语言消息")
    parser.add_argument("--request-id")
    parser.add_argument("--json", action="store_true", help="输出 JSON 结果")
    parser.add_argument("--no-html", action="store_true")
    parser.add_argument("--root", help="测试/迁移时指定项目根目录")
    parser.add_argument("--dashboard-json", action="store_true")
    args = parser.parse_args()
    service = CalorieService(args.root)
    if args.dashboard_json:
        print(json.dumps(service.dashboard_payload(), ensure_ascii=False, indent=2)); return 0
    if not args.message:
        parser.error("需要 message 或 --dashboard-json")
    result = service.handle_message(args.message, args.request_id, html_enabled=not args.no_html)
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2) if args.json else result.markdown)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
