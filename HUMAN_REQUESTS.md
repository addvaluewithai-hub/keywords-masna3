# HUMAN_REQUESTS.md — Agent → Human Assistance Queue

> **Source of truth:** this file. It is maintained by the reasoning agent as GitHub memory, not a human-operated dashboard or an automatic notification service. **Zero-budget policy:** never request or purchase paid subscriptions without separate explicit approval.

## Requests at a glance

| ID | Project | What I need | Urgency | Expected impact | Status |
|---|---|---|---|---|---|
| `HR-QSERVE-001` | qserve | Confirm the real early-access conversion destination | **SOON** | **CRITICAL** | OPEN |
| `HR-QSERVE-002` | qserve | Optional official Brave Autosuggest API access | **WHEN CONVENIENT** | **HIGH** | OPEN |
| `HR-QSERVE-003` | qserve | Optional no-cost keyword volume export | **WHEN CONVENIENT** | **HIGH** | OPEN |
| `HR-QSERVE-004` | qserve | Google Search Console access after launch | **LATER** | **HIGH** | WAITING PREREQUISITE |

## Priority scale

**Urgency:** `NOW` = immediate blocker; `SOON` = needed for next significant milestone; `WHEN CONVENIENT` = optional improvement; `LATER` = wait for a prerequisite. **Impact:** `CRITICAL` = central project outcome, `HIGH` = major expected quality/operational benefit, `MEDIUM` = useful, `LOW` = nice to have. These are qualitative judgments, not measured uplift.

**Valid statuses:** `OPEN`, `WAITING PREREQUISITE`, `IN PROGRESS`, `FULFILLED`, `DECLINED`, `CANCELLED`. Requests must retain their ID; completed and declined requests stay archived here for history.

## Current requests

### HR-QSERVE-001 — Confirm the real early-access conversion destination

- **Project / requested by:** qserve / reasoning agent
- **Urgency:** SOON · **Impact:** CRITICAL · **Status:** OPEN
- **Estimated human effort:** 10–20 min · **Allowed cost:** $0
- **What it affects:** Converting traffic into leads, not keyword discovery
- **Request:** Confirm QServe's actual public landing/demo URL and a working way for restaurant owners to request early access. If lead capture is not implemented, simply confirm that so we can plan it honestly.
- **Why I'm asking:** QServe is documented as a frontend prototype without production signup. Organic visits cannot reliably turn into leads without a truthful, working destination.
- **Acceptance criteria / desired input:** Public URL and CTA destination/status, or a decision to build lead capture.
- **Safe method:** Public link or status is fine in chat. Do not commit real prospect details to the public repo.
- **Fallback without human help:** Continue keyword research and content planning with 'View Demo' messaging; do not pretend a signup funnel exists.
- **Close only when:** Agent verifies the destination is working, updates QServe project status, and records evidence. Until then, OPEN.
- **When to surface it:** Before publishing acquisition pages or measuring lead conversion.
- **Created / last reviewed:** 2026-10-10 / 2026-10-10
- **Completion evidence:** Not provided yet.

### HR-QSERVE-002 — Optional official Brave Autosuggest API access

- **Project / requested by:** qserve / reasoning agent
- **Urgency:** WHEN CONVENIENT · **Impact:** HIGH · **Status:** OPEN
- **Estimated human effort:** 5–15 min · **Allowed cost:** $0 ONLY
- **What it affects:** Official provider diversity only; alternatives exist
- **Request:** Only if a truly no-cost/free-credit option is available on acceptable terms, configure a BRAVE_API_KEY in the repository's GitHub Actions secrets. Do not buy a plan or provide a payment card just for this.
- **Why I'm asking:** The official Brave suggestion adapter is implemented, but cannot run without a key. Google Autocomplete has produced useful keywords, but is an unofficial interface.
- **Acceptance criteria / desired input:** Confirm in conversation that the GitHub Actions secret is configured, or that it isn't obtainable for free.
- **Safe method:** GitHub Settings → Secrets and variables → Actions → New repository secret. Never paste or commit the key; this repo is public.
- **Fallback without human help:** Keep Brave marked blocked; use currently permitted small, explicit unofficial source tests only.
- **Close only when:** Agent verifies the provider actually runs successfully, or marks DECLINED if not free.
- **When to surface it:** When convenient; not a blocker to research.
- **Created / last reviewed:** 2026-10-10 / 2026-10-10
- **Completion evidence:** Not provided yet.

### HR-QSERVE-003 — Optional no-cost keyword volume export

- **Project / requested by:** qserve / reasoning agent
- **Urgency:** WHEN CONVENIENT · **Impact:** HIGH · **Status:** OPEN
- **Estimated human effort:** 15–30 min · **Allowed cost:** $0 ONLY
- **What it affects:** Measured search demand comparison; not core research
- **Request:** If you already have free access to Bing Webmaster keyword research, Google Ads Keyword Planner, or an existing legitimate Ahrefs/Semrush export, share a relevant CSV/XLSX for QR/digital restaurant menus in the US (English), Mexico (Spanish), or Brazil (Portuguese). Don't purchase anything.
- **Why I'm asking:** Autocomplete confirms suggestions but provides no verified Google monthly volume, CPC or organic difficulty. A source-labelled data export can improve opportunity ranking.
- **Acceptance criteria / desired input:** Dated export with provider, country, language, whether volume is ranges/estimates, and redacted private details.
- **Safe method:** Share a redacted file via chat or supported private connector. Only non-sensitive data and provenance can enter this public repo.
- **Fallback without human help:** Leave search volume/difficulty unknown and prioritize on semantic relevance, source observations and search results.
- **Close only when:** Agent validates source, date and fields, stores safe findings, and marks FULFILLED with a reference.
- **When to surface it:** Before investing heavily in multilingual content; otherwise optional.
- **Created / last reviewed:** 2026-10-10 / 2026-10-10
- **Completion evidence:** Not provided yet.

### HR-QSERVE-004 — Google Search Console access after launch

- **Project / requested by:** qserve / reasoning agent
- **Urgency:** LATER · **Impact:** HIGH · **Status:** WAITING PREREQUISITE
- **Estimated human effort:** 20–40 min · **Allowed cost:** $0
- **What it affects:** Learning from organic performance after launch
- **Request:** Once pages are live, verify the site property in Search Console, then provide appropriately authorized read-only access or a redacted Search Console performance export.
- **Why I'm asking:** Real clicks, impressions and search queries let the reasoning agent refine research based on outcomes. This data will not exist before the pages launch and index.
- **Acceptance criteria / desired input:** Verified site property/public site URL and a dated queries/pages report when data becomes available.
- **Safe method:** Use read-only access through an available connector or share a redacted export; never paste OAuth tokens into GitHub or chat.
- **Fallback without human help:** Keep researching and preparing content with existing public evidence; do not manufacture impressions.
- **Close only when:** Agent confirms real first-party performance data is available and then records completion evidence.
- **When to surface it:** After pages are published and Search Console has collected data.
- **Prerequisite:** QServe SEO pages are public, indexable and associated with an owned website.
- **Created / last reviewed:** 2026-10-10 / 2026-10-10
- **Completion evidence:** Not provided yet.

## Mandatory agent behavior

1. **Read this file at the start of every research session.** Match existing request IDs before asking the human the same question again.
2. **Log first; ask only when useful.** Add a request when human access, judgment, a file, an external account connection or an authorized key would materially help. Do not interrupt the user for routine research steps.
3. **Always include** a unique ID, project, exact human action, rationale, urgency, impact, status, expected cost/effort, fallback, and precise completion evidence.
4. **Separate 'blocking' from 'nice to have'.** A high-impact request can be low-urgency. Continue independent tasks while requests remain open.
5. **No secrets in GitHub.** The repo is public. Record only 'configured/verified' with no API key or OAuth token. Human can configure Secrets or approve a connector in an authorized interface.
6. **No paid pressure.** For this project budget is $0. A paid plan, card, subscription or bill requires new explicit human permission. Respect decisions to decline.
7. **Never claim a human provided something without evidence.** Update the status only after checking a linked file/result, accessible service, or unambiguous human response. Record completion date and safe evidence link (never sensitive IDs).
8. **This ledger does not send notifications by itself.** Summarize the highest-priority relevant open requests in an active conversation. No background monitoring is implied.
9. **Don't overwrite historical decisions.** Edit this file on GitHub to add or change requests and preserve original IDs, decisions and dates. Reassess urgencies when project milestones change.

## How the human can respond without opening GitHub

Just answer the agent in the conversation: e.g. **“HR-QSERVE-002: no free key available”** or **“HR-QSERVE-001: early-access form is now live at [public URL]”**. The connected agent verifies as appropriate and updates this ledger. For credentials, the human configures a GitHub Actions Secret or supported connector—not a chat message containing the secret.
