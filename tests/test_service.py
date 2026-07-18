import concurrent.futures
import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from backend.service import CalorieService, DataCorruptionError, ServiceError, TZ_NAME

TZ = ZoneInfo(TZ_NAME)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.clock = dt.datetime(2026, 7, 17, 12, 30, tzinfo=TZ)
        self.s = CalorieService(self.root, now_fn=lambda: self.clock)

    def tearDown(self):
        self.tmp.cleanup()

    def test_template_food_and_request_id_idempotency(self):
        first = self.s.handle_message("早餐 标准早餐A", "100")
        second = self.s.handle_message("早餐 标准早餐A", "100")
        self.assertTrue(first.ok and second.ok)
        self.assertTrue(second.duplicate)
        events = self.s.read_events(2026)
        self.assertEqual(1, len(events))
        self.assertEqual(290, self.s.daily_summary("2026-07-17")["calories"])

    def test_custom_program_weeks_and_targets_from_config(self):
        (self.root / "config.json").write_text(json.dumps({
            "program_weeks": 12,
            "calorie_target_kcal": 2000,
            "training_day_calorie_max_kcal": 2100,
            "minimum_recommended_calories_kcal": 1600,
            "protein_target_g": 150,
            "protein_min_g": 140,
            "protein_max_g": 160,
            "timezone": "Asia/Shanghai",
        }), encoding="utf-8")
        service = CalorieService(self.root, now_fn=lambda: self.clock)
        summary = service.daily_summary("2026-07-17")
        self.assertEqual(12, service.program_weeks)
        self.assertEqual(2000, summary["targets"]["calories"])
        self.assertEqual(150, summary["targets"]["protein_g"])
        self.assertEqual(2000, summary["calorie_gap"])
        self.assertIn("12 WEEK PROGRAM", service.today_result().data["html"])

    def test_invalid_config_is_rejected(self):
        (self.root / "config.json").write_text('{"program_weeks": 0}', encoding="utf-8")
        with self.assertRaises(ServiceError):
            CalorieService(self.root, now_fn=lambda: self.clock)

    def test_multi_line_message_splits_into_independent_events_and_is_idempotent(self):
        first = self.s.handle_message("早餐 标准早餐A\n体重 72.4kg，早起空腹", "batch-1")
        second = self.s.handle_message("早餐 标准早餐A\n体重 72.4kg，早起空腹", "batch-1")
        self.assertTrue(first.ok and second.ok)
        self.assertEqual(2, len(self.s.read_events(2026)))
        self.assertTrue(second.duplicate)

    def test_concurrent_same_request_id_writes_only_once(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.s.handle_message("早餐 标准早餐A", "race-1"), range(2)))
        self.assertTrue(all(result.ok for result in results))
        self.assertEqual(1, len(self.s.read_events(2026)))
        self.assertEqual(1, len({result.event_ids[0] for result in results}))

    def test_project_lock_is_cross_platform_and_released(self):
        self.assertNotIn("import fcntl", (Path(__file__).parents[1] / "backend/service.py").read_text(encoding="utf-8"))
        with self.s._write_lock():
            self.assertTrue(self.s.lock_path.exists())
        self.assertFalse(self.s.lock_path.exists())

    def test_stale_project_lock_is_recovered(self):
        self.s.lock_path.write_text('{"token":"stale"}', encoding="utf-8")
        old = dt.datetime.now().timestamp() - 300
        os.utime(self.s.lock_path, (old, old))
        with self.s._write_lock(timeout=.2, stale_after=.1):
            self.assertTrue(self.s.lock_path.exists())
        self.assertFalse(self.s.lock_path.exists())

    def test_suspected_duplicate_is_not_written(self):
        self.assertTrue(self.s.handle_message("午餐 鸡胸饭标准版", "1").ok)
        duplicate = self.s.handle_message("午餐 鸡胸饭标准版", "2")
        self.assertFalse(duplicate.ok)
        self.assertTrue(duplicate.duplicate)
        self.assertEqual(1, len(self.s.read_events(2026)))

    def test_corrections_apply_in_created_order(self):
        created = self.s.handle_message("早餐 标准早餐A", "1")
        target = created.event_ids[0]
        self.clock += dt.timedelta(seconds=1)
        self.assertTrue(self.s.handle_message(f"修改 {target} 改成 310 kcal 蛋白质 21", "2").ok)
        self.clock += dt.timedelta(seconds=1)
        self.assertTrue(self.s.handle_message(f"修改 {target} 改成 330 kcal", "3").ok)
        effective = self.s.effective_events()[0]
        self.assertEqual(330, effective["estimated_total_calories"])
        self.assertEqual(21, effective["estimated_total_protein_g"])

    def test_delete_correction_rejected_restore_recounts(self):
        created = self.s.handle_message("早餐 标准早餐A", "1")
        target = created.event_ids[0]
        self.clock += dt.timedelta(seconds=1)
        self.assertTrue(self.s.handle_message(f"删除 {target}", "2").ok)
        self.assertEqual(0, self.s.daily_summary("2026-07-17")["calories"])
        rejected = self.s.handle_message(f"修改 {target} 改成 400 kcal", "3")
        self.assertFalse(rejected.ok)
        self.clock += dt.timedelta(seconds=1)
        restored = self.s.handle_message(f"恢复 {target}", "4")
        self.assertTrue(restored.ok)
        self.assertEqual(290, self.s.daily_summary("2026-07-17")["calories"])

    def test_cross_year_correction_is_appended_to_original_year(self):
        self.clock = dt.datetime(2025, 12, 31, 8, 0, tzinfo=TZ)
        made = self.s.handle_message("早餐 标准早餐A", "1")
        target = made.event_ids[0]
        self.clock = dt.datetime(2026, 1, 1, 9, 0, tzinfo=TZ)
        changed = self.s.handle_message(f"修改 {target} 改成 310 kcal", "2")
        self.assertTrue(changed.ok)
        self.assertEqual(2, len(self.s.read_events(2025)))
        self.assertFalse((self.root / "data/2026.jsonl").exists())

    def test_atomic_interruption_preserves_old_file(self):
        event = self.s._build_food("早餐 标准早餐A", "1")
        self.s.append_event(event)
        before = (self.root / "data/2026.jsonl").read_bytes()
        self.clock += dt.timedelta(seconds=1)
        second = self.s._build_food("午餐 牛肉饭标准版", "2")
        with self.assertRaises(OSError):
            self.s.append_event(second, simulate_interrupt=True)
        self.assertEqual(before, (self.root / "data/2026.jsonl").read_bytes())
        self.assertEqual(1, len(self.s.read_events(2026)))

    def test_corrupt_last_line_reports_line_and_keeps_prior_bytes(self):
        self.s.handle_message("早餐 标准早餐A", "1")
        path = self.root / "data/2026.jsonl"
        with path.open("ab") as fh:
            fh.write(b'{"broken":')
        with self.assertRaises(DataCorruptionError) as ctx:
            self.s.read_events(2026)
        self.assertEqual(2, ctx.exception.line)
        result = self.s.handle_message("今天", "2")
        self.assertFalse(result.ok)
        self.assertIn("第 2 行", result.markdown)

    def test_schema_invalid_line_is_reported_as_corruption_with_line_number(self):
        self.s.handle_message("早餐 标准早餐A", "1")
        path = self.root / "data/2026.jsonl"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": "not-a-uuid"}, ensure_ascii=False) + "\n")
        with self.assertRaises(DataCorruptionError) as ctx:
            self.s.read_events(2026)
        self.assertEqual(2, ctx.exception.line)

    def test_empty_single_and_over_target_states(self):
        empty = self.s.today_result()
        self.assertIn("今天还没有饮食记录", empty.data["html"])
        self.s.handle_message("早餐 标准早餐A", "1")
        html = self.s.today_result().data["html"]
        self.assertIn("早餐", html)
        self.assertNotIn("午餐</strong>", html)
        self.clock += dt.timedelta(hours=3)
        self.s.handle_message("午餐 炒饭 1000 kcal 蛋白质 20g", "2")
        self.clock += dt.timedelta(hours=3)
        self.s.handle_message("晚餐 900 kcal 蛋白质 30g", "3")
        summary = self.s.daily_summary("2026-07-17")
        self.assertGreater(summary["calories"], 1800)
        self.assertIn("超出", self.s.today_result().data["html"])

    def test_html_input_is_escaped(self):
        self.s.handle_message("早餐 <script>alert(1)</script> 300 kcal 蛋白质 20", "1")
        rendered = self.s.today_result().data["html"]
        self.assertNotIn("<script>alert", rendered)
        self.assertIn("&lt;script&gt;", rendered)

    def test_same_day_weight_prefers_latest_fasting_measurement(self):
        self.s.handle_message("体重 73kg", "1")
        self.clock += dt.timedelta(minutes=10)
        self.s.handle_message("体重 72.4kg，早起空腹", "2")
        self.clock += dt.timedelta(minutes=10)
        self.s.handle_message("体重 74kg", "3")
        weight = self.s.daily_summary("2026-07-17")["weight"]
        self.assertEqual(72.4, weight["value"])

    def test_missing_weight_is_none_not_zero(self):
        days = self.s.recent_days(7)
        self.assertTrue(all(day["weight"] is None for day in days))
        trend = self.s.trend_data(7)
        self.assertTrue(all(p["value"] is None for p in trend["weight_7d_average"]))

    def test_takeout_has_low_confidence(self):
        result = self.s.handle_message("午餐 外卖餐馆盖饭", "1")
        self.assertTrue(result.ok)
        event = self.s.read_events(2026)[0]
        self.assertEqual("low", event["confidence"])

    def test_week_boundary_is_monday_to_sunday(self):
        monday = self.s.week_summary(dt.date(2026, 7, 13))
        sunday = self.s.week_summary(dt.date(2026, 7, 19))
        self.assertEqual((monday["start"], monday["end"]), ("2026-07-13", "2026-07-19"))
        self.assertEqual((monday["start"], monday["end"]), (sunday["start"], sunday["end"]))

    def test_markdown_degradation(self):
        self.s.handle_message("早餐 标准早餐A", "1")
        result = self.s.today_result(html_enabled=False)
        self.assertIsNone(result.data["html"])
        self.assertIn("今日汇总", result.markdown)

    def test_derived_failure_does_not_undo_source_write(self):
        with mock.patch.object(self.s, "rebuild_derived", side_effect=OSError("render failed")):
            result = self.s.handle_message("早餐 标准早餐A", "1")
        self.assertTrue(result.ok)
        self.assertIn("数据已安全保存", result.markdown)
        self.assertTrue(result.data["view_warning"])
        self.assertEqual(1, len(self.s.read_events(2026)))

    def test_backups_are_project_local(self):
        self.s.handle_message("早餐 标准早餐A", "1")
        self.clock += dt.timedelta(hours=3)
        self.s.handle_message("午餐 鸡胸饭标准版", "2")
        backups = list((self.root / "backups").rglob("*.jsonl"))
        self.assertTrue(backups)
        self.assertTrue(all(self.root in p.parents for p in backups))

    def test_restore_backup_validates_and_restores(self):
        self.s.handle_message("早餐 标准早餐A", "1")
        self.clock += dt.timedelta(hours=3)
        self.s.handle_message("午餐 鸡胸饭标准版", "2")
        backup = next((self.root / "backups").rglob("*.jsonl"))
        message = self.s.restore_backup(backup)
        self.assertIn("已从", message)
        self.assertEqual(1, len(self.s.read_events(2026)))

    def test_validation_rejects_negative_or_wrong_units(self):
        event = self.s._event_base("body_measurement", "体重 -1kg", "1")
        event.update({"date": "2026-07-17", "time": "10:00", "measurement_type": "weight", "value": -1, "unit": "kg", "condition": "未说明"})
        with self.assertRaises(ServiceError):
            self.s.append_event(event)
    def test_profile_uses_weeks_or_date_and_never_rewrites_events(self):
        created = self.s.handle_message("早餐 标准早餐A", "before-profile")
        before = (self.root / "data/2026.jsonl").read_bytes()
        saved = self.s.save_profile({"profile": {"height_cm": 172, "current_weight_kg": 75, "target_weight_kg": 68}, "plan": {"program_weeks": 8, "timezone": TZ_NAME}})
        self.assertFalse(saved["warning"])
        self.assertTrue((self.root / "profile.json").exists())
        plan = saved["profile"]["plan"]
        self.assertEqual(("2026-07-17", "2026-09-11", 8), (plan["start_date"], plan["end_date"], plan["program_weeks"]))
        self.assertEqual(before, (self.root / "data/2026.jsonl").read_bytes())
        self.assertEqual(created.event_ids[0], self.s.read_events(2026)[0]["id"])
        self.clock = dt.datetime(2026, 7, 17, 12, 30, tzinfo=TZ)
        date_saved = self.s.save_profile({"profile": {"height_cm": 172, "current_weight_kg": 75, "target_weight_kg": 70}, "plan": {"end_date": "2026-08-14", "timezone": TZ_NAME}})
        self.assertEqual(4, date_saved["profile"]["plan"]["program_weeks"])
        self.assertEqual(before, (self.root / "data/2026.jsonl").read_bytes())

    def test_profile_rejects_invalid_or_unsafe_plans(self):
        base = {"profile": {"height_cm": 172, "current_weight_kg": 75, "target_weight_kg": 68}, "plan": {"timezone": TZ_NAME}}
        for plan in ({"program_weeks": 0}, {"program_weeks": 8, "end_date": "2026-09-01"}, {"end_date": "2026-07-17"}):
            with self.subTest(plan=plan), self.assertRaises(ServiceError):
                self.s.save_profile({"profile": base["profile"], "plan": {"timezone": TZ_NAME, **plan}})
        fast = self.s.save_profile({"profile": {"height_cm": 172, "current_weight_kg": 100, "target_weight_kg": 60}, "plan": {"program_weeks": 4, "timezone": TZ_NAME}})
        self.assertTrue(fast["warning"])

    def test_profile_corruption_is_explicit(self):
        (self.root / "profile.json").write_text("{broken", encoding="utf-8")
        with self.assertRaises(ServiceError) as ctx:
            CalorieService(self.root, now_fn=lambda: self.clock)
        self.assertIn("profile.json 无法解析", str(ctx.exception))

    def test_dashboard_without_profile_does_not_expose_defaults(self):
        payload = self.s.dashboard_payload()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["configured"])
        self.assertIsNone(payload["settings"])
        self.assertIsNone(payload["today"])
