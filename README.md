# ListingLens

> **Status:** In development · **Current milestone:** FastAPI foundation and RSS ingestion · **Budget:** €0/month

ListingLens is an RSS-first marketplace monitor. It ingests HardverApró listings, preserves original metadata, detects new listings matching configurable watches, and sends email alerts. Future phases introduce listing verification, hardware-specification enrichment with Ollama, and a React listing browser. The initial target is an RTX 4070 Ti SUPER, but watches and sources are not hardcoded.

## 1. Goals and scope

**MVP requirements**

- Monitor one or more user-supplied RSS feeds approximately hourly, locally or via GitHub Actions.
- Normalize listings, retain raw feed data, and upsert without duplicates.
- Match configurable case-insensitive include/exclude keywords and optional HUF price bounds.
- Send one notification intent per newly matched `(listing, watch)` pair, with durable retry records.
- Preserve price changes, observation timestamps, and feed-specific appearances.
- Never infer that a listing was sold or archived solely because it disappeared from a rolling RSS feed.
- Build a small FastAPI backend now, initially with health and read-only listing endpoints.
- Keep source-specific behavior behind adapters so other marketplaces can be added.

**Out of scope for the initial release:** full-page scraping, Ollama enrichment, React frontend, multi-user authentication, purchasing, and guaranteed exact-hour delivery. API scaffolding is in scope; a publicly deployed API is not.

## 2. Technology decisions

| Layer | Choice | Reason |
|---|---|---|
| Python | Modern supported Python 3.x, pinned in `.python-version` | Consistent environments |
| Dependencies | `uv`, `pyproject.toml`, `uv.lock` | Fast reproducible installs |
| API | FastAPI, Uvicorn | Typed HTTP interface |
| Validation | Pydantic v2, `pydantic-settings` | Separate input/output contracts and environment settings |
| Database | PostgreSQL locally in Docker Compose; Neon later | Same SQL dialect in development and production |
| ORM and migrations | SQLAlchemy 2.x, Alembic, `psycopg` | Typed persistence and schema evolution |
| RSS | `httpx`, `feedparser` | HTTP retrieval and feed parsing |
| CLI | Typer | Reuse ingestion independently of FastAPI |
| Email | `smtplib`, `email.message` | No unnecessary dependency |
| Quality | Ruff, pytest, type hints | Practical engineering rigor |
| Scheduling | GitHub Actions cron and manual dispatch | Free, simple scheduled execution |
| Later | Ollama, React + TypeScript + Vite | Enrichment and browsing |

Use **synchronous SQLAlchemy sessions initially** for simplicity. Database session handling must not depend on FastAPI so CLI ingestion can reuse it. Never commit database credentials; local `.env` and CI secrets provide them.

## 3. Target repository structure

The comments describe the purpose of each file or directory. This is a **target layout**, not a claim that every file already exists. Create files as the corresponding feature is implemented.

```text
ListingLens/
├── README.md                           # Project specification, setup, and roadmap
├── pyproject.toml                      # Python dependencies and tool configuration
├── uv.lock                             # Locked Python dependency versions
├── .python-version                     # Local Python version pin
├── .env.example                        # Documented environment variable names, no secrets
├── .gitignore                          # Ignore local secrets, caches, databases, and exports
├── compose.yaml                        # Local PostgreSQL development service
├── Dockerfile                          # Optional future container image for API/worker
├── alembic.ini                         # Alembic migration configuration
├── alembic/                            # Version-controlled database schema migrations
│   ├── env.py                          # Connect migrations to settings and SQLAlchemy metadata
│   └── versions/                       # Individual database migration scripts
├── config/
│   └── watches.example.yaml            # Example RSS feed and watch definitions
├── src/
│   └── listinglens/
│       ├── __init__.py                  # Python package marker
│       ├── main.py                      # FastAPI app creation and router registration
│       ├── cli.py                       # Commands for local and scheduled ingestion
│       ├── core/
│       │   ├── __init__.py              # Core package marker
│       │   └── config.py               # Environment-based application settings
│       ├── db/
│       │   ├── __init__.py              # Database package marker
│       │   ├── base.py                  # Declarative Base and model metadata imports
│       │   └── session.py               # Engine, session factory, and session lifecycle
│       ├── models/
│       │   ├── __init__.py              # Register SQLAlchemy models for Alembic
│       │   ├── source.py                # Marketplace/source table
│       │   ├── feed.py                  # Feed definitions and HTTP cache metadata
│       │   ├── feed_run.py              # Fetch attempts and processing outcomes
│       │   ├── listing.py               # Canonical listings and raw source payload
│       │   ├── feed_listing.py          # Per-feed listing appearances and missing counts
│       │   ├── price_history.py         # Recorded listing price changes
│       │   ├── watch.py                 # Watch rules and feed associations
│       │   └── notification.py          # Outbox records and delivery attempts
│       ├── schemas/
│       │   ├── __init__.py              # Pydantic schema package marker
│       │   ├── listing.py               # Listing API responses and filtering inputs
│       │   ├── feed.py                  # Feed validation and API representations
│       │   ├── watch.py                 # Validated watch-rule configuration
│       │   └── ingestion.py             # Source-neutral parsed listing candidate
│       ├── routers/
│       │   ├── __init__.py              # FastAPI router package marker
│       │   ├── health.py                # Health and readiness endpoints
│       │   └── listings.py              # Read-only listing and detail endpoints
│       ├── services/
│       │   ├── __init__.py              # Business service package marker
│       │   ├── ingestion.py             # Orchestrate feed fetch, parse, and persistence
│       │   ├── listings.py              # Listing queries and update operations
│       │   ├── matching.py              # Evaluate watch keywords and price rules
│       │   ├── lifecycle.py             # Feed observations and verification eligibility
│       │   └── notifications.py         # Create and dispatch notification intents
│       ├── sources/
│       │   ├── __init__.py              # Marketplace adapter package marker
│       │   ├── base.py                  # Common adapter protocol and normalized output
│       │   └── hardverapro.py           # HardverApró RSS retrieval and field mapping
│       └── notifications/
│           ├── __init__.py              # Notification transport package marker
│           └── smtp.py                  # Gmail SMTP transport implementation
├── tests/
│   ├── conftest.py                      # Shared fixtures and test database setup
│   ├── fixtures/
│   │   └── hardverapro.xml              # Saved RSS response for offline tests
│   ├── unit/                            # Parser, matching, and lifecycle unit tests
│   └── integration/                     # PostgreSQL, API, and ingestion integration tests
├── .github/
│   └── workflows/
│       ├── ci.yml                       # Ruff and pytest on pushes/PRs
│       └── ingest.yml                   # Hourly and manually triggered feed ingestion
└── frontend/                           # React/Vite application (future phase)
```

**Conventions:** `models/` contains SQLAlchemy persistence models; `schemas/` contains Pydantic contracts. `routers/` only handles HTTP requests and responses; `services/` owns business operations. `sources/` understands marketplace-specific feeds, not database sessions. `notifications/` implements delivery transports; the notification service decides *what* to send. For the MVP, simple SQLAlchemy queries can live in services; introduce a `repositories/` layer only if persistence logic becomes hard to maintain. Avoid circular imports and do not create empty modules solely to match this tree.

## 4. Runtime boundaries

```text
GitHub Actions / local CLI
           |
           v
     ingestion service <---- source adapter (HardverApró RSS)
           |
           v
    PostgreSQL database
           |
       +---+----------------+
       |                    |
  matching service     listing service <--- FastAPI routers
       |
 notification service ---> SMTP transport

Future: verification worker / Ollama enrichment / React frontend
```

- FastAPI must **not** need to be running for scheduled ingestion.
- Both API and CLI import the same settings, SQLAlchemy models, and services.
- Source adapters return validated, source-neutral candidates and preserve the original feed entry.
- Services manage transactions; keep HTTP endpoints thin.
- Do not put email sending inside a database transaction.

## 5. Configuration and watch matching

Store non-secret feed/watch definitions in `config/watches.yaml` (or a private configuration source); load and validate with Pydantic. Example:

```yaml
feeds:
  - id: hardverapro-gpus
    source: hardverapro
    url: https://example.invalid/replace-with-real-feed
watches:
  - id: rtx-4070-ti-super
    name: RTX 4070 Ti SUPER
    enabled: true
    feed_ids: [hardverapro-gpus]
    include_all: ["4070", "super"]
    include_any: ["ti", "ti super"]
    exclude_any: ["keresek", "hibás"]
    min_price_huf: null
    max_price_huf: null
```

`include_all` uses AND, `include_any` uses OR, and `exclude_any` uses NOT. Match normalized Unicode/case/whitespace against title plus available summary. If a required price bound cannot be evaluated, return `indeterminate`, not a positive match. Store match reasons. Deduplicate notification intents by `(listing_id, watch_id)` for the new-match alert type. First ingestion defaults to **baseline mode**: existing entries are saved without a flood of emails; make initial alerts explicitly opt-in.

## 6. Ingestion contract

1. Load settings and validated watch configuration.
2. Fetch feeds with bounded timeouts/retries, descriptive User-Agent, and `ETag`/`Last-Modified` when supported.
3. Record feed-run status and parse errors; treat `304 Not Modified` as unchanged, **not** an empty feed.
4. Parse each item into a source-neutral Pydantic candidate, retaining all available raw fields.
5. Upsert by `(source_id, external_id)` where stable, otherwise by a documented canonical URL fallback.
6. Update first/last seen timestamps and feed membership; append price history **only on change**.
7. Evaluate watches and persist unique notification intents in a durable outbox.
8. Dispatch pending notifications, recording attempts, success, and errors.
9. Apply absence counters only when a feed-specific completeness policy permits them.
10. Log counts for fetched, created, updated, matched, notified, and failed records.

The same input replayed twice must not duplicate listings, unchanged prices, or notification intents. A failed or malformed fetch must not affect listing archival status. SMTP cannot guarantee exactly-once delivery after a crash; an outbox reduces duplicates but rare repeats remain possible.

## 7. Data model (proposed)

| Table | Purpose / key fields |
|---|---|
| `sources` | Marketplace identity; unique slug |
| `feeds` | RSS URLs, source, enabled flag, ETag, last-modified, completeness policy |
| `feed_runs` | Fetch/parse results, timestamps, HTTP status, item count, errors |
| `listings` | Source identity, URL, title, price, currency, raw JSONB, timestamps, verified status |
| `feed_listings` | Unique `(feed_id, listing_id)`, first/last observation, eligible miss count |
| `price_history` | Listing, price, currency, original price text, observed timestamp |
| `watches` | Stable watch IDs, rule JSON, enabled state |
| `watch_feeds` | Watch-to-feed associations |
| `notification_outbox` | Unique new-match notification intent, state, timestamps, last error |
| `notification_attempts` | Auditable SMTP delivery attempts |
| `listing_verifications` | Future page checks and evidence, separate from feed observations |

Use UTC timestamps, integer HUF values, uniqueness constraints, and Alembic migrations from the beginning. Store source-specific raw data in JSONB without forcing every feed field into a relational column. Keep retention and backups in mind for the free database tier.

## 8. Listing lifecycle: observation is not verification

A rolling RSS feed may stop showing a listing even when it is still available. Keep two separate dimensions:

- **Feed observation:** last observed, per-feed consecutive eligible misses, and observation evidence.
- **Verified listing status:** `unknown`, `active`, `inactive`, `verification_pending`, or `verification_failed`, with evidence and verification timestamp.

For a feed explicitly verified to be sufficiently complete, the *candidate* sequence may be `observed -> missed once -> missed twice -> verification pending`. For rolling feeds, **do not count feed disappearance as archival evidence**. Later, a bounded and permitted page check can identify explicit active/sold/archived signals. `403`, CAPTCHA, and timeouts are inconclusive; a `404` is evidence of unavailability, not automatically proof of a sale. Listings can become active again.

**MVP:** store observations and design the policy field. **Later:** implement page verification and progressive archival decisions after examining real HardverApró behavior.

## 9. API requirements

Start with a small, testable FastAPI application:

| Endpoint | Initial behavior |
|---|---|
| `GET /health` | Process liveness; no database dependency |
| `GET /ready` | Check database connectivity; return failure if unavailable |
| `GET /listings` | Paginated, read-only listing results; filters can grow later |
| `GET /listings/{listing_id}` | Listing detail or 404 |

Use Pydantic response schemas rather than exposing ORM entities directly. Keep router handlers thin and place query/pagination behavior in `services/listings.py`. Watch-management APIs, authentication, and public deployment are later decisions.

## 10. Local development and deployment

**Prerequisites:** `uv`, Docker Engine + Compose, a compatible Python version. Run PostgreSQL locally with `docker compose up -d`, install dependencies with `uv sync`, and apply migrations with `uv run alembic upgrade head`. Configure `.env` from `.env.example` (never commit `.env`). Document the actual app and CLI entrypoints in `pyproject.toml` before advertising commands as ready.

For production ingestion, GitHub Actions runs the CLI on an hourly best-effort schedule (for example `17 * * * *`) and supports `workflow_dispatch`. Use concurrency protection, GitHub secrets for PostgreSQL/SMTP credentials, and separate CI checks. Use Neon or another free PostgreSQL host only after verifying current limits and connection behavior. No paid infrastructure is required by design; free-tier limits must be monitored.

## 11. Testing and acceptance criteria

- [ ] RSS fixture is saved from a real HardverApró feed; identifiers, feed length, and fields are documented.
- [ ] Parser validates and preserves source fields without requiring live network access in tests.
- [ ] Docker PostgreSQL, SQLAlchemy models, and Alembic migrations work locally.
- [ ] FastAPI `/health`, `/ready`, and listing endpoints have tests.
- [ ] Ingesting the same feed twice creates no duplicate listings or price changes.
- [ ] Multiple feeds can reference the same canonical listing when identity is stable.
- [ ] Keyword/price rules handle exclusions, Unicode, and missing prices.
- [ ] A newly matched listing creates one durable notification intent.
- [ ] SMTP failure remains retryable and is recorded; tests use a fake transport.
- [ ] Feed errors and `304` never trigger false archival transitions.
- [ ] Local CLI and GitHub Actions invoke the same ingestion service.
- [ ] Ruff, pytest, and migration/integration checks pass in CI.

## 12. Roadmap

1. **Foundation (current):** FastAPI skeleton, `routers/`, `services/`, `schemas/`, `models/`, database connection, Docker PostgreSQL, Alembic, and health endpoints.
2. **RSS vertical slice:** HardverApró adapter, offline fixtures, candidate schema, feed/listing persistence, and idempotent CLI ingestion.
3. **Monitoring MVP:** Watch configuration, matching, notification outbox, Gmail SMTP, and hourly GitHub Actions.
4. **Lifecycle:** Feed completeness investigation, per-feed observation counters, cautious verification queue, page status evidence where permitted, and price-drop alerts.
5. **Catalog/enrichment:** More GPU/laptop feeds, permitted full-page extraction, Ollama + Pydantic hardware specs, model/version metadata, and re-enrichment.
6. **Frontend:** React/TypeScript/Vite listing grid, search/filter/sort, listing detail, seller/source metadata, and price history.
7. **Additional marketplaces:** New source adapters, source-specific rate limits, and cross-source deduplication policies.

## 13. Open decisions

- Validate HardverApró RSS URL formats, field coverage, identifier stability, rolling-window size, and access policy.
- Confirm Neon free-plan limits and whether local/CI connections require pooled or direct URLs.
- Decide where private watch definitions live and how updates are synchronized to the database.
- Define behavior when an existing listing starts matching after a price or watch-rule change.
- Decide retention limits for raw payloads and run logs, plus backup/export cadence.
- Defer authentication, frontend hosting, and public API access until needed.

## 14. Engineering principles

Keep marketplace adapters isolated. Keep HTTP concerns out of business services. Preserve raw evidence before normalization or enrichment. Prefer idempotent operations and explicit transactions. Treat missing information as unknown. Use migrations, tests, and structured logs. Implement only the abstractions needed for the current milestone while keeping the architecture easy to extend.
