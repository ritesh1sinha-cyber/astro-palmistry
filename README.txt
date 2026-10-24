GrahaRekha / astro-palmistry — Phase 1 deploy package
======================================================
Created for copying onto another PC (or overlay onto the GitHub clone).

Folder: astro-palmistry-phase1-deploy
Contains: changed application files + bundled MiniLM model (~476 MB).
Does NOT contain the full repo — overlay these paths onto your clone.

WHAT’S INCLUDED
---------------
• engines/astro/models/paraphrase-multilingual-MiniLM-L12-v2/
  Full local MiniLM (model.safetensors ~450 MB). Docker/API use this —
  no Hugging Face download required.

• Semantic / horary quality fixes
  - engines/astro/semantic_question.py       (new)
  - engines/astro/local_models.py
  - engines/astro/client_question_engine.py  (amount intent: “how much hike” ≠ Yes)
  - engines/astro/western_horary_rules.py
  - engines/astro/western_horary_report.py
  - engines/astro/horary_precompute.py
  - engines/astro/vedic_confluence_report.py
  - engines/astro/question_answer.py
  - engines/astro/present_read.py
  - core/handlers.py, api.py, …

• Docker / Railway (bundled model, no Hub download)
  - deploy/Dockerfile, Dockerfile.local
  - deploy/ensure_semantic_models.py
  - .gitattributes  (Git LFS rules for model weights)
  - MODELS.md, LOCAL.md, RAILWAY.md

• Tests
  - ci-storage/test_nlp_before_after.py
  - ci-storage/compare_semantic_routing.py
  - ci-storage/test_semantic_wiring.py
  - ci-storage/trim_and_load_minilm.py

HOW TO APPLY ON THE OTHER PC
----------------------------
1. Clone or open your astro-palmistry repo (same tree as GitHub).

2. Copy this package OVER the repo root (merge folders). Example PowerShell:

   $repo = "D:\path\to\astro-palmistry"
   $pkg  = "D:\path\to\astro-palmistry-phase1-deploy"
   Copy-Item -Path "$pkg\*" -Destination $repo -Recurse -Force

3. Confirm the weight file is real (~450 MB), not an empty pointer:

   (Get-Item "$repo\engines\astro\models\paraphrase-multilingual-MiniLM-L12-v2\model.safetensors").Length
   # expect ~470641600

4. Install runtime deps (once):

   pip install "torch==2.5.1" --index-url https://download.pytorch.org/whl/cpu
   pip install "sentence-transformers>=3.0,<6"
   pip install -r requirements.worker.txt

5. Verify models (no download):

   python deploy\ensure_semantic_models.py
   # -> [models] ready · bundled MiniLM=paraphrase-multilingual-MiniLM-L12-v2

6. Quality check (needs ~3+ GB free RAM / close Chrome if Windows paging errors):

   $env:PYTHONPATH = "engines;engines/astro"
   python ci-storage\test_nlp_before_after.py
   python ci-storage\trim_and_load_minilm.py

7. GitHub push (from that PC) — use Git LFS for model.safetensors:

   git lfs install
   git add .gitattributes engines/astro/models/
   git add -A
   git commit -m "Phase 1: bundled MiniLM + semantic horary amount intent"
   git push

   Docker/Railway then use `git lfs pull` / COPY — no Hugging Face fetch.
   ALLOW_MODEL_DOWNLOAD=1 is emergency-only.

PRE-PROD FLAGS
--------------
In core/config.py, before public launch set:
  _CODE_DEV_LOGIN = False
  _CODE_DEV_AUTO_PAY = False

MEMORY
------
Railway / Docker: plan ≥ 4 GB RAM for torch + MiniLM.
Windows: free commit charge (close Chrome) if you see OSError 1455.

QUALITY NOTE (already verified on source PC)
--------------------------------------------
“How much hike can I expect this year?” → intent=amount, H10 career,
answer shape increase_favoured — NOT bare “Yes”.
