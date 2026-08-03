from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST8 = ROOT.parent
PALMISTRY_DIR = TEST8 / "palmistry"
OCR_DIR = TEST8 / "palmistry_ocr"
DATA_DIR = ROOT / "data"
RULES_CORPUS = DATA_DIR / "rules_corpus.json"
HAND_MODEL = DATA_DIR / "hand_landmarker.task"
HAND_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
)
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"

for d in (DATA_DIR, UPLOAD_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)
