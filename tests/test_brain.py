"""Offline tests for adaptive research plan and source-evidence integrity."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from masna3.brain import make_plan, plan_all, ranked_queries
from masna3.store import Store


LOCALE = {
    "code": "en-US", "language": "en", "country": "US",
    "seeds": ["qr code menu for restaurants", "digital menu software"],
    "buying_signals": ["best", "software", "pricing"],
    "exclude_signals": ["jobs"],
}


class BrainTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / "projects" / "demo"
        self.folder.mkdir(parents=True)
        self.config = {"slug": "demo", "name": "Demo", "locales": [LOCALE]}
        (self.folder / "project.json").write_text(
            json.dumps(self.config), encoding="utf-8"
        )
        self.store = Store(self.folder)
        self.store.observe("en-US", "qr code menu for restaurants", "seed")
        self.store.observe("en-US", "digital menu software", "seed")
        self.store.observe("en-US", "best digital menu software", "agent_hypothesis")
        self.store.observe("en-US", "restaurant menu pricing", "brave")

    def test_plan_does_not_fake_api_access(self):
        with patch.dict(os.environ, {}, clear=True):
            plan = make_plan(self.folder, self.config, self.store, ["brave"])
        self.assertFalse(plan["source_status"]["brave"]["ready"])
        self.assertEqual(plan["ready_queries"], 0)
        self.assertEqual(plan["markets"][0]["with_suggestion_evidence"], 1)
        self.assertIsNone(plan["integrity"]["monthly_search_volume"])
        self.assertTrue((self.folder / "brain/next_actions.json").is_file())

    def test_seed_and_agent_hypothesis_are_not_verified(self):
        with patch.dict(os.environ, {"BRAVE_API_KEY": "mock"}, clear=True):
            plan = make_plan(self.folder, self.config, self.store, ["brave"])
        self.assertTrue(plan["source_status"]["brave"]["ready"])
        self.assertGreater(plan["ready_queries"], 0)
        by_query = {
            entry["query"]: entry
            for entry in plan["markets"][0]["providers"]["brave"]["next_queries"]
        }
        if "best digital menu software" in by_query:
            self.assertEqual(by_query["best digital menu software"]["verified_suggestion_sources"], [])
        self.assertEqual(plan["markets"][0]["with_suggestion_evidence"], 1)

    def test_refresh_and_zero_yield_penalty(self):
        now = "2026-10-10T12:00:00+00:00"
        before = ranked_queries(self.store, LOCALE, "brave", 10, now=now)
        self.assertIn("digital menu software", [r["query"] for r in before])
        self.store.record_query(
            "en-US", "brave", "digital menu software", 8, 0, now="2026-09-01T12:00:00+00:00"
        )
        after = ranked_queries(self.store, LOCALE, "brave", 10, now=now)
        first = next(r for r in before if r["query"] == "digital menu software")
        second = next(r for r in after if r["query"] == "digital menu software")
        self.assertLess(second["priority"], first["priority"])
        self.assertIn("previous_query_found_no_new_terms", second["reasons"])
        fresh = ranked_queries(self.store, LOCALE, "brave", 10,
                               now="2026-09-02T12:00:00+00:00")
        self.assertNotIn("digital menu software", [r["query"] for r in fresh])

    def test_plan_all_is_project_scoped(self):
        self.store.export()
        other = self.root / "projects" / "other"
        other.mkdir()
        (other / "project.json").write_text(json.dumps({
            "slug": "other", "name": "Other",
            "locales": [{**LOCALE, "seeds": ["fitness booking software"]}],
        }), encoding="utf-8")
        with patch.dict(os.environ, {}, clear=True):
            summaries = plan_all(self.root)
        self.assertEqual([s["project"] for s in summaries], ["demo", "other"])
        self.assertTrue((other / "brain/next_actions.json").exists())
        only_other = (other / "brain/next_actions.json").read_text(encoding="utf-8")
        self.assertNotIn("restaurant menu pricing", only_other)


if __name__ == "__main__":
    unittest.main()
