"""Agent-only GitHub file inbox/outbox protocol."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from .engine import config_for, export_reports, run_project
from .store import Store, utc_now, write_if_changed


JOB_ID = re.compile(r"[a-z0-9][a-z0-9-]{5,63}\Z")
PROVIDERS = frozenset({"brave", "google", "duckduckgo"})


class JobError(ValueError):
    """Invalid or unsafe agent-submitted request."""


def _required_text(value: Any, field: str, maximum: int = 180) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise JobError(f"{field} must be a non-empty string of at most {maximum} characters")
    return value.strip()


def _keys(job: dict, allowed: set[str]) -> None:
    unknown = set(job) - allowed
    if unknown:
        raise JobError("Unknown request fields: " + ", ".join(sorted(unknown)))


def _validate(job: Any, filename_id: str) -> dict:
    if not isinstance(job, dict):
        raise JobError("Request must be a JSON object")
    _keys(job, {
        "version", "job_id", "kind", "project", "providers", "per_locale",
        "allow_unofficial", "proposals",
    })
    if type(job.get("version")) is not int or job["version"] != 1:
        raise JobError("version must be 1")
    if job.get("job_id") != filename_id or not JOB_ID.fullmatch(filename_id):
        raise JobError("job_id must match the immutable request filename (6-64 slug characters)")
    job["project"] = _required_text(job.get("project"), "project", 64)
    kind = job.get("kind")
    if kind == "research":
        _keys(job, {
            "version", "job_id", "kind", "project", "providers",
            "per_locale", "allow_unofficial",
        })
        providers = job.get("providers", [])
        if not isinstance(providers, list) or len(providers) > 3:
            raise JobError("providers must be an array with up to 3 entries")
        if any(not isinstance(p, str) or p not in PROVIDERS for p in providers):
            raise JobError("Unsupported provider")
        if len(set(providers)) != len(providers):
            raise JobError("Duplicate providers are not allowed")
        limit = job.get("per_locale", 2)
        if type(limit) is not int or not 1 <= limit <= 5:
            raise JobError("per_locale must be an integer from 1 to 5")
        unofficial = job.get("allow_unofficial", False)
        if type(unofficial) is not bool:
            raise JobError("allow_unofficial must be a boolean")
        if not unofficial and any(p in {"google", "duckduckgo"} for p in providers):
            raise JobError("Unofficial providers need explicit allow_unofficial=true")
        job["providers"] = providers
        job["per_locale"] = limit
        job["allow_unofficial"] = unofficial
    elif kind == "propose":
        _keys(job, {"version", "job_id", "kind", "project", "proposals"})
        proposals = job.get("proposals")
        if not isinstance(proposals, list) or not 1 <= len(proposals) <= 50:
            raise JobError("proposals must contain 1-50 entries")
        for proposal in proposals:
            if not isinstance(proposal, dict) or set(proposal) != {"locale", "keyword", "reason"}:
                raise JobError("Each proposal needs exactly locale, keyword, reason")
            _required_text(proposal["locale"], "locale", 24)
            _required_text(proposal["keyword"], "keyword")
            _required_text(proposal["reason"], "reason", 500)
    else:
        raise JobError("kind must be research or propose")
    return job


def _propose(root: Path, job: dict) -> dict:
    folder, config = config_for(root, job["project"])
    valid_locales = {loc["code"] for loc in config["locales"]}
    for item in job["proposals"]:
        if item["locale"] not in valid_locales:
            raise JobError(f"Locale not configured: {item['locale']}")
    store = Store(folder)
    added = 0
    for loc in config["locales"]:
        for seed in loc["seeds"]:
            added += int(store.observe(loc["code"], seed, "seed", query="project config"))
    proposal_additions = 0
    for item in job["proposals"]:
        if store.observe(
            item["locale"], item["keyword"], "agent_hypothesis",
            query=item["reason"],
        ):
            proposal_additions += 1
    added += proposal_additions
    store.export()
    result = {
        "project": job["project"], "date": date.today().isoformat(),
        "new": added, "requests": 0, "sources": ["agent_hypothesis"],
        "notices": [
            "Agent proposals are research hypotheses, NOT independent evidence of search demand."
        ],
        "proposed_new": proposal_additions, "total": len(store.keywords()),
    }
    export_reports(folder, config, store, result)
    return result


def process_jobs(root: Path, max_jobs: int = 10) -> list[dict]:
    requests = root / "jobs" / "requests"
    outputs = root / "jobs" / "results"
    if not requests.exists():
        return []
    processed = []
    for path in sorted(requests.glob("*.json")):
        if len(processed) >= max_jobs:
            break
        result_path = outputs / path.name
        if result_path.exists():
            continue
        file_id = path.stem
        body = path.read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        kind = None
        project = None
        try:
            if len(body) > 32768:
                raise JobError("Request exceeds 32 KiB")
            job = _validate(json.loads(body), file_id)
            kind = job["kind"]
            project = job["project"]
            if kind == "research":
                summary = run_project(
                    root, project, job["providers"],
                    per_locale=job["per_locale"],
                    allow_unofficial=job["allow_unofficial"],
                )
            else:
                summary = _propose(root, job)
            result = {
                "version": 1, "job_id": file_id,
                "status": "completed_with_notices" if summary["notices"] else "completed",
                "kind": kind, "project": project,
                "request_sha256": digest, "finished_at": utc_now(),
                "summary": summary,
                "artifacts": {
                    "keywords": f"projects/{project}/data/keywords.jsonl",
                    "ranking": f"projects/{project}/opportunities/latest.csv",
                    "report": f"projects/{project}/reports/latest.md",
                },
            }
        except (ValueError, OSError, json.JSONDecodeError, TypeError, KeyError) as exc:
            result = {
                "version": 1, "job_id": file_id, "status": "failed",
                "kind": kind, "project": project,
                "request_sha256": digest, "finished_at": utc_now(),
                "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
            }
        write_if_changed(
            result_path, json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
        processed.append(result)
    return processed
