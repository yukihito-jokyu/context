from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "serve_review.py"
SPEC = importlib.util.spec_from_file_location("self_review_serve_review", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def feedback(approved: object) -> dict:
    return {
        "schema_version": "1.0",
        "report": {"target": "main", "source": "feature/110"},
        "reviews": [
            {
                "review_id": "review-example",
                "approved": approved,
                "feedback": "",
            }
        ],
        "manual_comments": [],
    }


class FeedbackValidationTest(unittest.TestCase):
    def test_accepts_boolean_approval(self) -> None:
        self.assertEqual(MODULE.validate_feedback(feedback(True)), feedback(True))

    def test_rejects_missing_approval(self) -> None:
        value = feedback(False)
        del value["reviews"][0]["approved"]
        with self.assertRaises(ValueError):
            MODULE.validate_feedback(value)

    def test_rejects_non_boolean_approval(self) -> None:
        with self.assertRaises(ValueError):
            MODULE.validate_feedback(feedback("true"))


if __name__ == "__main__":
    unittest.main()
