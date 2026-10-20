# Product Finder

> **Status:** Rebuild specification · **Phase:** MVP planning · **Cost target:** €0/month

Product Finder is an RSS-first marketplace monitoring application. It periodically ingests listings from HardverApró, preserves their original metadata, identifies new listings matching configurable watch rules, and sends one email per newly matched listing. Later phases add full-page extraction, structured hardware-specification enrichment, a FastAPI API, and a React/TypeScript listing browser.

The initial use case is finding an **NVIDIA RTX 4070 Ti SUPER** at an attractive price, but product names, RSS feeds, and matching rules must be configurable rather than hardcoded.

## 1. Goals

- Monitor one or more user-supplied HardverApró RSS URLs approximately once per hour.
- Store all available RSS entry fields, the raw feed-entry representation, provenance, and discovery timestamps in hosted PostgreSQL.
- Identify listings using stable source-specific IDs where available; otherwise use normalized canonical URLs with a documented fallback.
- Support case-insensitive include/exclude keyword rules and optional minimum/maximum price thresholds in HUF.
- Send an email for each **new listing/watch-rule match**, at most once under normal retries; record delivery attempts and errors.
- Track price changes and feed appearances without overwriting historical evidence.
- Distinguish absence from an RSS feed from actual listing archival.
- Run the same ingestion command locally and in GitHub Actions.
- Design source adapters so other marketplaces can be added later.

### Non-goals for MVP

- No page scraping, browser automation, Scrapy, Ollama, public API, or frontend.
- No proof that a listing is sold or archived based solely on feed disappearance.
- No multi-user authentication, instant push delivery, or guaranteed exact-hour scheduling.
- No automatic purchasing, bidding, or messaging sellers.

## 2. Proposed stack

| Concern | MVP | Later |
|---|---|---|
| Language | Current supported Python 3.x (pin version in `.python-version`) | Same |
| Package management | `uv` / `pyproject.toml` / committed lockfile | Same |
| HTTP / RSS | `httpx`, `feedparser` (verify feed behavior) | Per-source adapters |
| Models / config | Pydantic v2, `pydantic-settings` | Same |
| Persistence | PostgreSQL, SQLAlchemy 2.x, Alembic, `psycopg` | Same |
| Email | Standard library `smtplib` + `email.message` | Provider adapter if needed |
| Scheduling | GitHub Actions cron + manual dispatch | Worker/scheduler if needed |
| Quality | Ruff, pytest, type hints, CI | Same |
| API | Not in MVP | FastAPI |
| Frontend | Not in MVP | React + TypeScript + Vite |
| Enrichment | Not in MVP | Ollama + validated structured output |
| Containers | Optional for local PostgreSQL | Useful for API/worker deployment |

**Database choice:** Start with Neon hosted PostgreSQL if its free plan remains suitable. Keep database access standard PostgreSQL so switching providers does not require rewriting application logic. Use environment variables for credentials, never committed secrets.

## 3. User configuration

MVP configuration is file-based (e.g. `config/watches.yaml`), validated with Pydantic. A watch has a stable identifier, name, enabled flag, RSS feed reference, include/exclude terms, optional HUF price bounds, and destination email reference. Avoid putting credentials in this file.

Example (illustrative; URL must be replaced with a real HardverApró RSS feed):

```yaml
feeds:
  - id: hardverapro-gpus
    source: hardverapro
    url: https://example.invalid/replace-with-real-rss-url
watches:
  - id: rtx-4070-ti-super
    name: RTX 4070 Ti SUPER
    enabled: true
    feed_ids: [hardverapro-gpus]
    include_all: ["4070", "super"]
    include_any: ["ti", "ti super"]
    exclude_any: ["wanted", "keresek", "hibás"]
    min_price_huf: null
    max_price_huf: null
```

**Matching contract:** Normalize Unicode/case and whitespace. Apply `include_all` (AND), `include_any` (OR), and `exclude_any` (NOT) to a documented searchable text composed of title plus available summary. If a price threshold exists but price cannot be parsed confidently, mark the match `indeterminate` and do not send a price-qualified alert until it can be resolved. These are textual filters, not guaranteed product identification: `4070` + `super` may still yield false positives. Log match reasons for troubleshooting.

A listing may match multiple watches. Deduplicate by `(listing_id, watch_id)`; whether to consolidate multiple matching watches into one email is a later enhancement.

## 4. Ingestion contract

1. Load validated configuration and connect to PostgreSQL.
2. Fetch each RSS feed with a timeout, descriptive User-Agent, conditional HTTP headers (`ETag`, `Last-Modified`) when supported, and bounded retries/backoff.
3. Validate HTTP status and parse the feed. A `304 Not Modified` is a successful no-change result, **not** an empty feed.
4. Save a `feed_run` record with timing, HTTP status, parse status, item count, and error details.
5. Convert each item into a source-neutral `ListingCandidate`, preserving original source fields in JSONB and optionally bounded raw entry content.
6. Upsert listings using source-specific identity; update `last_seen_at` and record feed membership observations.
7. Append price history only when the normalized price changes. Preserve original price text and currency.
8. Evaluate enabled watches and create unique notification intents for newly observed matches.
9. Send pending emails and record attempts, delivery state, and failure reasons.
10. Update absence counters **only if the feed run is eligible for absence inference** (see lifecycle section).
11. Emit structured logs and a summary of fetched, new, updated, matched, notified, and failed items.

A run must be idempotent: replaying the same feed must not create duplicate listings, price-history entries, or notification intents.

### Feed completeness caveat

A successful RSS response is **not automatically a complete catalog**. A feed with a fixed number of newest items can omit older active listings. Therefore, missing from RSS must never by itself imply inactive. Eligibility for absence counting should require an explicit feed-specific policy, not just HTTP 200. For a rolling/latest-items feed, track `last_observed_in_feed_at` but do not automatically increase an archival confidence score from absence alone.

## 5. Listing lifecycle and archival verification

Keep **two separate dimensions**:

- **Feed observation:** `seen_this_run`, `last_seen_at`, `consecutive_eligible_misses` per `(feed_id, listing_id)`.
- **Verified listing status:** `unknown`, `active`, `inactive`, `verification_pending`, `verification_failed`, with status evidence and timestamps. `inactive` must be supported by an explicit site status or sufficiently reliable page evidence, not feed absence.

Suggested state flow for feeds whose completeness policy allows absence tracking:

```text
Observed in eligible feed run
  -> missed 1 eligible run
  -> missed 2 eligible runs
  -> verification_pending
       -> page explicitly active   -> active (reset/retain feed-miss evidence)
       -> page explicitly inactive -> inactive
       -> timeout/403/ambiguous   -> verification_failed / unknown; retry later
```

For **rolling RSS feeds**, bypass the automatic `missed 1 / missed 2` inference; disappearance is expected and is not evidence of archival. Verification candidates can instead be selected by age, explicit feed signals, or a separately defined periodic sampling policy.

Page verification is **post-MVP** and must be rate-limited and compliant with the source's published rules. A 404 can indicate removal but should be stored as a specific verification signal; 403, CAPTCHA, redirects, and temporary failures are not proof of inactivity. An explicit sold/archived badge is stronger evidence. Preserve `status_reason`, `verification_method`, `verified_at`, and optionally response fingerprint. Reactivation must be possible if later evidence shows an active listing.

## 6. Proposed data model

| Entity | Important fields | Constraints / notes |
|---|---|---|
| `sources` | id, slug, name | Unique slug |
| `feeds` | id, source_id, url, enabled, etag, last_modified, completeness_policy | Unique normalized feed identity |
| `feed_runs` | id, feed_id, started_at, finished_at, outcome, http_status, item_count, error | Append-only run history; retention policy needed |
| `listings` | id, source_id, external_id, canonical_url, title, summary, seller, location, raw_payload JSONB, first_seen_at, last_seen_at, verified_status, status_reason | Unique `(source_id, external_id)` when known; canonical URL fallback |
| `feed_listings` | feed_id, listing_id, first_seen_at, last_seen_at, consecutive_eligible_misses | Unique `(feed_id, listing_id)` |
| `listing_observations` | id, listing_id, feed_run_id, observed_at, payload_hash | Optional bounded history; avoid unbounded duplicate payloads |
| `price_history` | id, listing_id, observed_at, price_amount, currency, original_price_text | Store changes, not every unchanged poll |
| `watches` | id, name, enabled, rule_json, created_at | Configuration synchronized from YAML |
| `watch_feeds` | watch_id, feed_id | Many-to-many |
| `notification_outbox` | id, listing_id, watch_id, created_at, state, sent_at, last_error | Unique `(listing_id, watch_id)` for new-match alerts |
| `notification_attempts` | id, notification_id, attempted_at, result, error | Auditable retries |
| `listing_verifications` | id, listing_id, checked_at, method, evidence, result | Post-MVP |

Store timestamps in UTC. Use integer HUF amounts rather than floating-point currency values. Apply indexes to external IDs, canonical URLs, watch matches, and recent listing timestamps. Use migrations from day one.

**Important email limitation:** SMTP plus a database cannot guarantee exactly-once delivery. A process can send successfully and crash before recording `sent_at`. Use a durable outbox, retry limits, and deduplication keys to achieve practical at-least-once delivery with rare duplicate risk. Never mark an email sent before SMTP success.

## 7. Deployment and operations

- `ingest` is a CLI command that works both locally and in CI.
- GitHub Actions runs hourly at an off-peak minute, e.g. `17 * * * *`, and supports `workflow_dispatch` for manual runs.
- Use `concurrency` to avoid overlapping production ingestion runs. Database uniqueness constraints remain mandatory.
- Store `DATABASE_URL`, SMTP username/app password, sender, and recipient secrets in GitHub Actions secrets; use local `.env` ignored by Git.
- Run Ruff and pytest on pull requests separately from the scheduled ingestion workflow.
- Log failures clearly; a failed feed must not trigger archival transitions.
- GitHub Actions scheduled jobs may be delayed or skipped; an hourly cron is **best-effort**, not a delivery SLA. Public-repository schedules can be disabled after prolonged inactivity.
- Track database size and add a retention policy for old `feed_runs` and duplicate raw observations before approaching free-tier quotas.
- Keep a documented PostgreSQL export/restore procedure; free plans may not include managed backups.

### Email transport

Start with Gmail SMTP using TLS and an app password, assuming the sending Google account supports app passwords. Secrets must never appear in logs. Use `EmailMessage`, include listing title, price, direct URL, matched watch, and observed time. Treat rate limits and SMTP failures as retryable where appropriate. Do not add `yagmail` unless it solves a demonstrated need.

### Docker

Docker is **optional in MVP**. A small `compose.yaml` for local PostgreSQL is helpful for repeatable integration tests and migrations, while GitHub Actions can run Python directly via `uv`. Containerize the API and enrichment worker later if deployment warrants it.

## 8. Repository layout (target)

```text
product-finder/
├── README.md
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example
├── config/
│   └── watches.example.yaml
├── src/product_finder/
│   ├── cli.py
│   ├── settings.py
│   ├── domain/
│   │   ├── models.py
│   │   └── matching.py
│   ├── sources/
│   │   ├── base.py
│   │   └── hardverapro.py
│   ├── ingestion/
│   │   ├── service.py
│   │   └── lifecycle.py
│   ├── persistence/
│   │   ├── models.py
│   │   └── repositories.py
│   └── notifications/
│       ├── email.py
│       └── outbox.py
├── migrations/
├── tests/
│   ├── fixtures/
│   ├── unit/
│   └── integration/
├── .github/workflows/
│   ├── ci.yml
│   └── ingest.yml
└── frontend/                 # post-MVP
```

Avoid creating empty packages solely for speculative features. Add directories when implementation starts.

## 9. MVP acceptance criteria

- [ ] Real HardverApró RSS sample inspected and parser fixtures saved.
- [ ] Multiple feeds and watches load from validated configuration.
- [ ] One CLI command fetches feeds and persists entries to PostgreSQL.
- [ ] Same listing across repeated runs is represented once.
- [ ] Same listing in multiple feeds is represented once when stable identity is available.
- [ ] Raw source fields are retained and normalized fields are queryable.
- [ ] New matching listing creates one notification intent.
- [ ] A successful email records its delivery; failed email remains retryable.
- [ ] Re-running identical input does not generate another notification intent.
- [ ] Price changes are stored as history without duplicating unchanged prices.
- [ ] Invalid/failed/304 feed responses cannot mark listings inactive.
- [ ] Feed absence alone cannot set `verified_status=inactive`.
- [ ] CI passes Ruff, pytest, and migration/integration checks.
- [ ] GitHub Actions supports hourly schedule and manual trigger.
- [ ] Secrets are externalized; setup instructions permit local reproduction.

## 10. Roadmap

### Phase 0 — Feed discovery and feasibility

- Obtain real HardverApró RSS examples for GPU searches.
- Inspect GUID stability, publication dates, available fields, price formatting, feed size, and update behavior.
- Check published access requirements and feed usage limits.
- Test hosted PostgreSQL connection from GitHub Actions.

### Phase 1 — Working MVP

- Create Python project and quality tooling.
- Implement source adapter and RSS parsing.
- Implement database schema and Alembic migrations.
- Implement watch configuration and deterministic matching.
- Implement transactional notification outbox and Gmail SMTP.
- Deploy scheduled ingestion to GitHub Actions.
- Test replay, retry, malformed feed, price-change, and duplicate cases.

### Phase 2 — Lifecycle and full-page verification

- Add bounded, rate-limited page fetching where permitted.
- Parse listing-specific status indicators and record evidence.
- Implement progressive verification queue and recovery/reactivation logic.
- Add price-drop alerts as a separate notification type.

### Phase 3 — Catalog and AI enrichment

- Broaden ingestion to GPU and laptop feeds/categories.
- Fetch detailed listing pages where allowed and store original descriptions.
- Extract CPU, GPU, RAM, storage, display, and other hardware attributes via Ollama.
- Validate with Pydantic and preserve model version, raw output, confidence/validation failures, and reprocessing status.
- Support re-enrichment without rescraping.

### Phase 4 — API and frontend

- FastAPI paginated/filterable listing API.
- React/TypeScript/Vite grid view: search, filters, sorting, source, price, freshness, status.
- Listing detail view: original description, parsed specifications, seller/source metadata, price history, direct source link.
- Decide authentication and hosting only when a public deployment is in scope.

### Phase 5 — Multiple marketplaces

- Add new adapters behind the same normalized listing contract.
- Define cross-source identity/deduplication policy.
- Add source-specific rate limits, field mappings, and health metrics.

## 11. Testing strategy

- **Unit:** text normalization, AND/OR/exclusion rules, HUF price parsing, source identity, lifecycle state transitions.
- **Fixture-based:** saved RSS XML for normal, malformed, empty, reordered, and changed entries.
- **Integration:** PostgreSQL schema, unique constraints, idempotent upserts, outbox transactions, concurrent runs.
- **Email:** fake SMTP transport; no real messages in CI.
- **Failure cases:** timeout, 403/429, 304, invalid XML, partial response, DB failure, SMTP timeout, crash after SMTP acceptance.
- **End-to-end smoke:** one local ingestion using a fixture feed and disposable PostgreSQL database.

## 12. Decisions still to validate

1. **Real feed contract:** HardverApró RSS URLs, field coverage, stable identifiers, and feed window size must be tested against actual samples.
2. **Provider:** Neon is the initial preference; confirm account-specific free limits, networking, and inactivity behavior before committing.
3. **Watch configuration:** Decide whether watch YAML lives in the repository or is supplied as a private Actions secret; public config may reveal shopping preferences.
4. **Price matching:** Determine what to do when price is absent, negotiable, or ambiguously formatted.
5. **Initial run:** Default to *baseline mode* (save existing listings without emailing for all of them), with an explicit option to alert on initial matches.
6. **Email recipients:** MVP assumes one recipient, configured via secret; multi-recipient support is later.
7. **Feed absence:** Establish per-feed completeness policy; rolling feeds do not support reliable archival inference.
8. **Storage budget:** Define raw-payload size limits, run-log retention, and backup cadence to stay within free quotas.
9. **Notification semantics:** New-match-only for MVP; if an old listing begins matching after a price edit or watch-rule change, define whether that is a new alert-worthy event.
10. **Frontend hosting and access:** Deferred until Phase 4.

## 13. Development principles

- Prefer RSS and published APIs over brittle scraping.
- Keep source-specific parsing out of domain and persistence code.
- Preserve raw evidence; normalized and enriched data are derived.
- Treat missing information as unknown, not false.
- Make operations idempotent and errors observable.
- Use explicit migrations and tests instead of hand-editing production tables.
- Keep the MVP small; design interfaces for future growth without implementing unused abstractions.
- Prefer free, replaceable services and avoid vendor-specific database APIs.
