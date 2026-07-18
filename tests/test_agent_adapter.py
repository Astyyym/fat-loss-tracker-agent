import json
import tempfile
import unittest
from pathlib import Path

from backend.agent_adapter import process_payload
from backend.service import CalorieService, TZ_NAME


class AgentAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = CalorieService(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_message_contract_and_idempotency(self):
        request = {"message": "早餐 标准早餐A", "request_id": "gateway-1", "timezone": TZ_NAME, "attachments": [{"kind": "image", "reference": "local-ref-1"}]}
        first = process_payload(self.service, request)
        second = process_payload(self.service, request)
        self.assertTrue(first["ok"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(1, len(self.service.read_all_events()))
        self.assertEqual({"ok", "markdown", "event_ids", "duplicate", "error", "kind"}, set(first))

    def test_invalid_and_ignored_requests_do_not_write(self):
        invalid = process_payload(self.service, {"message": "", "timezone": TZ_NAME})
        ignored = process_payload(self.service, {"message": "今天心情不错", "timezone": TZ_NAME})
        self.assertFalse(invalid["ok"])
        self.assertTrue(ignored["ok"])
        self.assertEqual("ignored", ignored["kind"])
        self.assertEqual([], self.service.read_all_events())

    def test_does_not_accept_unbounded_or_platform_identity_fields(self):
        result = process_payload(self.service, {"message": "早餐 鸡蛋", "timezone": TZ_NAME, "attachments": [{"kind": "image", "reference": "x" * 129}]})
        self.assertFalse(result["ok"])
        self.assertIn("attachment", result["error"])


if __name__ == "__main__":
    unittest.main()
