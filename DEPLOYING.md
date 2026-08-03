# Deploying — and why the backend cannot live on Vercel

## The short version

| Piece | Vercel | Why |
|---|---|---|
| **Frontend** (`site/index.html`) | ✅ yes, ideal | static file, global CDN, free |
| **Backend** (`api.py` + `worker.py`) | ❌ no | see below — three separate hard limits |

So the split is: **frontend on Vercel, backend on a container host.** The frontend
proxies `/api/*` to the backend (`vercel.json`), so the browser still sees one
origin — no CORS, and the camera keeps working.

---

## Why not Vercel for the backend

Not a preference. Three measured, hard limits:

**1. Bundle size.** Vercel serverless functions cap at **250 MB unzipped**.
Measured from the installed packages:

| Package | Size |
|---|---|
| mediapipe | 115 MB |
| opencv | 75 MB |
| PyJHora | 100 MB |
| pyswisseph | 6.5 MB |
| SQLAlchemy + FastAPI | 21 MB |
| **Total** | **≈ 318 MB** |

That is already 27% over the limit — before `sentence-transformers` + `torch`
(another ~2 GB) that the confluence report needs. There is no trimming that
closes a gap that size.

**2. Execution time.** Hobby caps a function at 60 s, Pro at 300 s. A full
confluence report takes **90–180 s**, and birth-time rectification can reach
2 minutes. Even on Pro you would be one slow chart away from a timeout, and the
customer has already paid.

**3. No long-running workers.** The whole design is a queue plus worker
processes that hold a job for minutes and report progress. Vercel has no
always-on process — cron jobs are also duration-capped. You would have to throw
away the queue, the ETAs and the priority ordering, and with them the ability to
tell someone "you are third in line, about 4 minutes".

There is also no writable local disk and no SQLite, though those are the easy
parts to solve.

---

## What I recommend for your test round

```
┌─────────────────────┐        ┌──────────────────────────────┐
│ Vercel              │  /api  │ Render (or Railway / Fly)     │
│ site/index.html     │───────▶│ api + inline workers          │
│ global CDN, free    │  proxy │ Postgres + Redis (managed)    │
└─────────────────────┘        └──────────────────────────────┘
                                              │
                                    later: lift-and-shift to
                                    your VM with docker compose
```

Render is the closest thing to your eventual VM: it runs the same Docker image,
so what works there works with `docker compose` on your own box. `render.yaml`
in this repo is a ready blueprint — Postgres, Redis, and the API with inline
workers, all wired.

### Steps

**1. Backend on Render** (~10 minutes)

- New → Blueprint → point at this repo. It reads `render.yaml`.
- Before the first deploy, drop the Swiss Ephemeris `*.se1` files into
  `deploy/ephe/` and commit them to a private branch, or add a build step that
  downloads them (they are gitignored here by default).
- Set the secrets it asks for: `GOOGLE_CLIENT_ID`, Razorpay keys,
  `ALLOWED_ORIGINS` (your Vercel URL).
- Note the service URL, e.g. `https://astro-api.onrender.com`.

**2. Frontend on Vercel** (~2 minutes)

- Import the repo. Vercel reads `vercel.json` and serves `site/`.
- Replace `BACKEND_URL_PLACEHOLDER` in `vercel.json` with your Render host, then
  redeploy. (Vercel rewrites do not read env vars, so this is a literal edit.)
- Leave `apiBase: ''` in `index.html` — the proxy makes it same-origin.

**3. Verify**

```bash
python3 e2e_check.py --api https://your-app.vercel.app
```

28 checks, including the paywall attacks. `DEV_LOGIN=1` on the backend is needed
for the auth step — turn it off before you take real payments.

**4. Later, your VM**

```bash
cd deploy && cp .env.example .env && $EDITOR .env
docker compose up -d --build
```

Same images, plus separate worker pools and Caddy for TLS. Nothing to rewrite.

---

## Free-tier warnings, so they don't surprise you

- **Render free tier sleeps** after 15 minutes idle and cold-starts in ~30 s. The
  first request after a nap will look broken. Use Starter (paid) for anything you
  are demoing to someone else.
- **Memory:** mediapipe needs ~1 GB resident. A 512 MB instance will be OOM-killed
  mid-palm-reading. `render.yaml` asks for Standard for that reason.
- **The confluence report needs torch** (~2 GB image, ~1.5 GB RSS). It is
  commented out of `requirements.worker.txt`. Leave it off for the test round —
  every other feature works without it — and enable it when you have a box with
  4 GB.
- **Cold caches:** the first chart on a fresh deploy pays the full ephemeris
  cost (~400 ms); after that the `precomputes` cache makes it ~5 ms.

## Alternatives, honestly compared

| Host | Fits? | Notes |
|---|---|---|
| **Render** | ✅ | blueprint included; closest to your VM |
| **Railway** | ✅ | `railway.json` included; nice DX, usage-priced |
| **Fly.io** | ✅ | best if you want India-region placement (`blr`) |
| **Google Cloud Run** | ⚠️ | works, but 60-min cap and cold starts fight the queue model |
| **AWS Lambda** | ❌ | same 250 MB / 15-min limits as Vercel |
| **Vercel** | ❌ backend / ✅ frontend | see above |
