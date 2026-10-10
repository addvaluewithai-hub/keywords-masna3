"""Offline tests for the agent-only queue contract."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from masna3.agent_jobs import process_jobs
from masna3.store import Store


class AgentQueueTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        project = self.root / "projects" / "qserve"
        project.mkdir(parents=True)
        (project / "project.json").write_text(json.dumps({
            "slug": "qserve", "name": "QServe",
            "locales": [{
                "code": "en-US", "language": "en", "country": "US",
                "seeds": ["qr menu"], "buying_signals": ["best"],
            }],
        }), encoding="utf-8")
        self.inbox = self.root / "jobs" / "requests"
        self.inbox.mkdir(parents=True)

    def submit(self, job_id, payload):
        (self.inbox / (job_id + ".json")).write_text(
            json.dumps(payload), encoding="utf-8"
        )

    def test_propose_and_idempotence(self):
        payload = {
            "version": 1, "job_id": "qserve-proposal-001",
            "kind": "propose", "project": "qserve",
            "proposals": [{
                "locale": "en-US", "keyword": "best qr menu platform",
                "reason": "Plausible commercial term, not verified by an API",
            }],
        }
        self.submit(payload["job_id"], payload)
        done = process_jobs(self.root)
        self.assertEqual(done[0]["status"], "completed_with_notices")
        self.assertEqual(done[0]["summary"]["proposed_new"], 1)
        self.assertEqual(process_jobs(self.root), [])
        rows = Store(self.root / "projects" / "qserve").keywords()
        self.assertEqual(len(rows), 2)
        self.assertTrue(any("agent_hypothesis" in row["evidence"] for row in rows))
        ranking = (self.root / "projects/qserve/opportunities/latest.csv").read_text()
        self.assertIn("seed-only", ranking)
        self.assertTrue((self.root / "jobs/results/qserve-proposal-001.json").exists())

    def test_invalid_cannot_block_valid(self):
        self.submit("aaaaaa", {
            "version": 1, "job_id": "aaaaaa", "kind": "research",
            "project": "qserve", "providers": ["google"], "allow_unofficial": False,
        })
        self.submit("bbbbbb", {
            "version": 1, "job_id": "bbbbbb", "kind": "research",
            "project": "qserve", "providers": [],
        })
        results = process_jobs(self.root)
        self.assertEqual([r["status"] for r in results], ["failed", "completed"])

    def test_planner_job_produces_machine_plan_without_network(self):
        self.submit("planjob1", {
            "version": 1, "job_id": "planjob1", "kind": "plan",
            "project": "qserve",
        })
        results = process_jobs(self.root)
        self.assertEqual(results[0]["status"], "completed_with_notices")
        self.assertEqual(results[0]["summary"]["requests"], 0)
        plan_path = self.root / "projects/qserve/brain/next_actions.json"
        self.assertTrue(plan_path.exists())
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["project"], "qserve")
        self.assertEqual(plan["markets"][0]["locale"], "en-US")
        self.assertEqual(process_jobs(self.root), [])

    def test_reject_bad_locale_and_limits(self):
        self.submit("cccccc", {
            "version": 1, "job_id": "cccccc", "kind": "propose", "project": "qserve",
            "proposals": [{
                "locale": "fr-FR", "keyword": "menu digital", "reason": "unconfigured locale",
            }],
        })
        self.submit("dddddd", {
            "version": 1, "job_id": "dddddd", "kind": "research",
            "project": "qserve", "providers": [], "per_locale": 500,
        })
        results = process_jobs(self.root)
        self.assertTrue(all(r["status"] == "failed" for r in results))
        self.assertFalse((self.root / "projects/qserve/data/keywords.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
