import datetime as dt
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

from backend.agent_adapter import process_payload
from backend.image_candidates import CandidateStore
from backend.service import CalorieService, ServiceError, TZ_NAME

TZ = ZoneInfo(TZ_NAME)


class ImageCandidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = CalorieService(Path(self.tmp.name), now_fn=lambda: dt.datetime(2026, 7, 18, 12, 0, tzinfo=TZ))
        self.candidate = {"source_type": "meal_photo", "confidence": "low", "meal_label": "午餐", "items": [{"name": "鸡胸饭", "quantity": "1份", "estimated_calories": 520, "estimated_protein_g": 42}], "assumptions": ["米饭按半碗估算"]}

    def tearDown(self):
        self.tmp.cleanup()

    def test_submit_does_not_write_and_confirm_writes_once(self):
        submitted = process_payload(self.service, {"operation": "candidate_submit", "request_id": "image-1", "candidate": self.candidate})
        self.assertTrue(submitted["ok"])
        self.assertEqual([], self.service.read_all_events())
        confirmed = process_payload(self.service, {"operation": "candidate_confirm", "pending_id": submitted["pending_id"], "request_id": "image-1"})
        self.assertTrue(confirmed["ok"])
        self.assertEqual(1, len(self.service.read_all_events()))
        event = self.service.read_all_events()[0]
        self.assertEqual("image_candidate", event["nutrition_source"])
        self.assertIn("米饭按半碗估算", event["notes"])

    def test_correction_becomes_final_value_and_bad_candidate_fails(self):
        stored = CandidateStore(self.service).submit(self.candidate, "image-2")
        outcome = CandidateStore(self.service).confirm(stored["pending_id"], {"items": [{"name": "鸡胸饭", "quantity": "大份", "estimated_calories": 700, "estimated_protein_g": 50}], "source_type": "meal_photo", "confidence": "medium", "assumptions": ["用户修正份量"]}, "image-2")
        self.assertFalse(outcome["duplicate"])
        self.assertEqual(700, self.service.read_all_events()[0]["estimated_total_calories"])
        bad = process_payload(self.service, {"operation": "candidate_submit", "candidate": {"source_type": "meal_photo", "confidence": "low", "items": []}})
        self.assertFalse(bad["ok"])

    def test_candidate_replay_and_missing_candidate_are_safe(self):
        first = CandidateStore(self.service).submit(self.candidate, "image-3")
        second = CandidateStore(self.service).submit(self.candidate, "image-3")
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["pending_id"], second["pending_id"])
        with self.assertRaises(ServiceError):
            CandidateStore(self.service).confirm("missing", None)


if __name__ == "__main__":
    unittest.main()
