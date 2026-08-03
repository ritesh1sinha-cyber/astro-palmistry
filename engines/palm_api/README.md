# Palmistry Reader API

Upload a palm photo → computer vision extracts lines/mounts/morphology → predictions are matched from **7,000+ rules** extracted from all 10 palmistry PDFs in `test8/palmistry/` (via existing OCR under `palmistry_ocr/`).

No LLM. Predictions cite book + page from the corpus.

## Setup

```bash
cd /home/oppo/Desktop/test8
pip install -r palm_api/requirements.txt
python3 -m palm_api.build_corpus   # first time (~2s)
```

On first analyze, the MediaPipe hand model is downloaded to `palm_api/data/hand_landmarker.task` (~3 MB).

## Run

```bash
uvicorn palm_api.app:app --host 127.0.0.1 --port 8010
```

Open http://127.0.0.1:8010 — upload right/left palm images and click **Analyze & predict**.

## API

| Endpoint | Description |
|----------|-------------|
| `GET /` | Web UI |
| `GET /health` | Rules loaded count |
| `POST /api/analyze` | Single palm (`file`, `hand=left\|right`) |
| `POST /api/analyze/both` | Right + left (`right`, `left`, `active_hand`) |
| `POST /api/rebuild-corpus` | Re-scan all OCR texts into rules JSON |

## Stack

- **Landmarks:** MediaPipe Hand Landmarker (21 points) -> affine warp to a canonical palm frame (wrist bottom, fingers top, thumb/Venus mount on the right; left palms are mirrored).
- **Line tracing (classical, no DL):** `palm_lines.py` builds a curved template per line from the landmarks (so each line is always placed in the correct anatomical zone), then pulls each template sample onto the nearest real crease ridge and smooths it into a curved polyline. Polylines are mapped back to the original photo via the inverse affine.
  - Major lines: life, head, heart, fate (each with quality = clear / broken / chained / faint).
  - Minor lines: Sun (Apollo), Mercury/Health, Marriage, Girdle of Venus, Ring of Solomon, Children, Travel/restlessness.
  - Mounts: 7 zones scored from local texture.
- **Hand & finger morphology (`analyzer.py`):** hand type, finger/palm ratio, index-vs-ring length, head/life-line attachment, and **thumb** analysis (length vs index, will-vs-logic phalange balance, opening angle) — all from the landmarks, with book-backed meanings.
- **Special marks (`special_marks.py`):** the crease map is thinned to a skeleton; skeleton junctions/endpoints and small closed contours are classified into cross, star, grille, triangle, square, island, fish (Matsya) and trident (Trishul), each assigned to its nearest mount zone. Heuristic — confidence is reported and one sign is kept per zone.
- **Both-hands confluence (`confluence.py`):** left + right are processed internally; the report leads with one combined reading (dominant = current/developed, non-dominant = innate). Lines, mounts and special marks are compared across hands (reinforced / developed / latent), and timed human predictions are synthesized.
- **Human report, developer references:** the user report shows human, second-person predictions with age-of-event and no book citations. The underlying book/page sources for every point are written to a developer `reference.txt` (linked under the report).
- **Calibration:** templates are calibrated against the confirmed reference markings in `data/markers/01cec126c3c2_correct.json`. Run `python3 -m palm_api.tools.eval_lines` (from `test8/`) to measure mean per-line distance vs that ground truth.
- **Rules:** Heuristic extraction from `palmistry_ocr/*/*_ocr_full.txt` (palm terms + interpretive verbs, deduped).
- **Matching:** Keyword/tag overlap + category bonus vs measured features (major + minor lines + mounts).

## Book-rule coverage (50 Case Studies in Modern Palmistry)

All 449 rules extracted from `50_CASE_STUDIES_IN_MODERN_PALMISTRY_ocr_full.txt` live in
`data/rules_corpus.json` and are searched/matched for every reading. What the **detector**
can measure from a single 2-D palm photo:

| Book feature | Detected? | How |
| --- | --- | --- |
| Life / Head / Heart / Fate lines | Yes | curved templates + crease refinement |
| Line breaks / chains / faint sections | Yes | per-line `quality` |
| Head–life line attachment (joined/separate) | Yes | `lines.head.start_relation` |
| 7 mounts (Jupiter…Moon) | Yes | texture scoring per zone |
| Sun, Mercury/Health, Marriage, Girdle of Venus, Ring of Solomon | Yes | ridge density in zone |
| Children lines, Travel/restlessness lines | Yes | ridge density in percussion/Moon zones |
| Special marks: cross, star, grille, triangle, square, island, fish, trident | Yes | skeleton + contour heuristics |
| Thumb length (will), will-vs-logic phalanges, opening angle | Yes | landmark geometry |
| Index-vs-ring & finger length / setting | Yes | landmark geometry |
| Hand type (earth/air/fire/water) | Yes | shape ratios |

**Not reliably extractable from one flat photo** (their *text* rules remain searchable in the
corpus, but the detector does not measure them, to avoid false readings):

- Nails (shape, colour, moons, health spots) — fingertips are rarely in focus/resolution.
- Fingerprint patterns (arch / loop / whorl) — need high-resolution fingertip ridges.
- Skin colour / texture / redness — lighting and white-balance dependent.
- Thumb tip shape (conic / spatulate / square) and flexibility / set — need a side view.
- Fine line forks / branches and exact phalange shapes — below reliable photo resolution.

The user-facing **overlay** is drawn on the original photo as curved colored lines with a legend. Manual marking helper: `./mark_palm.sh [image]` (labelme) saves polylines to `data/markers/`, and `python3 palm_api/render_markers.py <markers.json>` renders them.

Palmistry is a traditional/entertainment practice with no scientific basis; treat all output as for-fun.
