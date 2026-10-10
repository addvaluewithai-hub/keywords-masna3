# Keywords Masna3 🏭

**A free-first, evidence-based keyword intelligence factory for any niche.**

One engine, separate research folders for each project. It discovers suggestions, tracks provenance, preserves historical runs, and creates explainable priority rankings. All core code uses **Python's standard library** (no paid SDK or API required to run seed-only research).

> **Reality check:** Autocomplete suggestions are not monthly search volume. The research score is a heuristic, not verified search volume, SEO difficulty or ranking probability. The engine never invents those measurements.

## For AI agents (primary interface)

**This is an agent-only system.** No operator dashboard and no manual workflows are required. Read [AGENTS.md](AGENTS.md) and the machine-readable [agent/manifest.json](agent/manifest.json) first.

An agent interacts entirely through connected GitHub operations: create an immutable JSON request at jobs/requests/<job_id>.json; a push-triggered Action processes it; inspect jobs/results/<job_id>.json and the output under projects/<slug>/. Requests may either record labeled hypotheses or use configured suggestion providers. No request commit should be mistaken for completed research. All results persist for the next agent.

## Current capabilities (v0.1)

- Per-project configuration in `projects/<slug>/project.json`; multiple markets and languages per project.
- Google and DuckDuckGo suggestions (**unofficial; disabled unless explicitly opted in**).
- Brave Autosuggest (official API; optional `BRAVE_API_KEY`, requires an eligible Brave plan).
- Persistent Git-friendly JSONL keyword registry, with first/last seen, source and example query.
- Keyword deduplication using Unicode normalization; separate locale records.
- Query frontier that expands from actually observed suggestions, not hallucinated queries.
- 21-day default revisit window, per-source request caps, delay between calls and no rate-limit bypasses.
- Explainable priority CSV and Markdown reports, with monthly volume and difficulty left blank.
- Unit tests, weekly GitHub Actions research workflow, and manual runs.

## Developer-only diagnostics (the agent interface is GitHub JSON jobs)

### Try it locally

Requirements: Python 3.11+.

```bash
git clone https://github.com/addvaluewithai-hub/keywords-masna3.git
cd keywords-masna3
python -m unittest discover -s tests -v
python -m masna3 projects

# No API calls: register seed hypotheses and export first reports.
python -m masna3 run --project qserve --providers none

# Official API (if you have a Brave Autosuggest key in your environment).
export BRAVE_API_KEY=your_key_here
python -m masna3 run --project qserve --providers brave --per-locale 4

# OPTIONAL experimental, unofficial endpoints — check each provider's terms.
python -m masna3 run --project qserve --providers google,duckduckgo --allow-unofficial --per-locale 2
```

Results go inside each project's folder:
- `data/keywords.jsonl` — durable registry, source evidence and observation history.
- `data/queries.jsonl` — persistent query frontier and last-attempt metadata.
- `opportunities/latest.csv` — heuristic priority and evidence classification.
- `reports/latest.md` — latest research digest.
- `reports/history/YYYY-MM-DD.json` — daily research-run summary.

## Add a project

Copy `projects/sample-fitness/project.json` to `projects/<new-slug>/project.json`. Update `slug`, `name`, `niche`, `objective` and each locale's `seeds` and optional `buying_signals` / `exclude_signals`. Then run:

```bash
python -m masna3 run --project new-slug --providers none
```

The research engine is generic; only project-specific configuration and snapshots change.

## Automation

- `Tests`: runs offline tests on pushes and pull requests.
- `Weekly Keyword Research`: runs every Monday, plus manually via Actions. It uses **only Brave by default**, respects small request caps, and commits the project's data/reports when changed.
- To collect new suggestions automatically, add `BRAVE_API_KEY` to GitHub repository Actions secrets and confirm the provider's terms, free quota and billing settings.
- Without that key, the workflow is still safe to run but **only seeds are registered**; it does not pretend that live research happened.
- Unofficial endpoints are *manual opt-in only*, never silently enabled by the scheduled workflow.
- GitHub may pause scheduled workflows after extended inactivity in public repositories.

## Guardrails

Never commit secrets or private customer data: this is a **public repository**. Provider availability, terms, geographic support and free quotas can change. The system logs missing provider access as a notice and does not automatically circumvent restrictions. Do not use its rankings as proof of Google demand. Review SERPs and business relevance before writing or publishing content.

## Architecture and roadmap

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the schema, limitations and the next milestones (real SERP analysis, optional volume enrichment, trend evidence, semantic clustering, Search Console feedback, dashboard).

**License:** not assigned yet. Public visibility alone is not an open-source license; repository owner should choose a license deliberately.
