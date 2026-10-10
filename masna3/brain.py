"""Deterministic research brain: evidence-led next-query selection, no invented metrics.

No LLM or paid API required. Ranks *research work*, not keyword popularity.
The planner never contacts external providers; provider readiness is reported.
"""
from __future__ import annotations

import json
from pathlib import Path

from .providers import available
from .store import Store, normalize, utc_now, write_if_changed

SUPPORTED = ("brave", "google", "duckduckgo")
HYPOTHESES = {"seed", "agent_hypothesis"}


def ranked_queries(store: Store, locale: dict, provider: str, limit: int,
                   refresh_days: int = 21, now: str | None = None) -> list[dict]:
    """Return explanations and bounded, reproducible research candidates."""
    from .engine import evaluate  # Delayed to keep scoring module independent.

    code = locale["code"]
    keywords = {r["normalized"]: r for r in store.keywords(code)}
    history = {
        r["normalized"]: dict(r) for r in store.db.execute(
            "SELECT * FROM queries WHERE locale=? AND provider=?",
            (code, provider),
        ).fetchall()
    }
    probes = locale.get("probes", [])
    # Probes are *query prompts*, NOT keywords and never become evidence
    # until an external suggestion source actually returns a phrase.
    proposed = store.candidates(
        code, list(dict.fromkeys(locale["seeds"] + probes)), provider, limit=5000,
        refresh_days=refresh_days, now=now,
    )
    ranked = []
    probe_keys = {normalize(p) for p in probes}
    for phrase in proposed:
        norm = normalize(phrase)
        evidence = keywords.get(norm, {}).get("evidence", {"seed": {}})
        keyword = keywords.get(norm, {
            "locale": code, "phrase": phrase, "evidence": evidence,
            "first_seen": "", "last_seen": "",
        })
        base = evaluate(keyword, locale)
        verified_sources = sorted(set(evidence) - HYPOTHESES)
        prior = history.get(norm)
        reasons = []
        if base["intent_signal_matches"]:
            reasons.append("buying_signal")
        if norm in probe_keys:
            reasons.append("unverified_exploration_probe")
        if verified_sources:
            reasons.append("observed_in_suggestion_source")
        else:
            reasons.append("unverified_research_candidate")
        if not prior:
            reasons.append("first_query_for_provider")
        elif prior["novel"] == 0:
            reasons.append("previous_query_found_no_new_terms")
        else:
            reasons.append("previous_query_produced_new_terms")

        # Exploration bonuses; repeated zero-yield queries are deprioritized.
        # Scores are research queue priorities, not measured SEO metrics.
        score = int(base["priority_score"])
        if norm in probe_keys and not verified_sources:
            score += 25  # Favor compact probes over repeatedly barren long seeds.
        score += min(12, 6 * len(verified_sources))
        if provider not in evidence:
            score += 5  # Independent-source verification opportunity.
        if prior is None:
            score += 12
        elif prior["novel"] == 0:
            score -= 22
        else:
            score += min(15, 3 * prior["novel"])
        score = max(0, min(100, score))
        ranked.append({
            "query": phrase, "priority": score,
            "reasons": reasons,
            "verified_suggestion_sources": verified_sources,
            "previous_results": prior["results"] if prior else None,
            "previous_novel": prior["novel"] if prior else None,
        })
    ranked.sort(key=lambda row: (-row["priority"], normalize(row["query"])))
    return ranked[:limit]


def make_plan(folder: Path, config: dict, store: Store,
              providers: list[str] | None = None,
              allow_unofficial: bool = False, per_locale: int = 3,
              refresh_days: int = 21, now: str | None = None) -> dict:
    providers = list(dict.fromkeys(providers if providers is not None else SUPPORTED))
    if not 1 <= per_locale <= 20 or not 1 <= refresh_days <= 365:
        raise ValueError("Invalid research planning limit")
    if any(p not in SUPPORTED for p in providers):
        raise ValueError("Unsupported research provider")
    markets = []
    provider_states = {}
    for provider in providers:
        enabled, reason = available(provider, allow_unofficial)
        past = store.db.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(novel), 0) AS new FROM query_events WHERE provider=?",
            (provider,),
        ).fetchone()
        provider_states[provider] = {
            "ready": enabled,
            "blocker": None if enabled else reason,
            "recorded_request_events": past["n"],
            "recorded_novel_events": past["new"],
            "recorded_novel_per_request": (
                round(past["new"] / past["n"], 3) if past["n"] else None
            ),
            "sample_size_warning": "insufficient_requests" if past["n"] < 10 else None,
            "historical_requests": store.db.execute(
                "SELECT COUNT(*) FROM queries WHERE provider=?", (provider,)
            ).fetchone()[0],
            "historical_new_keywords": store.db.execute(
                "SELECT COALESCE(SUM(novel), 0) FROM queries WHERE provider=?",
                (provider,),
            ).fetchone()[0],
        }
    total_ready = 0
    for locale in config["locales"]:
        code = locale["code"]
        rows = store.keywords(code)
        verified = sum(bool(set(row["evidence"]) - HYPOTHESES) for row in rows)
        lane = {
            "locale": code,
            "country": locale["country"],
            "language": locale["language"],
            "known_keywords": len(rows),
            "with_suggestion_evidence": verified,
            "without_suggestion_evidence": len(rows) - verified,
            "providers": {},
        }
        for provider in providers:
            candidates = ranked_queries(
                store, locale, provider, per_locale, refresh_days, now=now
            )
            ready = provider_states[provider]["ready"]
            lane["providers"][provider] = {
                "status": "ready" if ready else "blocked",
                "reason": "within_refresh_window_or_exhausted" if not candidates and ready
                          else provider_states[provider]["blocker"],
                "next_queries": candidates,
            }
            if ready:
                total_ready += len(candidates)
        markets.append(lane)
    # A source that yielded more novel queries is interesting to explore again,
    # but small samples are not treated as evidence of keyword market demand.
    ready_providers = [p for p in providers if provider_states[p]["ready"]]
    ready_providers.sort(key=lambda p: (
        -provider_states[p]["recorded_novel_per_request"]
        if provider_states[p]["recorded_novel_per_request"] is not None else 0,
        -provider_states[p]["recorded_request_events"],
        p,
    ))
    plan = {
        "schema_version": 1, "project": config["slug"],
        "generated_at": now or utc_now(),
        "objective": config.get("objective", ""),
        "stage": config.get("stage", ""),
        "strategy": "ranked_discovery_frontier",
        "source_status": provider_states,
        "preferred_ready_provider": ready_providers[0] if ready_providers else None,
        "markets": markets,
        "ready_queries": total_ready,
        "integrity": {
            "monthly_search_volume": None, "keyword_difficulty": None,
            "ranking_means": "heuristic research-priority only",
            "agent_proposals_mean": "unverified hypotheses, not search demand",
        },
        "next_action": (
            "submit_bounded_research_job" if total_ready
            else "configure_available_source_or_wait_for_refresh"
        ),
    }
    write_if_changed(
        folder / "brain" / "next_actions.json",
        json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return plan


def plan_project(root: Path, project: str, providers: list[str] | None = None,
                 allow_unofficial: bool = False, per_locale: int = 3) -> dict:
    from .engine import config_for
    folder, config = config_for(root, project)
    store = Store(folder)
    for locale in config["locales"]:
        for seed in locale["seeds"]:
            store.observe(locale["code"], seed, "seed", query="project config")
    store.export()
    plan = make_plan(
        folder, config, store, providers=providers,
        allow_unofficial=allow_unofficial, per_locale=per_locale,
    )
    return {
        "project": project, "date": plan["generated_at"][:10],
        "new": 0, "requests": 0, "sources": providers or list(SUPPORTED),
        "notices": [
            f"{name}: {state['blocker']}"
            for name, state in plan["source_status"].items() if not state["ready"]
        ],
        "total": len(store.keywords()), "ready_queries": plan["ready_queries"],
        "markets": len(plan["markets"]),
    }


def plan_all(root: Path) -> list[dict]:
    results = []
    for config in sorted((root / "projects").glob("*/project.json")):
        settings = json.loads(config.read_text(encoding="utf-8"))
        if settings.get("enabled", True) is False:
            continue
        results.append(plan_project(root, config.parent.name))
    return results
