"""What the customer actually receives, per job kind.

The handlers used to call a report generator per kind and then hand the HTML to
`astro_split` to cut it into a free half and a paid half by looking for section
headings. That worked for the old long-form reports, where "free" and "paid"
were contiguous blocks of text.

The card design does not split that way. The paywall sits INSIDE each card — the
headline and the evidence are free, the dated window and the remedy are not — so
cutting the document in half would either give away the timing or hide the
headlines. Every renderer here already takes `paid: bool` and locks the right
parts in place, which means the honest way to produce two halves is to render
twice.

That also removes a whole class of bug: there is no longer any way for a section
to land on the wrong side of the paywall because a heading was renamed.

One module per screen, one function each, all returning `(free_html, paid_html,
meta)` so `core.handlers` stays thin and testable.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import report_shell as RS


def clean(html: str) -> str:
    """Public wrapper so callers appending their own HTML can scrub it too.

    `core.handlers` bolts the old long-form document onto the paid half as an
    appendix. That append happened AFTER the render, so the appendix bypassed the
    chokepoint entirely and leaked a lane called "Longevity" into the paid
    report. Anything concatenated onto a rendered document has to come back
    through here.
    """
    return _scrub(html)


def _safe(fn, *a, **k) -> str:
    """A supporting block must never take the whole report down with it."""
    try:
        return fn(*a, **k) or ""
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] {getattr(fn, '__module__', '?')}."
              f"{getattr(fn, '__name__', '?')} failed: "
              f"{type(exc).__name__}: {exc}", flush=True)
        return ""


# --- Post-render validation guard -------------------------------------------
# Catches internal-data leakage, placeholder text, duplicate sections, and
# sentence corruption that slipped through earlier gates.  Runs after _scrub
# so it sees exactly what the customer will see.

def _post_render_guard(html: str) -> str:
    """Validate rendered HTML and strip any forbidden content found."""
    if not html:
        return html
    # Always strip known internal leakage (abbr titles, placeholder text, etc.)
    html = _strip_forbidden_patterns(html)
    try:
        from llm.report_validator import validate_rendered_html
        vr = validate_rendered_html(html)
        if not vr.ok:
            print(f"[report_render] post-render guard found "
                  f"{len(vr.errors)} errors, {len(vr.warnings)} warnings",
                  flush=True)
            for e in vr.errors:
                print(f"  ERROR [{e.code}] {e.message}", flush=True)
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] post-render guard validation failed: {exc}",
              flush=True)
    return html


def _strip_forbidden_patterns(html: str) -> str:
    """Remove known placeholder/fallback text from rendered HTML."""
    import re
    patterns = [
        r"This remedy is linked to a relevant chart factor",
        r"The chart evidence is summarized in the life-area reading above",
        r"Timing evidence is included in the overall reading",
        r"Promised, not yet active",
        r"Full analyst working",
        r"pending LLM prose",
        r"awaiting humanization",
        r"\[pending",
        r"\[placeholder",
        r"\[TODO",
        r"\[INTERNAL",
        r"Raw classical wording",
        r"Existing chart-rule",
        r"internal rule id",
    ]
    for pat in patterns:
        html = re.sub(pat, "", html, flags=re.I)
    # Strip title attributes from jargon abbr tags (prevents internal term leakage)
    html = re.sub(r'(<abbr\s+class="jargon")\s+title="[^"]*"', r'\1', html)
    # Clean up double spaces left by removal
    html = re.sub(r"  +", " ", html)
    # Clean up empty paragraphs
    html = re.sub(r"<p>\s*</p>", "", html)
    # The customer firewall blanks a whole text node when any part of it trips a
    # leak pattern. A labelled box then survives as a heading with nothing under
    # it — the reader sees an empty grey "Current timing" panel and concludes the
    # report is broken. Drop any labelled block left with no content.
    html = re.sub(
        r'<p class="fact-lead">\s*<span class="ev-label">[^<]*</span>\s*</p>',
        "", html)
    html = re.sub(
        r'<div class="why-now">\s*<span class="ev-label">[^<]*</span>\s*'
        r'<p>\s*</p>\s*</div>',
        "", html)
    return html


def _voice_polish(html: str) -> str:
    """Plain-English pass for customer fragments (no personal opening block)."""
    try:
        import os
        import astro_voice as V
        out = V.strip_leaks(html or "")
        out = V.strip_machinery(out)
        out = V.humanise(out)
        out = V.strip_citations(out, hide_system_names=True)
        if os.getenv("PLAIN_ENGLISH", "1") == "1":
            out = V.translate_jargon(V.rephrase(out), keep_original=False)
        return out
    except Exception:                                                # noqa: BLE001
        return html


def _scrub(html: str, *, allowed_dates: Optional[set] = None) -> str:
    """Last gate before a customer sees anything. Never bypass this.

    `no_longevity.scrub` was written for sentences. Run over a whole document it
    also rewrites the stylesheet — its whitespace and punctuation tidying is
    harmless there but pointless, and one of its numeric patterns could in
    principle eat a CSS value. So the <style> and <script> blocks are lifted out,
    the prose is scrubbed, and they are put back untouched.

    (The pass that found this also caught scrub turning "21.5 of 36" into
    "21. 5 of 36" — fixed in no_longevity itself, since that bug applied to any
    decimal anywhere.)
    """
    try:
        from no_longevity import scrub
    except Exception:                                                # noqa: BLE001
        return html
    out = scrub(html) if "<style" not in html and "<script" not in html \
        else _scrub_stashed(html, scrub)

    # Direct, concise voice — cut filler without touching a fact. The card
    # design skips `astro_voice.personalise` for most kinds, so this is the
    # only gate horary / daily / numerology / muhurat / BTR prose passes.
    try:
        from astro_voice import concise
        out = concise(out)
    except Exception:                                                # noqa: BLE001
        pass
    try:
        from qa_checks.grammar_check import fix_grammar
        out = fix_grammar(out)
    except Exception:                                                # noqa: BLE001
        pass

    # P2-4/P2-5: soften any exact month-year that is not backed by one of
    # this report's own timing windows, then run the consistency linter as
    # a visible (log-only) gate rather than dead test-only code. Neither
    # step raises — a false positive here must never take a paid report
    # down; it is surfaced so it can be fixed at the source.
    if allowed_dates:
        try:
            from qa_checks.date_guard import soften_unvalidated_dates
            out = soften_unvalidated_dates(out, allowed=allowed_dates)
        except Exception:                                            # noqa: BLE001
            pass
    # Final customer boundary: sanitize known raw-rule/classical fragments
    # before the consistency check. This is deliberately after all appendices
    # and renderer output have been assembled.
    try:
        from qa_checks.final_customer_boundary import finalize_customer_html
        out = finalize_customer_html(out, strict=True)
    except Exception as exc:                                        # noqa: BLE001
        # One last fail-closed pass. If a legacy appendix introduced a raw
        # fragment after the first sanitizer, sanitize it again and only return
        # if the visible text is clean.
        try:
            from qa_checks.customer_text_sanitizer import sanitize_html_document, validate_customer_text
            out = sanitize_html_document(out)
            leaks = validate_customer_text(out)
            if leaks:
                raise RuntimeError(f"customer evidence firewall residual leaks: {leaks[:4]}")
        except Exception as final_exc:                              # noqa: BLE001
            print(f"[report_render] final customer boundary failed: {final_exc}", flush=True)
            # Do not ship contaminated customer HTML. Return a minimal safe
            # document rather than silently logging and continuing.
            out = (
                '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
                '<title>Graharekha report</title></head><body>'
                '<p>The report could not be safely rendered. Please regenerate it.</p>'
                '</body></html>'
            )

    try:
        from qa_checks.report_consistency import validate_report_consistency
        result = validate_report_consistency(out)
        if not result.get("ok"):
            print(f"[report_render] consistency check failed: "
                  f"{result['failures']}", flush=True)
    except Exception:                                                # noqa: BLE001
        pass

    # The section rail goes on last, after every sanitizer. Adding it earlier
    # would put a <nav> full of heading text through scrubbers that rewrite
    # prose, and the rail is navigation, not prose.
    try:
        import report_shell as RS
        out = RS.inject_section_nav(out)
    except Exception:                                                # noqa: BLE001
        pass
    return out


def _scrub_stashed(html: str, scrub) -> str:
    import re as _re
    keep: list[str] = []

    def _stash(m: "_re.Match[str]") -> str:
        keep.append(m.group(0))
        return f"\x00KEEP{len(keep) - 1}\x00"

    stashed = _re.sub(r"<(style|script)\b.*?</\1>", _stash, html,
                      flags=_re.S | _re.I)
    out = scrub(stashed)
    for i, block in enumerate(keep):
        out = out.replace(f"\x00KEEP{i}\x00", block)
    return out


def _appendix_block(html: str, *, summary: str) -> str:
    """Long-form lane document — fragment only, no nested stylesheets."""
    if not html or not html.strip():
        return ""
    import astro_split as SP
    body = SP.as_fragment(clean(html))
    if not body.strip():
        return ""
    return (f'<details class="workings workings-main"><summary>{summary}</summary>'
            f'<div class="workings-wrap">{body}</div></details>')

# ---------------------------------------------------------------------------
# the flagship
# ---------------------------------------------------------------------------
def full_report(pc: dict, *, name: str = "", question: str = "",
                today: Optional[date] = None, price: int = 298,
                bundle_price: int = 298, lat: float = 0.0, lon: float = 0.0,
                tz: float = 5.5, daily: Any = None) -> tuple:
    """Present read, who you are, your past, the cards, timing, remedies.

    Order is deliberate and it is the commercial argument as much as the
    editorial one: the reader meets a claim about the six months they have just
    lived BEFORE anything is asked of them. If that lands, everything after it
    is credible; if it does not, they should close the page.
    """
    today = today or date.today()
    first = (name or "").split()[0] if name else ""

    import deep_evidence as DE
    DE.begin(pc, lat=lat, lon=lon, tz=tz, today=today)
    try:
        return _full_report_inner(
            pc, name=name, question=question, today=today, price=price,
            bundle_price=bundle_price, lat=lat, lon=lon, tz=tz, daily=daily,
            first=first)
    finally:
        DE.end()


def _full_report_inner(pc: dict, *, name: str = "", question: str = "",
                       today: date, price: int = 298, bundle_price: int = 298,
                       lat: float = 0.0, lon: float = 0.0, tz: float = 5.5,
                       daily: Any = None, first: str = "") -> tuple:
    present_block = None
    try:
        import present_read as PR
        present_block = PR.build(pc, today=today)
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] present read failed: {exc}", flush=True)

    past_html = ""
    try:
        import report_recognition as RR
        past_html = RR.render(RR.build(pc))
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] your-past failed: {exc}", flush=True)

    timing_html = ""
    timing_rows: list = []
    n_periods = 0
    try:
        import report_cards as RC
        import report_timing as RT
        areas = [(a.key, a.house) for a in RC.AREAS]
        labels = {a.key: a.label for a in RC.AREAS}
        timing_rows = RT.best_windows(pc, areas, years=5, limit=4,
                                      lat=lat, lon=lon, tz=tz)
        timing_html = RT.render(pc, timing_rows, labels)
        n_periods = len(RC.build_timeline(pc, today=today))
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] timing failed: {exc}", flush=True)
    n_windows = len(timing_rows)

    q_html = ""

    from qa_checks.report_diversity import ReportDiversityGate
    import report_cards as RC
    gate = ReportDiversityGate()
    shared_cards = RC.build_cards(
        pc, today=today, gate=gate, featured_timing=timing_rows)

    # Timing is now rendered from the same canonical area results used by the
    # cards/dashboard/Why blocks. The initial best_windows call is only a
    # source candidate; the canonical result is the source of truth.
    try:
        canonical_timing_rows = []
        for card in shared_cards:
            cr = (card.confluence or {}).get("canonical_result") or {}
            canonical_timing_rows.extend(
                (cr.get("timing") or {}).get("featured_windows") or [])
        if canonical_timing_rows:
            import report_timing as RT
            labels = {a.key: a.label for a in RC.AREAS}
            timing_html = RT.render(pc, canonical_timing_rows, labels)
            timing_rows = canonical_timing_rows
            n_windows = len(timing_rows)
    except Exception as exc:  # noqa: BLE001
        print(f"[report_render] canonical timing render failed: {exc}", flush=True)

    # LLM prose layer (facts in → structured prose out). Off unless configured.
    # Free and Paid share the same canonical truth but use different fact
    # projections (depth). When the LLM fails QA, humanize fills deterministic
    # fallback prose — prediction facts never change.
    free_prose_overlay: dict = {}
    paid_prose_overlay: dict = {}
    llm_meta: dict = {"enabled": False}
    facts_payload: dict = {}
    paid_facts = None
    free_facts = None
    try:
        from llm.facts import build_report_facts, project_for_access, public_fact_payload
        from llm.humanize import humanize
        base_facts = build_report_facts(
            pc, shared_cards, name=name, access="paid", today=today)
        paid_facts = project_for_access(base_facts, "paid")
        free_facts = project_for_access(base_facts, "free")
        facts_payload = public_fact_payload(paid_facts)
        # One LLM pass on paid-depth facts (rate-limit friendly). Free/paid
        # HTML still differ via renderer locks; language overlay shares truth.
        # Generate Free and Paid prose from their own access projections.
        # Never reuse Paid prose on Free: the Paid facts contain exact dates,
        # detailed evidence and remedies that the Free model must never see.
        free_llm = humanize("full_report", free_facts, access="free")
        paid_llm = humanize("full_report", paid_facts, access="paid")
        free_prose_overlay = free_llm.get("overlay") or {}
        paid_prose_overlay = paid_llm.get("overlay") or {}
        llm_meta = {
            "enabled": bool(paid_llm.get("enabled") or free_llm.get("enabled")),
            "stats": paid_llm.get("stats") or {},
            "free": {
                "stats": free_llm.get("stats") or {},
                "fallback_used": bool(free_llm.get("fallback_used")),
                "run_meta": free_llm.get("run_meta") or {},
            },
            "paid": {
                "stats": paid_llm.get("stats") or {},
                "fallback_used": bool(paid_llm.get("fallback_used")),
                "run_meta": paid_llm.get("run_meta") or {},
            },
        }
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] llm humanize skipped: {exc}", flush=True)
        free_prose_overlay, paid_prose_overlay = {}, {}

    # Every real date this document is allowed to print: the best-windows
    # list, every per-card trajectory window, and the running dasha/
    # antardasha envelope. Anything else that looks like an exact month-year
    # gets softened by date_guard in _scrub (P2-4).
    allowed_dates: set = set()
    try:
        from qa_checks.date_guard import allowed_month_years
        window_sources: list = list(timing_rows)
        for c in shared_cards:
            window_sources.extend(
                {"start": t.get("start"), "end": t.get("end")}
                for t in (c.trajectory or []))
            for node in list(getattr(c, "transition_map", None) or []):
                if isinstance(node, dict):
                    window_sources.append(
                        {"start": node.get("start"), "end": node.get("end")})
                else:
                    window_sources.append({
                        "start": getattr(node, "start", None),
                        "end": getattr(node, "end", None),
                    })
            for row in list(getattr(c, "transit_context", None) or []):
                if isinstance(row, dict):
                    window_sources.append(
                        {"start": row.get("start"), "end": row.get("end")})
                else:
                    window_sources.append({
                        "start": getattr(row, "start", None),
                        "end": getattr(row, "end", None),
                    })
            # The paid analytical layer has its own authoritative future
            # checkpoints. Include those exact dates in the final customer
            # date allowlist; otherwise _scrub can correctly-but-destructively
            # soften the very future dates we just calculated.
            if paid_facts is not None and paid:
                for aj in list(getattr(paid_facts, "life_area_judgements", None) or []):
                    for fc in list(getattr(aj, "future_confluence", None) or []):
                        if hasattr(fc, "model_dump"):
                            fc = fc.model_dump()
                        if isinstance(fc, dict):
                            d = fc.get("date")
                            if d:
                                window_sources.append({"start": d, "end": d})
                    for d in (getattr(aj, "relief_window", ""), getattr(aj, "stronger_window", "")):
                        if d:
                            window_sources.append({"start": d, "end": d})
        vim = pc.get("vimshottari", {}) or {}
        window_sources.append(vim.get("current_md") or {})
        window_sources.extend(vim.get("current_md_antardashas") or [])
        # Conversational free section: phase end + recent-months trust windows.
        try:
            from report_cards import current_ad
            ad = current_ad(pc) or {}
            window_sources.append({"start": ad.get("start"), "end": ad.get("end")})
        except Exception:  # noqa: BLE001
            pass
        try:
            import past_validation as PVH
            hist = PVH.build(pc, today=today, months=4, max_events=4) or {}
            for ev in list(hist.get("events") or [])[:4]:
                if isinstance(ev, dict):
                    window_sources.append(
                        {"start": ev.get("start"), "end": ev.get("end")})
        except Exception:  # noqa: BLE001
            pass
        allowed_dates = allowed_month_years(window_sources)
    except Exception:                                                 # noqa: BLE001
        allowed_dates = set()

    def build(paid: bool) -> str:
        import report_cards as RC
        prose = paid_prose_overlay if paid else free_prose_overlay
        if not isinstance(prose, dict):
            prose = {}
        tier = (llm_meta.get("paid") if paid else llm_meta.get("free")) or {}
        accepted = int((tier.get("stats") or {}).get("accepted") or 0)
        use_conversational = (
            bool(llm_meta.get("enabled"))
            and accepted > 0
            and bool(prose.get("conversational"))
            and bool(str(prose.get("personality") or "").strip())
        )
        if use_conversational:
            import report_conversational as RConv
            # The stones and the practical step are computed, not written, so
            # the conversational page carries the same block as the classic one
            # instead of leaving the reading with nothing to act on.
            fact_cards = []
            if paid and paid_facts is not None:
                fact_cards = list(getattr(paid_facts, "cards", None) or [])
            elif (not paid) and free_facts is not None:
                fact_cards = list(getattr(free_facts, "cards", None) or [])
            body = RConv.render(
                pc, name=name, price=price, today=today, paid=paid,
                cards=fact_cards or shared_cards, prose=prose,
                footer_unlock=(not paid),
                remedy_html=_safe(_remedy, pc, name=first, paid=paid, price=price),
                analysis=(paid_facts if paid else free_facts))
            return _post_render_guard(_scrub(body, allowed_dates=allowed_dates))

        # Frozen non-LLM / classic path — untouched when conversational is used.
        present_html = ""
        if present_block is not None:
            try:
                import present_read as PR
                present_html = PR.render(present_block, paid=paid)
            except Exception as exc:                                 # noqa: BLE001
                print(f"[report_render] present render failed: {exc}", flush=True)
        remedy = _safe(_remedy, pc, name=first, paid=paid, price=price)
        if paid:
            dashboard_html = _safe(_promise_dashboard, shared_cards)
            tail = dashboard_html + timing_html + remedy
        else:
            tail = (remedy
                    + _locked_preview(price=price, n_areas=len(RC.AREAS),
                                      n_windows=n_windows, n_periods=n_periods)
                    + _bundle(bundle_price))
        body = RC.render(
            pc, name=name, price=price, today=today, paid=paid,
            question_html="",
            proof_html=present_html + past_html,
            timing_html=tail,
            cards=shared_cards,
            prose=prose,
            footer_unlock=(not paid))  # free view: bottom CTA; paid: none
        return _post_render_guard(_scrub(body, allowed_dates=allowed_dates))

    free_html, paid_html = build(False), build(True)
    meta = {
        "design": (
            "conversational-v1"
            if (
                bool(llm_meta.get("enabled"))
                and int(((llm_meta.get("paid") or {}).get("stats") or {}).get("accepted") or 0) > 0
                and bool((paid_prose_overlay or {}).get("conversational"))
            )
            else "cards-v2"
        ),
        "price": price, "bundlePrice": bundle_price,
        "llm": llm_meta,
        # Internal only — _save_report pops this into object storage as facts.json
        "_facts": facts_payload,
        "freeSections": ["Your current chapter", "Who your chart says you are",
                         "Your recent past — free and checkable",
                         "What is happening right now",
                         "Major life areas",
                         "Gemstones you should not wear"],
        "paidSections": ["Why each life area reads the way it does",
                         "Exact dates for every life area",
                         "How this area changes over time",
                         "Planets involved",
                         "Your strongest upcoming windows",
                         "The full period sequence",
                         "What helps, per area",
                         "Remedies and suitable gemstones"],
        "teasers": {},
    }
    return free_html, paid_html, meta


def _promise_dashboard(cards: list) -> str:
    import promise_dashboard as PD
    return PD.render(cards)


def _remedy(pc: dict, *, name: str = "", paid: bool = False,
            price: int = 298) -> str:
    import remedy_block as RB
    return RB.render(
        RB.build(pc, domain="", name=name), paid=paid, price=price,
        lede="For the areas that need more care, the traditional approach is to "
             "support them through practical habits, mantra, charity and — where "
             "appropriate — gemstones. Some charts also indicate that a commonly "
             "recommended stone may not be suitable. That distinction is included "
             "here because gemstones should be considered from the individual chart.")


def _locked_preview(*, price: int, n_areas: int, n_windows: int,
                    n_periods: int) -> str:
    """Free view: the paid depth, titled and blurred, with the buy CTA.

    Each paid section keeps its real heading from the full report but its body
    is a blurred, non-personal placeholder — the free path never has the real
    paid content in memory, so nothing here can be unpicked from the HTML. The
    single unlock CTA comes from ``report_cards``' footer block.
    """
    windows_teaser = (
        f"{n_windows} dated window{'s' if n_windows != 1 else ''} "
        "across the next five years."
        if n_windows else
        "The strongest windows across the next five years.")
    periods_teaser = (
        f"{n_periods} period{'s' if n_periods != 1 else ''} with real dates."
        if n_periods else
        "Your own timing sequence, with real dates.")
    rows = [
        ("Why each area reads the way it does",
         f"The chart working behind all {n_areas} headlines — the houses, the "
         "planets and the periods that shape them."),
        ("The dated window for every life area",
         "When each part of your life actually moves, against the period you "
         "are in."),
        ("Your strongest upcoming windows", windows_teaser),
        ("The full period sequence", periods_teaser),
        ("What helps in each area",
         "The practical step and mantra where one applies."),
        ("Every gemstone that suits you",
         "Metal, finger and the day to begin."),
    ]
    return RS.lock_sections(rows)


def _bundle(bundle_price: int) -> str:
    """Shown only in the free view. Bundle unlock is quote-only via email."""
    _ = bundle_price  # fixed button pricing; bundle is hand-quoted
    return """
<section class="card" style="background:#16181d;color:#f7f5f1;border:0">
  <div class="ev-label" style="color:#c9a227">Everything, one package</div>
  <h3 style="font-family:Fraunces,serif;font-size:1.3rem;margin:8px 0 8px">
    Want the full bundle for your family?</h3>
  <p style="margin:0 0 10px;font-size:.9rem;opacity:.85">The complete set —
  full chart reading, birth-time rectification, kundali matching, palm reading,
  numerology, questions, daily readings and remedies — is arranged by hand.
  Write to us and we will set it up for you.</p>
  <p style="margin:0 0 14px;font-size:.9rem">
    <a href="mailto:admin@graharekha.co.in"
       style="color:#f4d79b;font-weight:600;text-decoration:underline">
      admin@graharekha.co.in</a></p>
  <p style="margin:0;font-size:.78rem;opacity:.6">If your birth time is
  uncertain, start with birth-time rectification — every other reading is built
  on it.</p>
</section>"""


# ---------------------------------------------------------------------------
# horary — one answer, not two engines arguing
# ---------------------------------------------------------------------------
def horary(*, question: str, verdicts: dict, western_judgment: dict,
           asked: str, name: str = "", horary_price: int = 298,
           full_report_price: int = 298,
           vedic_customer: Optional[dict] = None) -> tuple:
    from horary_answer import build_answer_html, reconcile
    prose_overlay: dict = {}
    llm_meta: dict = {"enabled": False}
    facts_payload: dict = {}
    try:
        from llm.facts import build_horary_facts, project_for_access, public_fact_payload
        from llm.humanize import humanize
        summary_preview = reconcile(verdicts)
        hfacts_paid = build_horary_facts(
            question=question, verdicts=verdicts,
            summary=summary_preview, name=name, access="paid",
            western_judgment=western_judgment,
            vedic_customer=vedic_customer)
        hfacts_free = project_for_access(hfacts_paid, "free")
        facts_payload = public_fact_payload(hfacts_paid)
        free_llm = humanize("horary", hfacts_free, access="free")
        paid_llm = humanize("horary", hfacts_paid, access="paid")
        prose_overlay = {
            "free": free_llm.get("overlay") or {},
            "paid": paid_llm.get("overlay") or {},
        }
        llm_meta = {
            "enabled": bool(paid_llm.get("enabled") or free_llm.get("enabled")),
            "stats": paid_llm.get("stats") or {},
            "free": {"stats": free_llm.get("stats") or {},
                     "fallback_used": bool(free_llm.get("fallback_used"))},
            "paid": {"stats": paid_llm.get("stats") or {},
                     "fallback_used": bool(paid_llm.get("fallback_used"))},
        }
    except Exception as exc:                                         # noqa: BLE001
        print(f"[report_render] horary llm skipped: {exc}", flush=True)

    common = dict(question=question, verdicts=verdicts,
                  western_judgment=western_judgment, asked=asked, name=name,
                  horary_price=horary_price, full_report_price=full_report_price,
                  vedic_customer=vedic_customer)
    free_body, _ = build_answer_html(**common, paid=False,
                                     prose=(prose_overlay.get("free", {})
                                            if isinstance(prose_overlay, dict) else {}))
    paid_body, answer = build_answer_html(**common, paid=True,
                                          prose=(prose_overlay.get("paid", {})
                                                 if isinstance(prose_overlay, dict) else {}))

    # No shell heading: build_answer_html already opens with the question and
    # when it was asked. Passing them again printed the question twice.
    # Voice polish strips machinery (python paths, MiniLM, rebuild notes) and
    # keeps the tone consistent with every other customer report.
    free = RS.page(f"Your question — {question[:60]}",
                   _scrub(_voice_polish(free_body)))
    paid = RS.page(f"Your question — {question[:60]}",
                   _scrub(_voice_polish(paid_body)))
    meta = {"design": "cards-v2", "answer": answer, "question": question,
            "asked": asked, "price": horary_price,
            "llm": llm_meta,
            "_facts": facts_payload,
            "freeSections": ["Question & moment chart context",
                             "Preview of locked consultation verdict & timeline"],
            "paidSections": ["The verdict — unified planetary confluence",
                             "Planetary dynamics & supporting influences",
                             "Key timing & dated windows",
                             "Targeted remedies & immediate relief"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# user question — natal chart, half free (working) / paid (verdict + dates + remedy)
# ---------------------------------------------------------------------------
def user_question(pc: dict, *, question: str, route: Any = None, name: str = "",
                  price: int = 298, lat: float = 0.0, lon: float = 0.0,
                  tz: float = 5.5, today: Optional[date] = None,
                  area: str = "") -> tuple:
    """Renders comprehensive, unified Vedic Consultation report for ANY life question."""
    today = today or date.today()
    first = (name or "").split()[0] if name else ""

    from confluence_question_engine import (
        analyze_question_confluence,
        render_confluence_card_html,
        synthesize_with_qwen,
    )

    conf = analyze_question_confluence(pc, question, domain_override=area)
    qwen_consultation = synthesize_with_qwen(conf)

    free_body = _voice_polish(render_confluence_card_html(conf, paid=False, qwen_text=""))
    paid_body = _voice_polish(render_confluence_card_html(conf, paid=True, qwen_text=qwen_consultation))

    title = f"Your Question — {question[:60]}"
    free = RS.page(title, _scrub(free_body))
    paid = RS.page(title, _scrub(paid_body))

    meta = {
        "design": "cards-v2",
        "answer": {
            "label": conf.classical_verdict[:80],
            "confidence": "high",
            "direction": "caution" if conf.is_lord_in_dusthana else "support",
            "breakthrough": conf.breakthrough_period,
        },
        "question": question,
        "area": conf.domain_title,
        "price": price,
        "llm": {"enabled": bool(qwen_consultation)},
        "_facts": {
            "question": question,
            "domain": conf.domain_title,
            "lagna": conf.lagna,
            "primary_house": conf.primary_house,
            "primary_lord": conf.primary_house_lord,
            "breakthrough_period": conf.breakthrough_period,
        },
        "freeSections": ["Question & Vedic Core Verdict", "Preview of Locked Upaya & Timeline"],
        "paidSections": [
            "Classical Astrological Verdict",
            "Deep Jyotish Consultation Reading",
            "Planetary Dynamics & Divisional Indicators",
            "Dasha Timeline & Key Milestones",
            "Targeted Vedic Upaya & Actionable Guidance"
        ],
        "teasers": {}
    }
    return free, paid, meta


# ---------------------------------------------------------------------------
# numerology — every number and its verdict free, the working behind them paid
# ---------------------------------------------------------------------------
def _as_date(v) -> date:
    """Handlers pass dob as an ISO string; the numerology maths needs a date."""
    if isinstance(v, date):
        return v
    y, m, d = (int(x) for x in str(v)[:10].split("-"))
    return date(y, m, d)


NUMEROLOGY_FREE_SECTIONS = (
    "Name harmony diagnosis and vibration assessment",
    "Your six core numbers (Life Path, Birth Day, Expression, Soul Urge, Personality, Chaldean root)",
    "Lo Shu magic square and missing cell analysis",
    "Current 45-year Mahadasha chapter & annual cycle",
)
NUMEROLOGY_PAID_SECTIONS = (
    "Suggested name corrections & tested lucky spellings",
    "Targeted remedies for each empty Lo Shu cell",
    "The next three birthday years forecast with transition dates",
    "Complete step-by-step mathematical derivations (Pinnacles, Challenges, Maturity)",
)


def _numerology_teaser(c: dict, pos: dict, h: dict, n_missing: int) -> str:
    """Shown on the site's pay card, so it has to stand on its own."""
    bits = [f"how each of your six numbers was built",
            f"your {pos['maha']['planet']} chapter with dates"]
    if n_missing:
        bits.append(f"a remedy for each of your {n_missing} empty Lo Shu cells")
    else:
        bits.append("the remedy for the period you are running")
    bits.append("spellings that would fix your name number"
                if h.get("needs_remedy") else "the name-correction working")
    return ("Every number and its meaning is free. The full reading adds "
            + ", ".join(bits[:-1]) + " and " + bits[-1] + ".")


def numerology(name: str, dob, *, today: Optional[date] = None,
               price: int = 298) -> tuple:
    import numerology_cards as NC
    import numerology_report as NR
    dob = _as_date(dob)
    today = today or date.today()

    pre = NC.build(name, dob, today=today)
    c, pos, h = pre
    missing, _raw, _pillar = NR._effective_grid_missing(c)

    def render(paid: bool) -> str:
        return _scrub(NC.render(name, dob, paid=paid, price=price,
                                today=today, precomputed=pre))

    free, paid = render(False), render(True)
    meta = {"design": "cards-v2", "price": price,
            "teaser": _numerology_teaser(c, pos, h, len(missing)),
            "freeSections": list(NUMEROLOGY_FREE_SECTIONS),
            "paidSections": list(NUMEROLOGY_PAID_SECTIONS),
            "emptyCells": len(missing),
            "nameAlignment": h["alignment"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# kundali matching
# ---------------------------------------------------------------------------
def kundali_match(match_meta: dict, *, groom: str = "", bride: str = "",
                  price: int = 298) -> tuple:
    import tab_renderers as TR

    def build(paid: bool) -> str:
        body = TR.render_match(match_meta, groom=groom, bride=bride, paid=paid,
                               price=price)
        # render_match prints its own couple header and score hero.
        return _scrub(RS.page(f"{groom} & {bride} — compatibility", body))

    free, paid = build(False), build(True)
    meta = {"design": "cards-v2", "price": price,
            "paidSections": ["Each dosha and what waives it",
                             "The Navamsha (D9) synastry",
                             "Remedies for the blocking doshas"],
            "teasers": {}}
    return free, paid, meta


# ---------------------------------------------------------------------------
# daily — verdict free every morning, the working behind it on subscription
# ---------------------------------------------------------------------------
DAILY_FREE_SECTIONS = (
    "Today's verdict & emotional climate",
    "Your lucky number and day colour",
    "Primary action (Do) and pitfall to avoid (Don't)",
    "Preview of locked precision clock windows & transit workings",
)
DAILY_PAID_SECTIONS = (
    "Precision Auspicious Hours & Rahu Kaal Avoid Times",
    "Your Personal Moon Transit & Ashtakavarga Score (/56)",
    "Full Action Guide — 3 Personalized Dos & 3 Don'ts",
    "Vimshottari Dasha & Pratyantardasha Sub-Clock",
    "The 9-Lane Confluence Matrix",
    "Moonology Phase Ritual & Journaling Prompt",
)


def _daily_teaser(reading: dict, n_lanes: int) -> str:
    """Shown on the site's subscribe card, so it has to stand on its own."""
    d = (reading or {}).get("dasha") or {}
    stack = "-".join(x for x in (d.get("md"), d.get("ad"), d.get("pd")) if x)
    parts = []
    if n_lanes:
        parts.append(f"all {n_lanes} lanes that voted on today")
    if stack:
        parts.append(f"the {stack} period you are running, with its dates")
    parts.append("the Ashtakavarga bindus under your dasha lords")
    parts.append("today's Rahu Kaal and choghadiya")
    return ("Today's verdict is yours free. The subscription opens "
            + ", ".join(parts[:-1]) + " and " + parts[-1] + " — every morning.")


def daily(reading: dict, *, lat: float = 25.6, lon: float = 85.1,
          tz: float = 5.5, day: Optional[date] = None, name: str = "",
          price: int = 298, pc: Optional[dict] = None) -> tuple:
    import daily_card as DC
    day = day or date.today()
    reading = reading or {}

    def build(paid: bool) -> str:
        return _scrub(DC.render(reading, name=name, day=day, lat=lat, lon=lon,
                                tz=tz, paid=paid, price=price, pc=pc))

    free, paid_html = build(False), build(True)
    lanes = [x for x in ((reading.get("vedic_confluence") or {}).get("lanes") or [])
             if x.get("signal")]
    meta = {"design": "cards-v2", "price": price, "date": day.isoformat(),
            "teaser": _daily_teaser(reading, len(lanes)),
            "freeSections": list(DAILY_FREE_SECTIONS),
            "paidSections": list(DAILY_PAID_SECTIONS),
            "laneCount": len(lanes),
            "teasers": {}}
    return free, paid_html, meta


# ---------------------------------------------------------------------------
# birth-time check
# ---------------------------------------------------------------------------
def btr(res: dict, *, price: int = 298) -> tuple:
    import tab_renderers as TR

    def build(paid: bool) -> str:
        body = TR.render_btr(res, paid=paid, price=price)
        return _scrub(RS.page("Birth-time check", body))

    free, paid_html = build(False), build(True)
    meta = {"design": "cards-v2", "price": price,
            "skipped": bool(res.get("skipped")),
            "reason": res.get("reason"),
            "paidSections": ["The exact rectified time, to the second",
                             "Your corrected rising sign and divisional charts",
                             "How each life event scored against it",
                             "The full ±90 minute scan and the fine refinement"],
            "teasers": {}}
    return free, paid_html, meta


# ---------------------------------------------------------------------------
# muhurat — day verdict free; checks, hours, alternatives paid
# ---------------------------------------------------------------------------
def muhurat(summary: dict, detail: Optional[dict] = None, *,
            price: int = 298, event_id: str = "", date_str: str = "") -> tuple:
    import tab_renderers as TR
    detail = detail or {}
    summary = summary or {}

    def build(paid: bool) -> str:
        body = TR.render_muhurat(
            summary, detail if paid else {},
            paid=paid, price=price, event_id=event_id, date_str=date_str)
        label = summary.get("event_label") or event_id or "Muhurat"
        return _scrub(RS.page(f"{label} — {date_str or summary.get('target_date') or ''}",
                              body))

    free, paid_html = build(False), build(True)
    n_alt = summary.get("alternativeCount")
    if n_alt is None:
        n_alt = len(detail.get("alternatives") or [])
    meta = {"design": "cards-v2", "price": price,
            "verdict": summary.get("verdict"),
            "eventId": event_id,
            "date": date_str or summary.get("target_date"),
            "paidSections": ["Every panchang check on the day, pass or fail",
                             "The strong hours — choghadiya, Abhijit, and what to avoid",
                             "Chart-specific notes for this occasion",
                             f"{n_alt} better dates near yours"],
            "teasers": {}}
    return free, paid_html, meta
