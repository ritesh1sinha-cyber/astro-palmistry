import sys
from pathlib import Path

sys.path.insert(0, "/app/engines")
sys.path.insert(0, "/app/engines/palm_api")
sys.path.insert(0, "/app")

from palm_api.pipeline import analyze_image_paths
from core.palm_report import build_palm_html_reading
from core.palm_validator import validate_report_html

print("=== GENERATING AL_AR REPORT (Ritesh) ===")
raw_alar = analyze_image_paths(["/app/AL.jpg", "/app/AR.jpg"], active_hand="right", overlay_dir=Path("/app/overlay_out"))
req_alar = {"name": "Ritesh", "age": 41, "gender": "male", "dominant": "right"}
free_alar, paid_alar, meta_alar = build_palm_html_reading(raw_alar, req_alar, price=298)
Path("/app/sample_palm_free_AL_AR.html").write_text(free_alar, encoding="utf-8")
Path("/app/sample_palm_paid_AL_AR.html").write_text(paid_alar, encoding="utf-8")
ok_alar, errors_alar = validate_report_html(paid_alar)
print("AL_AR Validation: " + ("PASSED" if ok_alar else "FAILED"))
if not ok_alar:
    for e in errors_alar:
        print("  ❌ " + str(e))

print("\n=== GENERATING L_R REPORT (Ananya) ===")
raw_lr = analyze_image_paths(["/app/L.jpg", "/app/R.jpg"], active_hand="right", overlay_dir=Path("/app/overlay_out"))
req_lr = {"name": "Ananya", "age": 28, "gender": "female", "dominant": "right"}
free_lr, paid_lr, meta_lr = build_palm_html_reading(raw_lr, req_lr, price=298)
Path("/app/sample_palm_free_L_R.html").write_text(free_lr, encoding="utf-8")
Path("/app/sample_palm_paid_L_R.html").write_text(paid_lr, encoding="utf-8")
ok_lr, errors_lr = validate_report_html(paid_lr)
print("L_R Validation: " + ("PASSED" if ok_lr else "FAILED"))
if not ok_lr:
    for e in errors_lr:
        print("  ❌ " + str(e))

