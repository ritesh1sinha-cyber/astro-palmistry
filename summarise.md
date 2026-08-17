# Session Summary — Classical Confluence Report Wiring

## Goal
Wire a classical-tone ("confluence") rephrase pass into the full-report LLM
prose pipeline so that, once the conversational page is accepted, an additional
LLM call rewrites the page into the authoritative voice of a practising Vedic
astrologer and merges the result back into the overlay. The pass must:

- emit only the fields the `ReportConfluenceProse` schema expects,
- never invent/calculate facts (Python owns all prediction truth), and
- never regress a working page (on any failure it returns `None` and leaves the
  existing overlay untouched).

## Source changes

### `engines/astro/llm/rules.py`
Replaced the `full_report_confluence` system-prompt body so its required output
**exactly** matches `ReportConfluenceProse`:
`astrological_basis, interpretation, personality, current_phase,
hardest_area_note, mind_now (list), why_now, family_note (list), areas (dict)`.
Removed all references to schema fields that no longer exist
(`executive_summary`, `hand_contrast_note`, `recent_months`) — these would now be
rejected by `extra="forbid"` and silently turn off classical tone. Prompt
versioning auto-invalidates the cache via the sha256 `prompt_version` digest, so
no manual bump was needed.

### `engines/astro/llm/humanize.py`
- `_llm_rephrase_full_report(facts, stats)` builds a compact fact payload
  (`public_fact_payload`), calls
  `_complete_validated(ReportConfluenceProse, system_prompt_for("full_report_confluence"), …)`,
  and projects the validated reply into the page-overlay keys (classical
  prose + per-area `interpretation`). Returns `None` on any failure.
- Wired at exactly **one** call site: inside `_humanize_report`, after the
  conversational overlay is built, screened and fact-filled, and after the
  `personality` emptiness guard — so it only runs when the conversational page
  already succeeded. The classic frozen renderer path (`accepted=0`) is
  untouched.

### `engines/astro/llm/schemas.py`
`ReportConfluenceProse` (already present) confirmed field/type/length/area
alignment and `extra="forbid"`. No structural edits required.

### `ci-storage/test_llm_prose.py`
Added `test_confluence_classical_reprise_merges`: stubs the LLM to return a
valid `ConversationalProse` (conversational layer) **and** a valid
`ReportConfluenceProse` (classical layer), then asserts the classical values
overwrite the page prose (`astrological_basis` replaced exactly) and the
classical per-area interpretation lands in the area shell.
Log line: `accepted=4 rejected=0 retries=0 fallback=False` — the classical
prose passes QA cleanly.

## Verification
- `ast.parse` OK for `rules.py`, `humanize.py`, `schemas.py`, and the edited
  test file.
- `system_prompt_for("full_report_confluence")` resolves; prompt aligned
  (no `executive_summary`/`hand_contrast_note`/`recent_months`).
- Schema `extra="forbid"` rejects stray `executive_summary`/`hand_contrast_note`
  fields (proving the prompt/schema alignment matters and is enforced on real
  LLM responses via `complete_model(schema=...)`).
- `_llm_rephrase_full_report` importable as a module-global.
- `ci-storage/test_llm_prose.py`: **47 passed**.
- Full LLM suite (`engines/astro/llm/` + `ci-storage`): **161 passed, 2 failed**.

### Docker (local dev stack)
`docker-compose.local.yml` live-mounts `./engines` → `/app/engines`, so the API
container picks up the source on boot. `api` was restarted; `/health → 200`;
postgres + redis healthy; MiniLM + sentence-transformers loaded. The report at
`http://localhost:3000/api/file/...#sec-creativity-projects` renders correctly
(deterministic classical body).

## Known failures (pre-existing, unrelated)
Two tests fail with `ModuleNotFoundError: No module named 'palm_api'` at
`core/palm_conversational.py:325` (`test_palm_conversational_render_paid_areas`,
`test_the_free_page_renders_both_new_sections`). `palm_api` lives under
`engines/palm_api` but the test `sys.path` (ROOT + `engines/astro`) does not
include `engines`, so `import palm_api` cannot resolve. This is an
environmental/test-path issue in code not touched in this session — **not** a
regression from these changes.

## Scratch files in repo root
Left alongside the repo's existing `_apply_*.py` convention for traceability:
`_apply_prompt.py`, `_apply_prompt3.py` (rules.py patch history);
`_run_tests.py`, `_run_ci_tests.py`, `_run_all_llm.py`, `_verify_wiring.py`,
`_fix_indent2.py` (verification helpers). `_apply_prompt2.py` (the broken
intermediate that split the prompt's string literals) was deleted. These are
not mounted into the container and are safe to remove.

## Continue your work (next steps)
1. **Enable the LLM path locally** to see real classical prose (the stubbed
   tests prove the wiring; a live run needs a backend):
   ```bash
   LLM_ENABLED=1 LLM_BASE_URL=http://host.docker.internal:1234/v1 LLM_API_KEY=<key> \
     docker compose -f docker-compose.local.yml up -d api
   ```
   (`restart` does not re-evaluate `${LLM_ENABLED:-0}`; `up -d api` does.)
2. If you want the local dev test runner to exercise the palm render path, add
   `engines` to the test `sys.path` (or mount `./engines/palm_api`) so
   `import palm_api` resolves, then the two palm_api failures will run for
   real.
3. Consider promoting `_llm_rephrase_full_report` behind an explicit
   `ReportConfig`/tone gate if classical-tone rollout should be opt-in rather
   than always-on.
4. Optionally delete the scratch helpers above and run
   `python _run_all_llm.py` to re-confirm the green baseline after cleanup.
