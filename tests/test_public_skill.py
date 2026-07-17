import re
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SKILL = ROOT / "skills/fat-loss-tracker/SKILL.md"


class PublicSkillTests(unittest.TestCase):
    def test_skill_frontmatter_and_body(self):
        content = SKILL.read_text(encoding="utf-8")
        self.assertTrue(content.startswith("---\n"))
        match = re.search(r"\n---\n", content[4:])
        self.assertIsNotNone(match)
        frontmatter = content[4:match.start() + 4]
        self.assertIn("name: fat-loss-tracker", frontmatter)
        self.assertIn("description:", frontmatter)
        self.assertIn("license: MIT", frontmatter)
        self.assertGreater(len(content[match.end() + 4:].strip()), 0)

    def test_public_skill_has_no_private_absolute_paths(self):
        content = SKILL.read_text(encoding="utf-8")
        forbidden = ["/mnt/d/", "D:\\wenjian", "/home/czk", "四周减脂记录Agent"]
        for value in forbidden:
            self.assertNotIn(value, content)
        self.assertIn("<PROJECT_ROOT>", content)
        self.assertIn("backend/service.py", content)

    def test_skill_reuses_existing_gateway_and_service(self):
        content = SKILL.read_text(encoding="utf-8")
        self.assertIn("Do not create another Telegram bot", content)
        self.assertIn("backend/service.py", content)
        self.assertIn("Never directly read, rewrite, truncate, or delete", content)


if __name__ == "__main__":
    unittest.main()
