# Architecture, database design and capacity for 1 lakh+ users

## 1. Shape

```
                    ┌──────────── Caddy (TLS, HTTP/3) ────────────┐
                    │  /            → static site (same origin)   │
                    │  /api/*       → api replicas (least_conn)   │
                    └───────────────────┬────────────────────────┘
                                        │
                    ┌───────────────────▼──────────────────┐
                    │  api  (stateless, N replicas)         │
                    │  auth · orders · polling · delivery   │
                    │  NEVER runs an engine                 │
                    └───────┬───────────────────┬───────────┘
                            │                   │
                  ┌─────────▼────────┐   ┌──────▼───────────────┐
                  │ Redis            │   │ Postgres             │
                  │ queue · slots    │   │ users · orders       │
                  │ ETAs · rate limit│   │ entitlements · cache │
                  └─────────┬────────┘   └──────▲───────────────┘
                            │                   │
        ┌───────────────────┴───────┐           │
        │                           │           │
┌───────▼────────┐        ┌─────────▼──────┐    │
│ worker-heavy   │        │ worker-light   │────┘
│ full reports   │        │ palm · horary  │
│ birth-time     │        │ daily · match  │      ┌──────────────┐
└───────┬────────┘        └────────┬───────┘─────▶│ S3 / R2      │
        └──────────────────────────┘              │ report halves│
                                                  └──────────────┘
```

**The API never runs an engine.** Every reading is a job. That single rule is
what makes the thing scalable: a 3-minute report cannot block a request thread,
and API replicas stay small (no mediapipe, no PyJHora, no torch).

**Three deployment shapes, one codebase:**

| Shape | Config | Good for |
|---|---|---|
| One container | `INLINE_WORKER=1`, SQLite, no Redis | laptop, demo, pilot |
| One box | Postgres + Redis + worker containers | launch → ~10k users |
| Fleet | N api + N workers, managed PG/Redis, S3 | 1 lakh+ |

Moving between them changes environment variables and replica counts. No code.

---

## 2. Database design

### Why it is shaped this way

**Payment and access are separate tables.** `orders` records what was *paid*;
`entitlements` records what may be *seen*. A refund revokes the entitlement and
leaves the payment history intact — you can still answer "did this person pay in
March?" a year later. A promo, a support grant and a purchase all flow through
the same access check, so there is exactly one place that answers "can they read
this?" (`billing.entitled`).

**`precomputes` is the scalability keystone.** An ephemeris pass is the expensive
part of every astrology feature, and it depends only on the birth *moment* — not
on who asked. Keyed by `sha256(dob|tob|lat|lon|tz)` and engine version, so:

- the full report, the daily reading, muhurat and event timing all reuse one pass
- twins, or two customers born the same minute in the same city, share it
- **measured: 378 ms cold → 5 ms warm, a 75× saving** on the hot path

**Reports live in object storage, not the database.** Postgres holds keys. 1M
reports at ~200 KB is 200 GB — that belongs in S3/R2 at ₹2/GB, not in your
primary database's backups.

**Free and paid halves are separate objects.** Not one document with a CSS blur.
The paid bytes never reach an unpaid browser.

**`jobs` and `payment_events` are monthly partitions.** At 1 lakh users a busy
month is a few hundred thousand job rows; dropping a partition is instant where
`DELETE` would be a vacuum problem. `payment_events` keeps every webhook,
signature-valid or not — that is your evidence in a chargeback.

**Credits are an append-only ledger.** `users.credits` is a cache of
`credit_ledger`; the ledger is the truth. Support can always explain a balance.

### Tables

| Table | Rows at 1 lakh users | Notes |
|---|---|---|
| `users` | 100 k | `email` citext unique; `google_sub` unique |
| `sessions` | ~300 k | only a **hash** of the token is stored, so a DB leak cannot mint sessions |
| `charts` | ~250 k | unique on `(user_id, chart_hash)` — re-submitting the same birth data reuses the row |
| `precomputes` | ~200 k | the cache; LRU-evicted after 120 unused days |
| `orders` | ~150 k/yr | `idempotency_key` unique → retry-safe order creation |
| `payment_events` | ~400 k/yr | partitioned, never deleted |
| `entitlements` | ~150 k | partial unique index prevents double-granting the same thing |
| `subscriptions` | ~20 k | index on `current_period_end` for the renewal sweep |
| `credit_ledger` | ~200 k | append-only |
| `usage_counters` | ~300 k | free-tier metering, PK `(user, kind, period)` |
| `reports` | ~1 M | keys only; `expires_at` drives retention |
| `jobs` | ~2 M/yr | partitioned monthly, pruned at 90 days |

Total live data is **well under 20 GB** — comfortable for a single Postgres
instance for a long time. The growth is all in object storage, which is cheap
and independently scalable.

### Indexes that matter

Every hot query is covered:

- `ux_charts_user_hash` — chart dedupe on submit
- `ix_reports_user (user_id, created_at DESC)` — the "my reports" page
- `ux_entitlement_live` — the access check, on every paid view
- `ix_orders_status` — *partial*, only `created|pending`: the reconciliation
  sweep scans a handful of rows, not the whole table
- `ix_jobs_live` — partial, only `queued|processing`
- `ix_subs_renewal` — partial, only `active`

Partial indexes matter here: order and job tables are append-heavy and mostly
historical, so indexing only the live rows keeps them tiny.

---

## 3. Queue design

Redis holds the live queue; Postgres holds the durable record. If Redis is lost,
no money or report is lost — only in-flight positions.

**Priority.** Score = `priority × 1e12 + enqueue_time`. FIFO within a band,
bands ordered:

| Priority | Who |
|---|---|
| 1 | already paid for this item |
| 3 | active subscriber |
| 5 | free user |

A ₹1,499 customer never waits behind a queue of free chart summaries.

**Concurrency.** A ZSET of *leased* slots per kind, taken under `WATCH/MULTI`.
Leases expire, so a `SIGKILL`ed worker cannot leak capacity — and no `EVAL`,
because some managed Redis offerings block Lua. Per-kind caps stop one slow kind
from eating the fleet:

```
CAP_FULL_REPORT=4   CAP_BTR=2   CAP_PALM=6   CAP_DEFAULT=12
```

**ETAs are measured, not guessed.** An EWMA of real durations per kind, in Redis,
so every replica quotes the same number and it self-corrects to your hardware.

**Pools.** `worker-heavy` takes full reports and rectification; `worker-light`
takes everything else. This is the difference between "a 2-second answer takes 2
seconds" and "a 2-second answer waits behind three reports".

---

## 4. Capacity for 1 lakh users

### Measured on modest CPU (in this build)

| Job | Time |
|---|---|
| chart summary (cache warm) | **52 ms** |
| chart summary (cold) | 378 ms |
| numerology | 30 ms |
| horary (both traditions) | ~1–5 s |
| kundali match | ~100 ms – 10 s |
| muhurat | 1.5 s |
| palm reading | 4–6 s |
| birth-time rectification | 1.8 s – 2 min (event count) |
| full confluence report | 90–180 s |

Throughput observed with **two** worker threads: 15 cold charts in 2.1 s
(7/sec), warm 12.9/sec.

### The arithmetic

Take 1,00,000 registered, 20% monthly active (20k), 3% paying:

| Load | Volume | CPU-seconds/month |
|---|---|---|
| Free chart summaries | 60k/mo | ~3,100 |
| Numerology | 20k/mo | 600 |
| Daily readings (5k subscribers × 30) | 150k/mo | ~45,000 |
| Palm readings | 20k/mo | ~100,000 |
| Horary | 10k/mo | ~30,000 |
| Full reports | 1,500/mo | ~225,000 |
| **Total** | | **≈ 404,000 CPU-s ≈ 112 CPU-hours/month** |

One core provides ~720 CPU-hours a month. **Average load is well under one
core.** Capacity planning here is entirely about *peak*, not volume.

### Peak, which is what actually matters

Assume an evening peak carrying 15% of the day's traffic in one hour, and a
launch-day spike of 10×. Sizing for "a full report starts within 2 minutes and a
palm reading within 20 seconds at peak":

| Stage | Users | Machine | Replicas |
|---|---|---|---|
| Launch | <5k | 1 × 4 vCPU / 8 GB | api 2, light 3, heavy 1 |
| Growth | 5k–30k | 1 × 8 vCPU / 16 GB | api 2, light 4, heavy 2 |
| **1 lakh** | 100k | 2–3 × 8 vCPU / 16 GB + managed PG + managed Redis | api 4, light 8, heavy 3 |
| Spike | — | `docker compose up -d --scale worker-light=16` | minutes to apply |

Storage at 1 lakh users: ~1M report halves ≈ **200–400 GB in S3/R2**, plus
~2 GB of Postgres. Palm photos are deleted after analysis (`KEEP_UPLOADS=0`).

### What to watch

Queue depth, not CPU. If `light` depth stays above ~20 or `heavy` above ~5,
users are watching a spinner:

```bash
curl -s https://your-domain/api/queue | jq
```

`GET /api/queue` returns depth per pool, slots in use per kind, and the measured
average per kind. That is the one dashboard that matters.

---

## 5. Where the real limits are

Being straight about the ceilings:

1. **Postgres is a single writer.** Fine to several lakh users at this write
   volume. Beyond that: PgBouncer (transaction pooling) first, read replicas for
   the reports list, and only then consider sharding by `user_id`.
2. **The engines are single-threaded Python.** Throughput scales with worker
   count, not with cleverness. Budget CPU accordingly.
3. **The confluence report needs torch** (~2 GB image, ~1.5 GB RSS). That is why
   `worker-light` is built with `WITH_CONFLUENCE=0` — keep the heavy image on
   the heavy pool only.
4. **Redis is the queue's single point of failure.** Losing it drops in-flight
   positions (not data or money). Use managed Redis with AOF, or accept that a
   restart makes a handful of users press the button again.
5. **A worker restart kills its in-flight job.** Jobs are retried once for
   transient errors; a `docker compose restart` mid-report means someone's paid
   report needs regenerating. Drain first: scale the pool to 0, wait for
   `/api/queue` to clear, deploy, scale back up.

---

## 6. Deploy

```bash
cd deploy
cp .env.example .env && $EDITOR .env      # domain, APP_SECRET, PG_PASSWORD, Razorpay
openssl rand -hex 32                      # → APP_SECRET
# copy Swiss Ephemeris .se1 files into deploy/ephe/
docker compose up -d --build
docker compose logs -f caddy              # watch the certificate issue
```

Verify:

```bash
curl https://your-domain/health
python3 e2e_check.py --api https://your-domain
```

### Going-live checklist

- [ ] `APP_SECRET` and `PG_PASSWORD` freshly generated
- [ ] `DEV_LOGIN` and `INLINE_WORKER` **unset** (the API refuses dev login without it)
- [ ] `RAZORPAY_WEBHOOK_SECRET` set — **without it every webhook is rejected**, which is the correct failure mode
- [ ] Razorpay webhook URL pointed at `/api/payment/webhook`
- [ ] `ALLOWED_ORIGINS` = your domain
- [ ] Google OAuth: production domain in *Authorised JavaScript origins*
- [ ] Terms / Privacy / Refunds / Contact pages live (Indian PSPs require them)
- [ ] Backups running **and one restore rehearsed**
- [ ] `PyJHora==4.7.0` pinned, `deploy/ephe/*.se1` present
