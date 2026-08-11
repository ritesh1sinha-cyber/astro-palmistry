"""Sync full astro Python + review HTML to the peer-review bundle folder."""
from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = Path(r"C:\Users\IN009287\Downloads\Compressed\latest")
ASTRO_DST = BUNDLE / "astro_files"
ASTRO_PY_DST = BUNDLE / "astro_python"
REVIEW_DST = BUNDLE / "review_html"
CI = ROOT / "ci-storage"

ASTRO_SRC = ROOT / "engines" / "astro"
CORE_SRC = ROOT / "core"
NEW_PALM_DIR = ROOT / "engines" / "palm_api"

# Orchestration modules peers need to trace POST → worker → report.
ROOT_PY = ("api.py", "worker.py")
CORE_PY = (
    "auth.py",
    "billing.py",
    "config.py",
    "db.py",
    "errors.py",
    "handlers.py",
    "llm_client.py",
    "maintenance.py",
    "palm_cards.py",
    "palm_report.py",
    "pdf_export.py",
    "promo.py",
    "queue.py",
    "schema.sql",
    "stats.py",
    "store.py",
    "turnstile.py",
)

# Regression / review helpers for peers.
CI_FILES = (
    "test_v4_meaning_merge.py",
    "test_manifestation_fix.py",
    "test_v8_regression.py",
    "test_canonical_confluence_v9.py",
    "test_confluence_presentation_v9.py",
    "test_customer_text_sanitizer.py",
    "test_confluence_headline_v10.py",
    "test_post_v10_consistency.py",
    "test_promise_confluence.py",
    "test_review10_fixes.py",
    "test_latest_report_cleanup.py",
    "test_llm_prose.py",
    "test_canonical_result.py",
    "test_palm_canonical.py",
    "test_modern_correlation.py",
    "test_palm_cards_human_correlation.py",
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
    "gen_llm_peer_reports.py",
    "gen_llm_tab_smoke.py",
    "gen_palm_review.py",
    "age_band_regression.json",
    "random_chart_regression.json",
    "regression_summary.json",
)


def _copy_file(src: Path, dst: Path) -> None:
    if not src.is_file():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _sync_interpretation_config(dst_root: Path) -> int:
    """Copy JSON interpretation configs peers need for confluence/manifestation."""
    src = ASTRO_SRC / "interpretation" / "config"
    dst = dst_root / "engines" / "astro" / "interpretation" / "config"
    if not src.is_dir():
        return 0
    return _mirror_tree(src, dst, skip_names={"__pycache__"})


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


def _mirror_py_tree(src: Path, dst: Path) -> int:
    """Copy every .py file under src, preserving relative paths."""
    count = 0
    if not src.is_dir():
        return 0
    for path in src.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(src)
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        count += 1
    return count


def _sync_full_astro_python(dst_root: Path) -> int:
    """End-to-end astro stack: api/worker, core orchestration, all engines/astro .py."""
    if dst_root.is_dir():
        shutil.rmtree(dst_root)
    dst_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for name in ROOT_PY:
        _copy_file(ROOT / name, dst_root / name)
        if (dst_root / name).is_file():
            count += 1

    core_dst = dst_root / "core"
    for name in CORE_PY:
        _copy_file(CORE_SRC / name, core_dst / name)
        if (core_dst / name).is_file():
            count += 1

    astro_dst = dst_root / "engines" / "astro"
    count += _mirror_py_tree(ASTRO_SRC, astro_dst)
    return count


def main() -> int:
    if not BUNDLE.is_dir():
        BUNDLE.mkdir(parents=True, exist_ok=True)

    seed = Path(r"C:\Users\IN009287\Downloads\Compressed\graharekha_v5_full_source")
    astro_dst = ASTRO_DST / "engines" / "astro"
    if seed.is_dir() and not astro_dst.is_dir():
        print(f"Seeding empty bundle from {seed}")
        shutil.copytree(seed, BUNDLE, dirs_exist_ok=True)

    if not BUNDLE.is_dir():
        raise SystemExit(f"Peer review bundle not found: {BUNDLE}")

    # Full end-to-end astro Python (charts, techniques, report pipeline).
    py_count = _sync_full_astro_python(ASTRO_PY_DST)
    cfg_count = _sync_interpretation_config(ASTRO_PY_DST)

    # Keep astro_files aligned with the same full astro stack (+ palm for mixed drops).
    astro_files_py = _sync_full_astro_python(ASTRO_DST)
    cfg_count += _sync_interpretation_config(ASTRO_DST)
    palm_dst = ASTRO_DST / "engines" / "palm_api"
    palm_count = _mirror_py_tree(NEW_PALM_DIR, palm_dst)
    # Palm JSON correlation tables
    palm_data = NEW_PALM_DIR / "data"
    if palm_data.is_dir():
        palm_count += _mirror_tree(
            palm_data, palm_dst / "data", skip_names={"__pycache__"})
    updated = astro_files_py + palm_count

    # Frontend (chatEnabled / public-config wiring)
    _copy_file(ROOT / "site" / "index.html", BUNDLE / "site" / "index.html")
    _copy_file(ROOT / "requirements.api.txt", BUNDLE / "requirements.api.txt")
    _copy_file(ROOT / "docker-compose.local.yml", BUNDLE / "docker-compose.local.yml")

    # Review HTML — root bundle + nested copies used in earlier drops.
    REVIEW_DST.mkdir(parents=True, exist_ok=True)
    html_sources = (
        list(CI.glob("*.html"))
        + list((CI / "oversample").glob("*.html"))
        + list((CI / "review_html").rglob("*.html"))
    )
    for src_html in html_sources:
        # Preserve llm_smoke/ subfolder names when nested
        try:
            rel = src_html.relative_to(CI / "review_html")
        except ValueError:
            rel = Path(src_html.name)
        _copy_file(src_html, REVIEW_DST / rel)
        _copy_file(src_html, ASTRO_DST / "review_html" / rel)
        if rel.parent == Path("."):
            _copy_file(src_html, ASTRO_DST / src_html.name)

    # JSON smoke summaries for LLM peer review
    for src_json in (CI / "review_html").rglob("*.json"):
        try:
            rel = src_json.relative_to(CI / "review_html")
        except ValueError:
            continue
        _copy_file(src_json, REVIEW_DST / rel)
        _copy_file(src_json, ASTRO_DST / "review_html" / rel)

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
        f"astro_python .py files: {py_count}\n"
        f"astro_files .py files (astro+palm): {updated}\n"
        f"interpretation/config files: {cfg_count}\n"
        f"Review HTML files: {len(html_sources)}\n"
        f"Includes: engines/astro/llm/*, core/llm_client.py, site/index.html, "
        f"LLM smoke HTML under review_html/llm_smoke/\n",
        encoding="utf-8",
    )
    print(f"Peer review bundle updated: {BUNDLE}")
    print(f"astro_python (full end-to-end astro .py): {py_count}")
    print(f"astro_files (astro+palm .py): {updated}")
    print(f"interpretation/config files: {cfg_count}")
    print(f"Review HTML files: {len(html_sources)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
