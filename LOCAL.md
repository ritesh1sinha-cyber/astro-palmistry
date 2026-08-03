# Running the whole thing locally

One command, no configuration. This is the fastest loop — and after Railway,
the cheapest.

```bash
docker compose -f docker-compose.local.yml up --build
```

Then open **http://localhost:3000**.

First build takes ~8–12 minutes (mediapipe and PyJHora are large). After that,
rebuilds are seconds — `core/` and `api.py` are bind-mounted, so editing the
product layer needs only a restart, not a rebuild.

| URL | What |
|---|---|
| http://localhost:3000 | the site, with `/api` proxied same-origin (mirrors Vercel) |
| http://localhost:8080 | the API directly, for `curl` |
| http://localhost:8080/docs | FastAPI's interactive docs |
| localhost:5432 | Postgres (`astro` / `localdev`) |
| localhost:6379 | Redis |

## Verify it

```bash
# from the host
python3 e2e_check.py --api http://localhost:8080 \
  --left  path/to/left_palm.jpg \
  --right path/to/right_palm.jpg \
  --name "Ritesh Kumar Sinha" --dob 1985-03-08 --tob 13:05 --age 41

# or from inside the container, no host Python needed
docker compose -f docker-compose.local.yml exec api \
  python e2e_check.py --api http://localhost:8080
```

29 checks, about two minutes. `no citations in output` is the one that proves your
readings carry no book, author or page reference.

## Why this differs from production

| | local | `deploy/docker-compose.yml` |
|---|---|---|
| app containers | one (API + inline workers) | api ×2, worker-heavy ×2, worker-light ×4 |
| web server | nginx, plain HTTP | Caddy, automatic HTTPS |
| `DEV_LOGIN` | on | **off** |
| secrets | throwaway, in the compose file | from `.env`, generated |
| concurrency caps | 1–4 (a laptop) | 4–12 |

Same image, same code paths. What passes here passes on a VM.

## Useful commands

```bash
# logs from the app only
docker compose -f docker-compose.local.yml logs -f api

# queue depth and measured per-kind durations
curl -s localhost:8080/api/queue | jq

# poke at the database
docker compose -f docker-compose.local.yml exec postgres psql -U astro -d astro
#   \dt                                 list tables
#   select kind, status, duration_ms from jobs order by created_at desc limit 10;
#   select chart_hash, hits from precomputes;      the cache paying off
#   select * from v_daily_revenue;                 revenue view

# nightly housekeeping, on demand
docker compose -f docker-compose.local.yml exec api python -m core.maintenance --once

# start clean (drops the database and all generated reports)
docker compose -f docker-compose.local.yml down -v
```

## Turning on the full confluence report

It needs `sentence-transformers` + torch, which add ~2 GB:

```bash
docker compose -f docker-compose.local.yml build \
  --build-arg WITH_CONFLUENCE=1 api
docker compose -f docker-compose.local.yml up -d api
```

Then `e2e_check.py --full-report`. Every other feature works without it.

## Swiss Ephemeris (optional)

Without the `.se1` files, swisseph uses its built-in model — accurate to a
fraction of a degree, but not bit-identical to JHora. For exact parity:

```bash
mkdir -p deploy/ephe && cp /path/to/*.se1 deploy/ephe/
```

then add to the `api` service in `docker-compose.local.yml`:

```yaml
    environment:
      EPHE_PATH: /ephe
    volumes:
      - ./deploy/ephe:/ephe:ro
```

The entrypoint installs them at boot and logs how many it found.

## If something goes wrong

**Build fails on a `COPY`** — this build is the decisive test. Railway failed
three times on path-specific COPYs it did not place in the build context
(`deploy/ephe/`, `deploy/entrypoint.sh`, `engines/astro`) while sibling paths
arrived fine. The Dockerfile now does a single `COPY . .` and asserts the context
is complete, so:

* **builds locally, failed on Railway** → a Railway build-context quirk, not the
  Dockerfile. Deploy from a registry image instead of Railway's builder, or use a
  host that builds the context faithfully.
* **fails locally too, with `BUILD CONTEXT INCOMPLETE`** → the assertion names
  the missing path and we fix the repo.

**A palm reading dies with no error** — an out-of-memory kill. mediapipe holds
~1 GB. Give Docker Desktop at least 4 GB (Settings → Resources).

**`FileNotFoundError: PyJHora source not found`** — `PYJHORA_SRC` is unset. The
image sets it to `/usr/local/lib/python3.12/site-packages`.

**Camera doesn't work** — `getUserMedia` needs HTTPS *or* localhost.
`http://localhost:3000` counts; `http://192.168.x.x:3000` does not. To test from
a phone, use `ngrok http 3000`.

**Port already in use** — change the left-hand number in `ports:`, e.g.
`"3001:80"`.
