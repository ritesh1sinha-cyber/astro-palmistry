# Local semantic models (MiniLM) — required for premium UX

The **full confluence report** (and the Bhardwaj semantic lane) group findings by
*meaning*, not just keywords. That uses **Sentence Transformers** with a local
**all-MiniLM-L6-v2** encoder (~90 MB) plus an optional cross-encoder for agreement
scoring.

Without these weights the engine falls back to a **lexical hash encoder** —
reports still generate, but clusters are thinner, duplicates slip through, and
copy feels more “machine stitched.”

## What runs where

| Component | Path | Purpose |
|-----------|------|---------|
| Loader | `engines/astro/local_models.py` | Offline load from `engines/astro/models/` |
| Download | `engines/astro/download_models.py` | One-time fetch from Hugging Face |
| Confluence | `engines/astro/confluence_engine.py` | MiniLM clustering + agreement |
| Bhardwaj lane | `engines/astro/bhardwaj_semantic.py` | Chart → book corpus by meaning |
| Fallback | `engines/astro/semantic_fallback.py` | Lexical stand-in if ST missing |
| Boot helper | `deploy/ensure_semantic_models.py` | Build + entrypoint ensure |

Preferred encoder (Phase 1): **`paraphrase-multilingual-MiniLM-L12-v2`**
under `engines/astro/models/`. Falls back to `all-MiniLM-L6-v2` if present.

```
engines/astro/models/paraphrase-multilingual-MiniLM-L12-v2/
engines/astro/models/cross-encoder-stsb-roberta-base/   # optional agreement scorer
```

## Bundled in the GitHub repo (Git LFS)

`model.safetensors` is ~450 MB — **GitHub rejects files over 100 MB** without
[Git LFS](https://git-lfs.com). This repo tracks weights under
`engines/astro/models/` via `.gitattributes`.

On the machine that pushes:

```bash
git lfs install
git add .gitattributes engines/astro/models/
git commit -m "Add paraphrase-multilingual-MiniLM-L12-v2 for semantic confluence"
git push
```

Docker / Railway **do not download from Hugging Face**. They use the LFS files
from the clone (`git lfs pull` in `deploy/Dockerfile`) or `COPY` from
the build context (`deploy/Dockerfile.local`).

Verify inside the image / checkout:

```bash
python deploy/ensure_semantic_models.py
# -> [models] ready · bundled MiniLM=paraphrase-multilingual-MiniLM-L12-v2
```

Emergency only: `ALLOW_MODEL_DOWNLOAD=1` permits a Hub fetch if LFS files were
skipped.

Preferred path:

```
engines/astro/models/paraphrase-multilingual-MiniLM-L12-v2/
```


## Docker & Railway (recommended — enabled by default)

Both `deploy/Dockerfile` (Railway) and `deploy/Dockerfile.local` default
to **`WITH_CONFLUENCE=1`**. Models come from the **repo (Git LFS)**, not Hugging Face:

1. Install CPU `torch` + `sentence-transformers`
2. **Worker image:** `git clone` + `git lfs pull` so `model.safetensors` is in the image
3. **Local image:** `COPY engines/astro/` (includes `models/`)
4. `ensure_semantic_models.py` **verifies** bundled weights (fails the build if missing)

Hub download only if you set `ALLOW_MODEL_DOWNLOAD=1` (emergency).

### Railway

`railway.json` passes `WITH_CONFLUENCE=1`. After deploy, confirm:

```bash
curl -s https://YOUR-SERVICE.up.railway.app/health | jq .semantic
```

Expect:

```json
{
  "mode": "minilm",
  "models": { "minilm": true, "cross_encoder": false }
}
```

(`cross_encoder` is optional for Phase 1.)

**Memory:** plan **≥ 4 GB RAM** on the Railway service once torch is loaded.
A full confluence report peaks around 2–3 GB resident during embedding.

**Build time:** first deploy ~10–15 min (torch wheels + LFS pull). Later deploys
cache Docker layers. No Hugging Face model fetch in the normal path.

To disable (smaller image, degraded confluence):

- Railway → Service → Variables: `WITH_CONFLUENCE=0`
- Or set build arg `WITH_CONFLUENCE=0` in `railway.json`

### Local Docker

```bash
docker compose -f docker-compose.local.yml up --build
```

`WITH_CONFLUENCE` is `"1"` in `docker-compose.local.yml`. The image copies
`engines/astro/models/` from the checkout (after `git lfs pull` on the host).

Verify:

```bash
curl -s http://localhost:8080/health | jq .semantic
python e2e_check.py --api http://localhost:8080 --full-report
```

### Production VM (`deploy/docker-compose.yml`)

`worker-heavy` already sets `WITH_CONFLUENCE: "1"`. Only the heavy pool needs
torch; `worker-light` stays lean.

## Bare laptop (no Docker)

Weights are already under `engines/astro/models/` once you clone with LFS:

```bash
git lfs install
git lfs pull
pip install "torch==2.5.1" --index-url https://download.pytorch.org/whl/cpu
pip install "sentence-transformers>=3.0,<6"
python deploy/ensure_semantic_models.py
# Note: torch 2.4.x fails MiniLM load (DTensor ImportError). Use 2.5.1+.
```

Emergency only (no LFS checkout): `python engines/astro/download_models.py`

Set before running the API:

```powershell
$env:PYTHONPATH = "engines;engines/astro"
$env:PYJHORA_SRC = "C:\Program Files\Python311\Lib\site-packages"
python -m uvicorn api:app --host 127.0.0.1 --port 8123
```

## Optional: generative polish (cloud LLM)

MiniLM does **semantic grouping**, not prose generation. For warmer openings set
on the API service:

```bash
ASTRO_LLM_KEY=sk-...
ASTRO_LLM_MODEL=gpt-4o-mini
# ASTRO_LLM_URL=https://api.openai.com/v1/chat/completions
```

See `engines/astro/astro_voice.py` → `llm_polish()`. This is optional; MiniLM is
the baseline for confluence quality.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `/health` shows `"mode": "degraded_lexical"` | ST not installed or models missing — rebuild with `WITH_CONFLUENCE=1`, check logs for `[models]` |
| `ModuleNotFoundError: sentence_transformers` | Image built with `WITH_CONFLUENCE=0` |
| Build fails: MiniLM missing | Run `git lfs pull` before push/build; confirm `model.safetensors` is a real ~450 MB file, not an LFS pointer |
| OOM / paging file too small (Windows) | Free RAM (close Chrome) or raise page file; Docker/Railway need ≥4 GB |
| OOM on Railway during full report | Raise service memory to 4–8 GB |

## Before charging for full reports at scale

1. `/health` → `semantic.mode` is **`minilm`**, not `degraded_lexical`
2. Run `e2e_check.py --full-report` — confluence section completes
3. Flip `_CODE_DEV_AUTO_PAY = False` in `core/config.py` when Razorpay is live
