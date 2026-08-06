# GrahaRekha — production stack 

Your planets, read from your hand. graharekha.co.in

Palmistry + Vedic astrology as a paid product, built to carry 1 lakh+ users.

```
api.py                 stateless HTTP API (auth, orders, polling, delivery)
worker.py              runs the engines; scale by replicas
core/
  schema.sql           canonical PostgreSQL schema (partitions, indexes, views)
  db.py                data access (Postgres in prod, SQLite for a laptop)
  queue.py             Redis queue: priority, leased slots, measured ETAs
  billing.py           orders, entitlements, subscriptions, credits, webhooks
  auth.py              Google Sign-In verified server-side, revocable sessions
  handlers.py          the only code that touches the engines
  palm_report.py       palm free/paid mapping
  store.py             object storage (S3/R2/MinIO or local)
  maintenance.py       nightly retention, partition roll, backup
site/index.html        the website
deploy/                Dockerfiles, compose, Caddy, .env.example
e2e_check.py           post-deploy gate: 28 checks including paywall attacks
ARCHITECTURE.md        design, database rationale, capacity maths
```

## House rules baked into the code

- **No citations in a reading.** Book titles, author names and page numbers are
  stripped from every customer-facing byte (`engines/astro/astro_voice.py` →
  `strip_citations`). Where a source name was labelling a method, it is replaced
  with a neutral description — "the nadi method", "the sub-lord method" — so the
  sentence still tells the reader which technique spoke. `e2e_check.py` scans
  every generated report half against a blocklist and fails the build on a leak.
- **No machinery talk.** "deterministic", "rule engine", "no LLM", internal
  filenames and calibration warnings never reach a customer.
- **Every reading is addressed to one person**, opening with facts only their own
  chart or hand produces.
- **The paid half never leaves the server** before payment clears.

## Where your engine code goes

The two engines are imported, never modified. Place them so they are importable:

```
engines/palm_api/           ← your palm_api package
engines/astro/              ← contents of your astro web/ folder
                              (astro_precompute.py, vedic_confluence_report.py,
                               numerology_report.py, kundali_match.py,
                               muhurat_checker.py, btr_rectify.py, …)
engines/astro/astro_voice.py   ← from this project (personalisation)
engines/astro/astro_split.py   ← from this project (free/paid split)
engines/astro/astro_hotfix.py  ← from this project (upstream glyph bug)
deploy/ephe/                ← Swiss Ephemeris .se1 files
```

`Dockerfile.worker` copies those into place.

## Run it locally with Docker (recommended)

```bash
docker compose -f docker-compose.local.yml up --build
open http://localhost:3000
```

One container runs the API and the workers, with Postgres, Redis and nginx
alongside. nginx proxies `/api` so the frontend is same-origin — the same shape
as Vercel in front of Railway. See **LOCAL.md**.

## Run it without Docker (no infrastructure at all)

```bash
pip install "fastapi[standard]" sqlalchemy redis fakeredis pydantic
export DEV_LOGIN=1 APP_SECRET=dev-only LOCAL_STORE=./storage
export DATABASE_URL=sqlite:///./astro.db PYTHONPATH=engines:engines/astro
uvicorn api:app --port 8080          # inline worker starts automatically
python3 -m http.server 5500 -d site  # then open http://localhost:5500
```

## Run it in production

```bash
cd deploy
cp .env.example .env && $EDITOR .env
openssl rand -hex 32                 # APP_SECRET, and again for PG_PASSWORD
docker compose up -d --build
python3 ../e2e_check.py --api https://your-domain
```

Scaling is replica counts, nothing else:

```bash
docker compose up -d --scale worker-light=8 --scale worker-heavy=3
```

See **ARCHITECTURE.md** for the database design, the capacity arithmetic, and an
honest list of where the ceilings are.
