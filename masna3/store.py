"""SQLite working store with Git-friendly JSONL snapshots as durable state."""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


class Store:
    """Each project owns one independent store; only its exports are committed."""

    def __init__(self, folder: Path):
        self.folder = folder
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            CREATE TABLE keywords (
                locale TEXT NOT NULL,
                normalized TEXT NOT NULL,
                phrase TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                evidence TEXT NOT NULL,
                PRIMARY KEY (locale, normalized)
            );
            CREATE TABLE queries (
                locale TEXT NOT NULL,
                provider TEXT NOT NULL,
                normalized TEXT NOT NULL,
                phrase TEXT NOT NULL,
                last_run TEXT NOT NULL,
                results INTEGER NOT NULL,
                novel INTEGER NOT NULL,
                PRIMARY KEY (locale, provider, normalized)
            );
            CREATE TABLE query_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                locale TEXT NOT NULL,
                provider TEXT NOT NULL,
                phrase TEXT NOT NULL,
                run_at TEXT NOT NULL,
                results INTEGER NOT NULL,
                novel INTEGER NOT NULL
            );
            """
        )
        self._restore()

    def _restore(self) -> None:
        keyword_path = self.folder / "data" / "keywords.jsonl"
        if keyword_path.exists():
            for line in keyword_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                self.db.execute(
                    "INSERT INTO keywords VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        row["locale"], row["normalized"], row["phrase"],
                        row["first_seen"], row["last_seen"],
                        json.dumps(row["evidence"], ensure_ascii=False, sort_keys=True),
                    ),
                )
        query_path = self.folder / "data" / "queries.jsonl"
        if query_path.exists():
            for line in query_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                self.db.execute(
                    "INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        row["locale"], row["provider"], row["normalized"], row["phrase"],
                        row["last_run"], row["results"], row["novel"],
                    ),
                )
        event_path = self.folder / "data" / "query_events.jsonl"
        if event_path.exists():
            for line in event_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                self.db.execute(
                    "INSERT INTO query_events(locale, provider, phrase, run_at, results, novel) VALUES (?, ?, ?, ?, ?, ?)",
                    (event["locale"], event["provider"], event["phrase"],
                     event["run_at"], event["results"], event["novel"]),
                )
        self.db.commit()

    def observe(self, locale: str, phrase: str, source: str, query: str = "",
                now: str | None = None) -> bool:
        """Return True iff this is a brand-new keyword; evidence is retained by source."""
        phrase = re.sub(r"\s+", " ", phrase).strip()
        key = normalize(phrase)
        if not key or len(key) > 180 or any(ord(c) < 32 for c in phrase):
            return False
        now = now or utc_now()
        row = self.db.execute(
            "SELECT evidence FROM keywords WHERE locale=? AND normalized=?",
            (locale, key),
        ).fetchone()
        if row is None:
            evidence = {source: {"first_seen": now, "last_seen": now,
                                 "observations": 1, "example_query": query}}
            self.db.execute(
                "INSERT INTO keywords VALUES (?, ?, ?, ?, ?, ?)",
                (locale, key, phrase, now, now,
                 json.dumps(evidence, ensure_ascii=False, sort_keys=True)),
            )
            self.db.commit()
            return True
        evidence = json.loads(row["evidence"])
        if source == "seed" and source in evidence:
            return False  # Replaying project seeds must not fake a new observation.
        if source not in evidence:
            evidence[source] = {"first_seen": now, "last_seen": now,
                                "observations": 0, "example_query": query}
        evidence[source]["last_seen"] = now
        evidence[source]["observations"] += 1
        evidence[source]["example_query"] = query
        self.db.execute(
            "UPDATE keywords SET last_seen=?, evidence=? WHERE locale=? AND normalized=?",
            (now, json.dumps(evidence, ensure_ascii=False, sort_keys=True), locale, key),
        )
        self.db.commit()
        return False

    def keywords(self, locale: str | None = None) -> list[dict]:
        if locale:
            rows = self.db.execute(
                "SELECT * FROM keywords WHERE locale=? ORDER BY normalized", (locale,)
            ).fetchall()
        else:
            rows = self.db.execute(
                "SELECT * FROM keywords ORDER BY locale, normalized"
            ).fetchall()
        return [{**dict(row), "evidence": json.loads(row["evidence"])} for row in rows]

    def candidates(self, locale: str, seeds: list[str], provider: str, limit: int,
                   refresh_days: int = 21, now: str | None = None) -> list[str]:
        now_dt = datetime.fromisoformat(now or utc_now())
        historical = {r["normalized"]: r for r in self.db.execute(
            "SELECT * FROM queries WHERE locale=? AND provider=?", (locale, provider)
        ).fetchall()}
        seed_keys = {normalize(seed) for seed in seeds}
        combined: dict[str, str] = {}
        for seed in seeds:
            if normalize(seed):
                combined[normalize(seed)] = seed
        # Only use previously observed suggestions, not AI-fabricated queries.
        for row in self.keywords(locale):
            if len(row["phrase"]) <= 80:
                combined.setdefault(row["normalized"], row["phrase"])
        eligible = []
        for key, phrase in combined.items():
            prior = historical.get(key)
            if prior:
                when = datetime.fromisoformat(prior["last_run"])
                if now_dt - when < timedelta(days=refresh_days):
                    continue
            eligible.append((
                0 if prior is None else 1,
                0 if key in seed_keys else 1,
                prior["last_run"] if prior else "",
                key, phrase,
            ))
        eligible.sort()
        return [item[-1] for item in eligible[:limit]]

    def record_query(self, locale: str, provider: str, phrase: str,
                     results: int, novel: int, now: str | None = None) -> None:
        now = now or utc_now()
        self.db.execute(
            "INSERT INTO query_events(locale, provider, phrase, run_at, results, novel) VALUES (?, ?, ?, ?, ?, ?)",
            (locale, provider, phrase, now, results, novel),
        )
        self.db.execute(
            """INSERT INTO queries VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(locale, provider, normalized) DO UPDATE SET
               phrase=excluded.phrase, last_run=excluded.last_run,
               results=excluded.results, novel=excluded.novel""",
            (locale, provider, normalize(phrase), phrase, now, results, novel),
        )
        self.db.commit()

    def export(self) -> None:
        rows = self.keywords()
        kw_lines = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                           for row in rows)
        query_rows = [dict(r) for r in self.db.execute(
            "SELECT * FROM queries ORDER BY locale, provider, normalized"
        ).fetchall()]
        query_lines = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
                              for row in query_rows)
        write_if_changed(self.folder / "data" / "keywords.jsonl", kw_lines)
        write_if_changed(self.folder / "data" / "queries.jsonl", query_lines)
        event_rows = self.db.execute(
            "SELECT locale, provider, phrase, run_at, results, novel FROM query_events ORDER BY seq"
        ).fetchall()
        event_lines = "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in event_rows
        )
        write_if_changed(self.folder / "data" / "query_events.jsonl", event_lines)
