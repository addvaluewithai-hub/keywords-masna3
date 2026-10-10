"""Project runner, explainable heuristic prioritization, and reports."""
from __future__ import annotations

import csv
import io
import json
import re
import time
from datetime import date
from pathlib import Path

from .providers import ProviderError, available, suggest
from .store import Store, normalize, utc_now, write_if_changed


def config_for(root: Path, project: str) -> tuple[Path, dict]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", project):
        raise ValueError("Project must be a lowercase slug")
    folder = root / "projects" / project
    path = folder / "project.json"
    if not path.is_file():
        raise ValueError(f"Project not found: {project}")
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("slug") != project or not config.get("locales"):
        raise ValueError(f"Invalid project configuration: {project}")
    for loc in config["locales"]:
        if not loc.get("code") or not loc.get("seeds") or not loc.get("language") or not loc.get("country"):
            raise ValueError(f"Locale requires code, seeds, language and country: {project}")
    return folder, config


def evaluate(row: dict, locale_config: dict) -> dict:
    """Transparent ranking heuristic: NOT search volume or measured SEO difficulty."""
    keyword = normalize(row["phrase"])
    seeds = locale_config["seeds"]
    terms = set(keyword.split())
    similarities = []
    for seed in seeds:
        st = set(normalize(seed).split())
        similarities.append(len(terms & st) / len(terms | st) if (terms | st) else 0)
    relevance = round(35 + 65 * max(similarities or [0]))
    commercial_signals = [normalize(s) for s in locale_config.get("buying_signals", [])]
    matched = [s for s in commercial_signals if s in keyword]
    intent = min(100, 20 + 40 * len(matched))
    independent = len(set(row["evidence"]) - {"seed", "agent_hypothesis"})
    evidence_strength = min(100, 25 * independent)
    score = round(0.50 * relevance + 0.35 * intent + 0.15 * evidence_strength)
    negative = [normalize(s) for s in locale_config.get("exclude_signals", [])]
    if any(s in keyword for s in negative):
        score = max(0, score - 35)
    confidence = "seed-only" if independent == 0 else ("multi-source" if independent >= 2 else "single-source")
    return {
        "locale": row["locale"],
        "keyword": row["phrase"],
        "priority_score": score,
        "confidence": confidence,
        "intent_signal_matches": ", ".join(matched),
        "sources": ", ".join(sorted(row["evidence"])),
        "first_seen": row["first_seen"],
        "last_seen": row["last_seen"],
        "monthly_search_volume": "",  # never invent these metrics
        "organic_keyword_difficulty": "",
    }


def export_reports(folder: Path, config: dict, store: Store, outcome: dict) -> None:
    configs = {loc["code"]: loc for loc in config["locales"]}
    scored = sorted(
        [evaluate(row, configs[row["locale"]]) for row in store.keywords()],
        key=lambda row: (-row["priority_score"], row["locale"], row["keyword"].casefold()),
    )
    headers = [
        "locale", "keyword", "priority_score", "confidence", "intent_signal_matches",
        "sources", "first_seen", "last_seen", "monthly_search_volume",
        "organic_keyword_difficulty",
    ]
    csv_file = io.StringIO()
    writer = csv.DictWriter(csv_file, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    writer.writerows(scored)
    write_if_changed(folder / "opportunities" / "latest.csv", csv_file.getvalue())

    report = [
        f"# Keyword research: {config['name']}",
        "",
        f"Run: {outcome['date']}  |  Project: {config['slug']}",
        "",
        f"- Total known keywords: **{len(scored)}**",
        f"- New keywords this run: **{outcome['new']}**",
        f"- Successful provider requests: **{outcome['requests']}**",
        f"- Sources selected: **{', '.join(outcome['sources']) or 'seed-only'}**",
        "",
        "## Top 20 research opportunities",
        "",
        "| Locale | Keyword | Heuristic priority | Evidence |",
        "|---|---|---:|---|",
    ]
    for row in scored[:20]:
        safe = row["keyword"].replace("|", "\\|").replace("\n", " ")
        report.append(
            f"| {row['locale']} | {safe} | {row['priority_score']} | {row['confidence']} |"
        )
    if outcome["notices"]:
        report += ["", "## Provider notices", ""]
        report.extend(f"- {notice}" for notice in outcome["notices"])
    report += [
        "",
        "## Measurement integrity",
        "",
        "The priority score is a local heuristic based on lexical relevance, buying-intent ",
        "signals and independent suggestion sources. It is **not** a search-volume,",
        "SEO-difficulty, ranking or conversion estimate. Missing metrics remain blank.",
        "Seeds are hypotheses, not validated demand. Only real provider responses count",
        "as independent evidence. Manual SERP review is required before publishing.",
        "",
    ]
    content = "\n".join(report)
    write_if_changed(folder / "reports" / "latest.md", content)
    run_history = {
        "date": outcome["date"], "project": config["slug"], "known_keywords": len(scored),
        "new_keywords": outcome["new"], "requests": outcome["requests"],
        "sources": outcome["sources"], "notices": outcome["notices"],
    }
    write_if_changed(
        folder / "reports" / "history" / f"{date.today().isoformat()}.json",
        json.dumps(run_history, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )


def run_project(root: Path, project: str, sources: list[str], per_locale: int = 4,
                allow_unofficial: bool = False, refresh_days: int = 21,
                pause_seconds: float = 1.0) -> dict:
    if not 1 <= per_locale <= 20:
        raise ValueError("per_locale must be between 1 and 20")
    if not 1 <= refresh_days <= 365:
        raise ValueError("refresh_days must be between 1 and 365")
    folder, config = config_for(root, project)
    store = Store(folder)
    outcome = {
        "project": project, "date": date.today().isoformat(), "new": 0,
        "requests": 0, "sources": sources, "notices": [],
    }
    for loc in config["locales"]:
        for seed in loc["seeds"]:
            outcome["new"] += int(store.observe(loc["code"], seed, "seed", query="project config"))
    for source in dict.fromkeys(sources):
        usable, reason = available(source, allow_unofficial)
        if not usable:
            outcome["notices"].append(f"{source}: {reason}")
            continue
        throttled = False
        for loc in config["locales"]:
            if throttled:
                break
            # Feed provider requests from the evidence-led adaptive frontier.
            from .brain import ranked_queries
            queries = [item["query"] for item in ranked_queries(
                store, loc, source, per_locale, refresh_days=refresh_days
            )]
            for query in queries:
                try:
                    suggestions = suggest(source, query, loc["language"], loc["country"])
                except ProviderError as exc:
                    outcome["notices"].append(f"{source} / {loc['code']}: {exc}")
                    if str(exc) in {"HTTP 429", "HTTP 401", "HTTP 403"}:
                        throttled = True
                        break  # Never bypass rate limits or access restrictions.
                    continue
                novel = 0
                for phrase in suggestions:
                    if store.observe(loc["code"], phrase, source, query=query):
                        novel += 1
                store.record_query(loc["code"], source, query, len(suggestions), novel)
                outcome["new"] += novel
                outcome["requests"] += 1
                if pause_seconds > 0:
                    time.sleep(pause_seconds)
    store.export()
    export_reports(folder, config, store, outcome)
    from .brain import make_plan
    make_plan(folder, config, store)
    outcome["total"] = len(store.keywords())
    return outcome
