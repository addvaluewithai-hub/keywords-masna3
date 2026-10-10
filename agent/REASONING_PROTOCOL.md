# Agent Reasoning Protocol (model-first)

**Cognitive core:** the connected ChatGPT / reasoning Agent in an active session. **GitHub** is durable project context, provenance, execution orchestration, queued jobs, and status—not the semantic decision-maker.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| Reasoning agent | Understand product, intent, relevance, clustering, page strategy, competitor interpretation, business tradeoffs and what to research next. |
| GitHub repo | Persist snapshots, decisions, task requests/results, statuses, source provenance and auditable rationale. |
| Actions / scripts | Fetch suggestions within authorized limits, deduplicate, normalize, preserve history, validate formats, export reports and run tests. |
| Source APIs | Supply evidence with dates and provenance; they cannot determine truthfulness of product fit on their own. |

## Session playbook

1. Read `agent/manifest.json`, `AGENTS.md`, `HUMAN_REQUESTS.md`, project config, latest raw keyword registry, any prior `intelligence/status.json`, and actual product repo/README.
2. Identify new/unreviewed terms by comparing current registry with last review snapshot.
3. Personally assess meaning, language and local market, search intent, product fit, false positives, variants, prerequisites and provisional clusters. Use current SERPs when needed, with source URLs and dates.
4. Write **agent-authored** analysis to `projects/<slug>/intelligence/semantic-review-YYYY-MM-DD.json`; reason for each keyword, distinguish hypothesis from evidence, and leave missing volume/difficulty null.
5. Update `projects/<slug>/intelligence/status.json` with pointers, next actions, and actual review coverage. Existing mechanical `brain/next_actions.json` is a query **frontier**, not the authoritative content strategy.
6. Delegate only mechanizable operations using immutable `jobs/requests/<id>.json`. Read matching `jobs/results/<id>.json` before calling execution complete.
7. Never let automated scores silently overwrite semantic judgements. Explain conflicts in a new versioned review.
8. If something needs human input, write/update `HUMAN_REQUESTS.md` *before* interrupting the owner. Give each request an ID, project, urgency, expected impact, cost, effort, fallback and verification requirement. Request only relevant high-value help, and continue other research when possible. This public file must never include secret values.
9. Before choosing any keyword to target, recheck current product functionality, and perform appropriate SERP review; a keyword being present in autocomplete does not prove market demand.

## Human collaboration as an exception, not an operating dependency

The reasoning agent owns the human assistance ledger at `HUMAN_REQUESTS.md`; routine discovery and strategic analysis remain agent-led. The agent checks outstanding requests before repeating them, records fulfilled or declined outcomes, and explains consequences of missing inputs without inventing data. Impact and urgency are separate qualitative judgments. No paid product is assumed available: this project's budget is $0 unless the human expressly changes it. The ledger does not notify people automatically; the agent raises the relevant item during an active conversation.

## Interaction limits

This agent does not remain alive after the chat ends. GitHub Actions can run scheduled deterministic jobs, but **cannot invoke this chat's reasoning model automatically** without a separately configured agent runtime/API. On a future chat or agent invocation, resume by reading repo state. Don't promise asynchronous thinking or ongoing personal monitoring.

## What success means

Not the maximum number of keywords. Success means an **evidence-based, actionable, explainable, correctly scoped** backlog for each niche. Preserve rejected keywords as negative knowledge. Distinguish mechanical task priorities from model-authored decisions.
