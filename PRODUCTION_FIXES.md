# GrahaRekha — Final Life-Area Production Patch

## Files changed
- `llm/clean_report.py`
- `llm/rules.py`
- `llm/schemas.py`
- `llm/test_clean_report.py`
- `report_render.py`

## What is enforced
1. Deterministic complete confluence owns every life-area verdict.
2. Qwen cannot upgrade MIXED/MODERATE into strongly supported/favourable language.
3. Qwen-generated conclusions that contradict the deterministic verdict are discarded and replaced with a deterministic astrologer-style conclusion.
4. Future timing is derived from normalized `future_confluence` checkpoints, not from an LLM-created timing sentence or a stale relief window.
5. `Improves` / `Eases but continues` is not treated as `GOOD`.
6. Future dates in prose must belong to that area's own validated checkpoints.
7. Unsupported `things will be better` / `eventually things will improve` wording is rejected.
8. Health conclusions reject diagnosis, cure, treatment, medication and recovery/outcome language.
9. Internal/meta language is removed from `Where You Are Now`.
10. Generic final-guidance filler is rejected; guidance falls back to approved area-specific actions.
11. Canonical life-area titles are enforced by the renderer.
12. The clean report has a publication gate before and after rendering.
13. If the clean report fails validation, the system fails closed instead of silently falling back to the old legacy report.
14. Prompt/schema versions are bumped to the final confluence-lock versions.

## Verification
- `pytest -q llm/test_clean_report.py` -> **28 passed**
- `pytest -q llm/test_clean_report.py test_section_nav.py` -> **38 passed**

An unrelated pre-existing `report_render_test.py` collection error remains in the broader repository (`horary()` API mismatch). It is not part of this life-area patch.
