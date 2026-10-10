"""Offline tests: no API key, requests, or external dependencies required."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from masna3.engine import evaluate, run_project
from masna3.store import Store, normalize


class FactoryTests(unittest.TestCase):
    def test_unicode_normalization_and_dedup(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d))
            self.assertEqual(normalize("  QR   MENU "), "qr menu")
            self.assertTrue(store.observe("en-US", "QR Menu", "seed", now="2026-10-10T00:00:00+00:00"))
            self.assertFalse(store.observe("en-US", "qr  menu", "seed", now="2026-10-11T00:00:00+00:00"))
            self.assertFalse(store.observe("en-US", "qr menu", "brave", now="2026-10-12T00:00:00+00:00"))
            row = store.keywords()[0]
            self.assertEqual(len(row["evidence"]), 2)
            self.assertEqual(row["evidence"]["seed"]["observations"], 1)

    def test_snapshot_roundtrip_and_frontier(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            first = Store(folder)
            first.observe("es-MX", "menú digital", "seed", now="2026-10-01T00:00:00+00:00")
            first.observe("es-MX", "menú digital gratis", "brave", now="2026-10-01T00:00:00+00:00")
            first.record_query("es-MX", "brave", "menú digital", 10, 1, now="2026-10-01T00:00:00+00:00")
            first.export()
            second = Store(folder)
            self.assertEqual(len(second.keywords()), 2)
            choices = second.candidates(
                "es-MX", ["menú digital"], "brave", 4, 21,
                now="2026-10-02T00:00:00+00:00",
            )
            self.assertNotIn("menú digital", choices)
            self.assertIn("menú digital gratis", choices)

    def test_scoring_never_fabricates_volume(self):
        row = {
            "locale": "en-US", "phrase": "best menu software",
            "evidence": {"seed": {}, "brave": {}},
            "first_seen": "x", "last_seen": "x",
        }
        loc = {
            "seeds": ["menu software"],
            "buying_signals": ["best", "software"],
        }
        result = evaluate(row, loc)
        self.assertEqual(result["monthly_search_volume"], "")
        self.assertEqual(result["organic_keyword_difficulty"], "")
        self.assertGreater(result["priority_score"], 50)

    def test_project_run_offline_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for slug, seed in [("alpha", "qr menu"), ("beta", "yoga software")]:
                folder = root / "projects" / slug
                folder.mkdir(parents=True)
                config = {
                    "slug": slug, "name": slug,
                    "locales": [{
                        "code": "en-US", "country": "US", "language": "en",
                        "seeds": [seed], "buying_signals": ["software"]
                    }],
                }
                (folder / "project.json").write_text(json.dumps(config), encoding="utf-8")
            first = run_project(root, "alpha", [], pause_seconds=0)
            second = run_project(root, "alpha", [], pause_seconds=0)
            run_project(root, "beta", [], pause_seconds=0)
            self.assertEqual(first["new"], 1)
            self.assertEqual(second["new"], 0)
            self.assertEqual(first["total"], 1)
            alpha = (root / "projects/alpha/data/keywords.jsonl").read_text()
            beta = (root / "projects/beta/data/keywords.jsonl").read_text()
            self.assertIn("qr menu", alpha)
            self.assertNotIn("yoga software", alpha)
            self.assertIn("yoga software", beta)
            self.assertTrue((root / "projects/alpha/opportunities/latest.csv").exists())


if __name__ == "__main__":
    unittest.main()
