"""Sync latest astro report code + review HTML to graharekha_v5_full_source peer-review folder."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(r"C:\Users\IN009287\Downloads\Compressed\graharekha_v5_full_source")
ASTRO_DST = BUNDLE / "astro_files"
REVIEW_DST = BUNDLE / "review_html"
CI = ROOT / "ci-storage"

# New v4 stacks not in the original snapshot layout.
NEW_ASTRO_DIRS = ("interpretation", "narration", "qa_checks")
NEW_ASTRO_FILES = ("local_models.py",)

# Regression / review helpers for peers.
CI_FILES = (
    "test_v4_meaning_merge.py",
    "test_manifestation_fix.py",
    "test_v8_regression.py",
    "test_v3_regression.py",
    "test_final_fix_loopholes.py",
    "test_rubric_matrix.py",
    "test_recognition_semantic.py",
    "test_golden_fixtures_structured.py",
    "gen_age_band_regression.py",
    "gen_random_chart_regression.py",
    "gen_docker_smoke_copy.py",
    "gen_interactive_review.py",
    "gen_oversample_reports.py",
    "age_band_regression.json",
    "random_chart_regression.json",
    "regression_summary.json",
)


def _copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _mirror_tree(src: Path, dst: Path, *, skip_names: set[str] | None = None) -> int:
    skip = skip_names or set()
    count = 0
    if not src.is_dir():
        return 0
    for path in src.rglob("*"):
        rel = path.relative_to(src)
        if any(part in skip for part in rel.parts):
            continue
        if path.is_dir():
            continue
        if path.suffix == ".pyc" or "__pycache__" in path.parts:
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def main() -> int:
    if not BUNDLE.is_dir():
        raise SystemExit(f"Peer review bundle not found: {BUNDLE}")

    astro_src = ROOT / "engines" / "astro"
    astro_dst = ASTRO_DST / "engines" / "astro"
    updated = 0

    # Refresh every module already present in the study snapshot.
    for dst_file in astro_dst.rglob("*.py"):
        rel = dst_file.relative_to(astro_dst)
        src_file = astro_src / rel
        if src_file.is_file():
            shutil.copy2(src_file, dst_file)
            updated += 1

    for rel_name in NEW_ASTRO_FILES:
        _copy_file(astro_src / rel_name, astro_dst / rel_name)
        updated += 1

    for dir_name in NEW_ASTRO_DIRS:
        updated += _mirror_tree(astro_src / dir_name, astro_dst / dir_name)

    # Top-level orchestration copied in the original bundle.
    for rel in ("api.py",):
        _copy_file(ROOT / rel, ASTRO_DST / rel)
    for rel in ("config.py", "handlers.py", "queue.py", "billing.py", "db.py", "stats.py"):
        _copy_file(ROOT / "core" / rel, ASTRO_DST / "core" / rel)

    # Review HTML — root bundle + nested copies used in earlier drops.
    REVIEW_DST.mkdir(parents=True, exist_ok=True)
    html_sources = list(CI.glob("*.html")) + list((CI / "oversample").glob("*.html"))
    for src_html in html_sources:
        _copy_file(src_html, REVIEW_DST / src_html.name)
        _copy_file(src_html, ASTRO_DST / src_html.name)
        _copy_file(src_html, ASTRO_DST / "review_html" / src_html.name)

    # ci-storage helpers for peer verification.
    ci_dst = BUNDLE / "ci-storage"
    ci_dst.mkdir(parents=True, exist_ok=True)
    for name in CI_FILES:
        _copy_file(CI / name, ci_dst / name)
    _mirror_tree(CI / "oversample", ci_dst / "oversample", skip_names={"__pycache__"})
    _mirror_tree(CI / "review_html", ci_dst / "review_html", skip_names={"__pycache__"})

    stamp = BUNDLE / "SYNC_STAMP.txt"
    stamp.write_text(
        f"Synced from {ROOT}\nDate: {date.today().isoformat()}\n"
        f"Astro modules refreshed: {updated}\n",
        encoding="utf-8",
    )
    print(f"Peer review bundle updated: {BUNDLE}")
    print(f"Astro .py modules refreshed: {updated}")
    print(f"Review HTML files: {len(html_sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
