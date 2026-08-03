# Vedic Astro — portable code bundle

Copied from `test8` — **runnable astro app + all lane engines**, without book PDFs, OCR dumps, or session/report history.

**Size:** ~300 MB (mostly PyJHora + MiniLM embedding model).

## What is included

| Component | Path | Purpose |
|-----------|------|---------|
| **Main app** | `astro_report_generator.py` | Web UI (sidebar), all APIs, report pipeline |
| **Chart math** | `pyjhora/src/` | D1, divisional, dasha, KP, panchang via Swiss Ephemeris |
| **Lane reports** | `vedic_*_report.py`, `numerology_report.py`, etc. | BNN, KP, Jaimini, Vimshottari, BTR, muhurat, horary, … |
| **Book rules (baked)** | `*_book_data.json` | Pre-extracted OCR rules — **no `book_ocr/` needed** |
| **Confluence AI routing** | `models/all-MiniLM-L6-v2/` | Offline semantic domain matching |
| **Palmistry** | `palm_api/` | Optional sidebar lane (same as palmistry-code) |
| **Western horary** | `western-horary-data/rules_v6.json` + `western_horary_*.py` | Louis/Lilly lane |

## What is NOT included (by design)

| Excluded | Why |
|----------|-----|
| `book_ocr/` (~2 GB) | Rules already in `*_book_data.json` |
| `*.pdf` books | Not needed at runtime |
| `models/cross-encoder-*` (~4.6 GB) | Optional; confluence works with MiniLM only |
| `reports/`, `_astro_sessions/` | Your generated output (empty dirs created) |
| `cursor-agent` | Optional AI narrative — install separately if wanted |

## Setup on a new PC

```bash
cd astro-code
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
bash scripts/run_server.sh
```

Open **http://127.0.0.1:8091**

### Linux (OpenCV)

```bash
sudo apt install libgl1
```

### If MiniLM model missing

```bash
python3 download_models.py    # downloads only MiniLM (~90 MB); needs internet once
```

## Main entry points

| Task | Command / URL |
|------|----------------|
| Full web app | `python3 astro_report_generator.py` |
| Port | `ASTRO_PORT=8091` (default) |
| Precompute chart CLI | `python3 natal_from_pyjhora.py --help` |
| BTR only | UI sidebar **BTR** or `python3 btr_rectify.py` |
| Palmistry only | Sidebar **Palmistry** or see `palm_api/README.md` |

## Sidebar sections (UI)

Vedic · Palmistry · Numerology · BTR · Event Predictor · User Question · Horary · Marriage Match · Muhurat · Daily Forecast

## Rebuilding book JSON from OCR (advanced)

Requires full `test8` checkout with `book_ocr/` and PDFs:

```bash
python3 build_bnn_data.py
python3 build_kp_data.py
# etc.
```

Normal client work does **not** need this step.

## Optional features

| Feature | Extra requirement |
|---------|-------------------|
| Cursor human report | `cursor-agent` on PATH |
| Cross-encoder agreement | `python3 download_models.py` (full, ~5 GB) |
| Re-OCR books | `ocr_pdf_jpg_chunks.py` + Tesseract (not in bundle) |

## File count

- ~170 Python modules at repo root
- 13 JSON corpora (`*_book_data.json`, KP table, nakshatra karmic tales)

---

**Bottom line:** Copy this folder + `pip install -r requirements.txt` once. No `test8`, no PDFs, no OCR tree required for day-to-day report generation.
