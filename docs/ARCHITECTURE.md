# Keywords Masna3 — Architecture & Research Integrity

## Design principles

1. **Project isolation:** config and snapshots live under `projects/<slug>/`; the shared engine has no niche-specific rules.
2. **Evidence over guesses:** seed terms are hypotheses; provider suggestions are tagged with source and query; volume and organic difficulty stay null unless verified.
3. **Reproducible research:** stable JSONL snapshots and query frontier can be reconstructed on another machine.
4. **Budget guards:** low request caps, 21-day refresh, pauses, no proxy rotation, no captcha solving, no retries around access denials.
5. **Local-first:** use an in-memory SQLite working store and commit human-readable JSONL/CSV reports instead of repeatedly committing a binary database.
6. **Privacy:** no account IDs, secrets, email lists or customer data should enter a public project snapshot.

## Data path

Project JSON config → seed import → provider adapter → normalized keyword registry + per-source evidence → query frontier → transparent heuristic ranking → per-project CSV + Markdown report → Git commit.

### Keyword schema (`data/keywords.jsonl`)

Each line is an object with:
- `locale`, `normalized`, `phrase`
- `first_seen`, `last_seen` (ISO 8601 UTC)
- `evidence`: keyed by provider, with `first_seen`, `last_seen`, `observations` and `example_query`

The `seed` provider represents an unverified researcher hypothesis. Locale plus normalized phrase is the uniqueness key. Language-aware morphological clustering is **not** implemented yet; normalization does not equate translations or synonyms.

### Query frontier (`data/queries.jsonl`)

Each line tracks `locale`, `provider`, `normalized`, `phrase`, `last_run`, `results`, and `novel`. Previously run queries must age past the refresh window. Novel suggestions become candidates on later runs, so the research space expands over time.

### Opportunity CSV

`priority_score` uses:
- 50% lexical resemblance to project seeds;
- 35% configured buying-intent signal matches;
- 15% independent source evidence.

Negative signals apply a fixed penalty. This ranking only sorts research tasks; it is **not a calibrated conversion probability or measured ranking difficulty**. Source confidence means `seed-only`, `single-source`, or `multi-source`, not statistical validation. Rankings are only approximately useful within a locale.

`monthly_search_volume` and `organic_keyword_difficulty` stay blank rather than invented.

## Current source contracts

| Source | Access | Research evidence | Notes |
| --- | --- | --- | --- |
| Brave Autosuggest | Official API, optional key | Search suggestions | May require account/billing setup even under a free monthly credit. |
| Google suggestions | Unofficial, manual opt-in | Search suggestions | Endpoint behavior/terms can change; no guaranteed quota. |
| DuckDuckGo suggestions | Unofficial, manual opt-in | Search suggestions | Endpoint behavior/terms can change; no guaranteed quota. |

No paid-service scraping. A 401, 403 or 429 causes that provider to stop for the current run; the engine does not evade rate limits.

## Next milestones (not included yet)

- Add provider contract tests with mocked responses, bounded per-source budgets and run telemetry.
- Market-specific discovery strategies and multilingual semantic grouping with optional local models.
- First-party GSC import after site verification, with real clicks, impressions and positions.
- Optional SERP review adapters and visible manual evidence trails for competitiveness.
- Search trend enrichment, staleness monitoring, and feedback-based frontier priorities.
- Real durable transactional database + web UI if keyword count outgrows Git-friendly snapshots.
- Formal licensing, contribution policy, and documentation for self-hosted deployment.

## Known limitations

- No native Google search-volume API or reliable free organic keyword-difficulty score.
- The in-memory SQLite store is reconstructed from JSONL on each run; not for multi-writer concurrency.
- The query frontier is heuristic and not a trained autonomous agent.
- Reports use daily filenames, so multiple runs on the same date replace that day's summary.
- A cron job cannot create external evidence without a working provider and its allowed quota.
