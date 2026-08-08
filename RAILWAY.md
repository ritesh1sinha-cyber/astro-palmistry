# Deploying the backend on Railway

Railway runs real containers, so the engines and the long-running workers both
work — unlike Vercel, where the dependency bundle (318 MB) exceeds the 250 MB
function limit and a 90–180 s report exceeds the execution cap.

Shape for the test round: **one service** (API + workers in one container),
plus managed Postgres and Redis.

```
Vercel (frontend, static)  ──/api/*──▶  Railway service (api + inline workers)
                                              ├── Railway Postgres
                                              └── Railway Redis
```

## 1. Create the project

1. railway.app → **New Project → Deploy from GitHub repo** → pick this repo.
2. Railway reads `railway.json` and builds `deploy/Dockerfile.worker`.
   First build takes ~8–12 minutes (mediapipe and PyJHora are large).
3. **Add Postgres:** New → Database → PostgreSQL.
4. **Add Redis:** New → Database → Redis.

## 2. Variables

On the app service, set these. The two `${{...}}` values are Railway references —
paste them exactly; Railway substitutes the real credentials.

```bash
ENV=prod
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

APP_SECRET=            # openssl rand -hex 32
INLINE_WORKER=1        # one service answers HTTP and runs readings
INLINE_WORKER_THREADS=2

ALLOWED_ORIGINS=https://your-app.vercel.app
LOCAL_STORE=/data/storage

# for the test round only — lets e2e_check.py sign in. REMOVE before real payments.
DEV_LOGIN=1

# when you have them:
GOOGLE_CLIENT_ID=424015602169-sh7vtf9gita53b7s6jkiqr20vms8aevl.apps.googleusercontent.com
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
RAZORPAY_PAYMENT_BUTTON_ID=pl_TMzAWfueT93HPY
```

`GOOGLE_CLIENT_ID` is **required for the Google button on production**. Local
dev can read it from the gitignored `.config` file; Railway cannot. Without this
variable, `/api/public-config` returns `"googleClientId":""` and the site shows
guest/admin only.

In [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials),
Authorized JavaScript origins must include:

- `https://www.graharekha.co.in`
- `https://graharekha.co.in`
- `http://localhost:3000` (local Docker)

After setting the variable, redeploy the Railway service (or wait for the
auto-redeploy) and hard-refresh the site. Confirm with:

```bash
curl -s https://www.graharekha.co.in/api/public-config
# googleClientId should be non-empty
```

Railway's `DATABASE_URL` arrives as `postgresql://…`, which SQLAlchemy would
route to psycopg2. The app rewrites it to psycopg3 on startup, so you don't need
to touch it.

## 3. Add a volume

Generated reports are written to `LOCAL_STORE`. Without a volume they vanish on
every redeploy, and a customer's paid report 404s.

- Service → **Settings → Volumes → New Volume**, mount path `/data`.

For anything beyond testing, use object storage instead — set `S3_BUCKET`,
`S3_ENDPOINT`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (Cloudflare R2 is
cheapest for this) and the volume stops mattering.

## 4. Verify

```bash
curl -s https://your-service.up.railway.app/health | jq .semantic
```

Expect `"mode": "minilm"` and `"models": {"minilm": true, "cross_encoder": true}`.
If you see `"degraded_lexical"`, the image was built without sentence-transformers
— see **MODELS.md**.

```bash
python3 e2e_check.py --api https://your-service.up.railway.app
```

Expect 29 checks. Two will differ from local:

- **`no citations in output`** must still pass — that is the check that your
  readings carry no book, author or page reference.
- **`unsigned webhook rejected`** will pass *instead of* the unlock checks once
  `RAZORPAY_WEBHOOK_SECRET` is set. That is correct: without a valid signature no
  order can be marked paid.

## 5. Then the frontend on Vercel

1. Import the same repo. Vercel reads `vercel.json` and serves `site/`.
2. Edit `vercel.json`: replace `BACKEND_URL_PLACEHOLDER` with your Railway host
   (Vercel rewrites cannot read env vars, so it must be a literal), commit, redeploy.
3. Set `ALLOWED_ORIGINS` on Railway to the Vercel URL.

## If the deploy fails, check these first

**`FileNotFoundError: PyJHora source not found`** — `PYJHORA_SRC` is unset. The
image now sets it to `/usr/local/lib/python3.12/site-packages`; if you overrode
the variable, that is the value it needs.

**Startup crash on `CREATE EXTENSION`** — the schema needs `pgcrypto` and
`citext`. Railway's Postgres allows both for the default user. If yours does not,
run them once from the database's Query tab as a superuser, then redeploy.

**A palm reading dies with no error in the log** — that is an out-of-memory kill.
mediapipe holds ~1 GB while it runs. Raise the service memory, or test the
astrology features first: they are far lighter.

**Healthcheck fails but logs look fine** — the first boot creates the schema and
partitions. `healthcheckTimeout` is already 300 s in `railway.json`; don't lower it.

**`ModuleNotFoundError: No module named 'fakeredis'` on `/health`** — `REDIS_URL`
is missing or still the literal `${{Redis.REDIS_URL}}` (Redis plugin not linked).
Either add **New → Database → Redis** and paste `REDIS_URL=${{Redis.REDIS_URL}}`,
or redeploy after pulling the fix that bundles fakeredis for single-service
`INLINE_WORKER=1` deploys.

## What to expect on the free tier

- **Build time** ~10–15 min with MiniLM enabled (torch wheels + `git lfs pull`).
  Image ~3 GB. Model weights come from the GitHub repo (LFS), not Hugging Face.
- **Memory:** plan **≥ 4 GB RAM** on the service. mediapipe needs ~1 GB for palm;
  torch + MiniLM adds ~1.5 GB during a full confluence report.
- **Cold start** after idle is ~20–30 s on the first request.
- **MiniLM semantic grouping is ON by default** (`WITH_CONFLUENCE=1` in
  `railway.json`). Check `/health` → `semantic.mode` is `"minilm"`, not
  `"degraded_lexical"`. See **MODELS.md** to disable on tiny boxes.
- **Cost:** roughly $5–15/month at test volumes. It sleeps less aggressively than
  Render's free tier, which is why it is the better choice for a demo you want to
  show someone.
