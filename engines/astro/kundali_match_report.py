#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTML report for kundali matching."""
from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path
from typing import Any

try:
    from client_report_html import finalize_report_html
except Exception:  # pragma: no cover
    finalize_report_html = lambda h, client_name="": h  # noqa: E731


def _e(s: Any) -> str:
    return escape(str(s) if s is not None else "")


def _adv_verdict_tag(verdict: str) -> str:
    cls = {"recommend": "yes", "reject": "no", "caution": "warn"}.get(verdict, "warn")
    label = {"recommend": "RECOMMEND", "reject": "REJECT", "caution": "CAUTION"}.get(
        verdict, verdict.upper()
    )
    return f'<span class="tag {cls}">{_e(label)}</span>'


def _render_advanced_numerology(advanced: dict[str, Any]) -> str:
    if not advanced.get("available"):
        return ""

    g = advanced.get("groom") or {}
    b = advanced.get("bride") or {}
    enm = advanced.get("psychic_enmity") or {}
    pc = advanced.get("plane_couple") or {}
    dec = advanced.get("decision") or {}

    def plane_rows(person: dict) -> str:
        rows = ""
        for key in ("spiritual", "emotional", "physical"):
            p = (person.get("planes") or {}).get(key) or {}
            rows += (
                f"<tr><td>{_e(p.get('label'))}</td>"
                f"<td>{_e(', '.join(map(str, p.get('present') or [])) or 'none')}</td>"
                f"<td>{_e(p.get('strength_label'))}</td></tr>"
            )
        return rows

    step_rows = ""
    for s in dec.get("steps") or []:
        mark = "PASS" if s.get("pass") else "FLAG"
        step_rows += (
            f"<tr><td>{_e(s.get('step'))}</td><td>{_e(s.get('name'))}</td>"
            f"<td>{mark}</td><td>{_e(s.get('detail'))}</td></tr>"
        )

    remedy_html = ""
    for block in advanced.get("remedies") or []:
        steps = "".join(f"<li>{_e(x)}</li>" for x in (block.get("steps") or []))
        remedy_html += (
            f"<p><strong>{_e(block.get('for'))}</strong> "
            f"<span class=\"fine\">({_e(block.get('type'))})</span></p><ul>{steps}</ul>"
        )

    def adverse_list(person: dict, role: str) -> str:
        adv = person.get("adverse") or {}
        hi = adv.get("higher") or []
        lo = adv.get("lower") or []
        if not hi and not lo:
            return f"<p class=\"fine\">{role}: no adverse clusters flagged.</p>"
        parts = []
        if hi:
            parts.append("higher " + "; ".join("-".join(map(str, c)) for c in hi))
        if lo:
            parts.append("lower " + "; ".join("-".join(map(str, c)) for c in lo))
        return f"<p class=\"fine\"><strong>{role}:</strong> {_e(' | '.join(parts))}</p>"

    return f"""<div class="card">
<h2>Layer 5 - Advanced numerology marriage protocol (7-phase)</h2>
<p>{_adv_verdict_tag(dec.get('verdict', 'caution'))} {_e(dec.get('headline', ''))}</p>

<h3>Phase I-II - Psychic numbers (Moolank) and enmity</h3>
<table>
<tr><th>Person</th><th>Psychic</th><th>Planet</th><th>Traits</th></tr>
<tr><td>Groom</td><td>{_e(g.get('psychic'))}</td><td>{_e(g.get('psychic_planet'))}</td><td>{_e(g.get('psychic_traits'))}</td></tr>
<tr><td>Bride</td><td>{_e(b.get('psychic'))}</td><td>{_e(b.get('psychic_planet'))}</td><td>{_e(b.get('psychic_traits'))}</td></tr>
</table>
<p><strong>Psychic enmity:</strong> {'Yes' if enm.get('anemical') else 'No'} - {_e(enm.get('detail', ''))}</p>

<h3>Phase III - Destiny paths (Bhagyank)</h3>
<table>
<tr><th>Person</th><th>Destiny</th><th>Trajectory</th><th>Note</th></tr>
<tr><td>Groom</td><td>{_e(g.get('destiny'))}</td><td>{_e(g.get('destiny_band'))}</td><td>{_e(g.get('destiny_note'))}</td></tr>
<tr><td>Bride</td><td>{_e(b.get('destiny'))}</td><td>{_e(b.get('destiny_band'))}</td><td>{_e(b.get('destiny_note'))}</td></tr>
</table>

<h3>Phase IV - Seferal grid planes</h3>
<p class="fine">Grid digits present - groom: {_e(', '.join(map(str, g.get('seferal_digits') or [])))}; bride: {_e(', '.join(map(str, b.get('seferal_digits') or [])))}</p>
<table>
<tr><th>Plane</th><th>Groom present</th><th>Groom strength</th></tr>
{plane_rows(g)}
</table>
<table>
<tr><th>Plane</th><th>Bride present</th><th>Bride strength</th></tr>
{plane_rows(b)}
</table>
<p class="fine"><strong>Common empty planes:</strong> {_e(', '.join(pc.get('common_empty') or []) or 'none')}</p>
<ul class="fine">{''.join(f'<li>{_e(p)}</li>' for p in (pc.get('polarities') or []))}</ul>

<h3>Phase V - Adverse marital indicators</h3>
{adverse_list(g, 'Groom')}
{adverse_list(b, 'Bride')}

<h3>Phase VI - 5-step decision framework</h3>
<table>
<tr><th>Step</th><th>Check</th><th>Result</th><th>Detail</th></tr>
{step_rows}
</table>

<h3>Phase VII - Strategic remediation</h3>
{remedy_html or '<p class="fine">No specific cross-correction required.</p>'}
</div>"""


def _tag(verdict: str) -> str:
    cls = {"yes": "yes", "no": "no", "caution": "warn"}.get(verdict, "warn")
    label = {"yes": "FAVOURABLE", "no": "NOT RECOMMENDED", "caution": "CAUTION"}.get(verdict, verdict.upper())
    return f'<span class="tag {cls}">{_e(label)}</span>'


def write_kundali_match_report(
    *,
    result: dict[str, Any],
    groom_meta: dict[str, str],
    bride_meta: dict[str, str],
    out_path: Path,
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    v = result.get("verdict") or {}
    ak = result.get("ashtakoota") or {}
    doshas = result.get("doshas") or {}
    goel = result.get("goel_synastry") or {}
    manglik = result.get("manglik") or {}
    remissions = result.get("remissions") or []
    remedies = result.get("remedies") or []

    koot_rows = ""
    for k in ak.get("koots") or []:
        mark = "OK" if k.get("ok") else "LOW"
        koot_rows += (
            f"<tr><td>{_e(k.get('label'))}</td>"
            f"<td>{_e(k.get('score'))} / {_e(k.get('max'))}</td>"
            f"<td>{mark}</td></tr>"
        )

    dosha_rows = ""
    for d in doshas.get("items") or []:
        st = "waived" if d.get("waived") else ("active" if d.get("active") else "clear")
        dosha_rows += (
            f"<tr><td>{_e(d.get('name'))}</td><td>{_e(st)}</td>"
            f"<td>{_e(d.get('detail'))}</td></tr>"
        )

    rem_rows = ""
    for r in remissions:
        st = "yes" if r.get("remission_applies") else "no"
        rem_rows += (
            f"<tr><td>{_e(r.get('dosha'))}</td><td>{_e(st)}</td>"
            f"<td>{_e(r.get('detail'))}</td></tr>"
        )

    rem_html = ""
    if rem_rows:
        rem_html = f"""<div class="card">
<h2>Remissions (Bhardwaj rules37 p.168-169)</h2>
<p class="fine">Scriptures allow half-guna credit when remission applies; shanti is still advised.</p>
<table><tr><th>Item</th><th>Remission</th><th>Detail</th></tr>{rem_rows}</table>
</div>"""

    remedy_html = ""
    for block in remedies:
        steps = "".join(f"<li>{_e(s)}</li>" for s in (block.get("steps") or []))
        remedy_html += (
            f'<p><strong>{_e(block.get("for"))}</strong> '
            f'<span class="fine">({_e(block.get("source"))})</span></p><ul>{steps}</ul>'
        )

    goel_rows = ""
    for c in goel.get("checks") or []:
        mark = "OK" if c.get("ok") else "MISS"
        goel_rows += (
            f"<tr><td>{mark}</td><td>{_e(c.get('name'))}</td><td>{_e(c.get('detail'))}</td></tr>"
        )

    d9c = result.get("d9_compatibility") or {}
    d9_html = ""
    if d9c.get("available"):
        d9_rows = ""
        for c in d9c.get("checks") or []:
            mark = "OK" if c.get("ok") else "MISS"
            d9_rows += (
                f"<tr><td>{mark}</td><td>{_e(c.get('name'))}</td><td>{_e(c.get('detail'))}</td></tr>"
            )
        d9_tag = {"strong": "yes", "mixed": "warn", "weak": "no"}.get(d9c.get("verdict"), "warn")
        d9_html = f"""<div class="card">
<h2>Layer 3b - Navamsha (D9) marriage compatibility</h2>
<p><span class="tag {d9_tag}">{_e((d9c.get('verdict') or '').upper())}</span> {_e(d9c.get('headline', ''))}</p>
<p class="fine">The D9 is the primary chart of marriage. Groom D9 lagna <strong>{_e(d9c.get('groom_d9_lagna'))}</strong>
(lord {_e(d9c.get('groom_d9_lagna_lord'))}) - bride D9 lagna <strong>{_e(d9c.get('bride_d9_lagna'))}</strong>
(lord {_e(d9c.get('bride_d9_lagna_lord'))}). Passed {_e(d9c.get('passed'))} / {_e(d9c.get('total'))} checks
({_e(d9c.get('score_pct'))}%).</p>
<table><tr><th></th><th>D9 check</th><th>Detail</th></tr>{d9_rows}</table>
<p class="fine">Reads each partner's 7th house, 7th lord and marriage karaka (Venus for groom, Jupiter for bride),
then overlays each D9 onto the other for relational harmony.</p>
</div>"""

    num = result.get("numerology") or {}
    num_html = ""
    if num.get("available"):
        gnum = num.get("groom") or {}
        bnum = num.get("bride") or {}
        lp = num.get("life_path_compat") or {}
        su = num.get("soul_urge_compat") or {}
        av = num.get("avasthi") or {}
        rel = num.get("relationship_number") or {}
        nver = num.get("verdict") or {}
        tips = (num.get("partner_tips") or {}).get("tips") or []
        tip_items = "".join(f"<li>{_e(t)}</li>" for t in tips)
        warn = num.get("warnings") or []
        warn_html = ""
        if warn:
            warn_html = "<p class=\"fine\">" + " ".join(_e(w) for w in warn) + "</p>"
        av_lp = av.get("life_path") or {}
        av_su = av.get("soul_urge") or {}
        num_html = f"""<div class="card">
<h2>Layer 4 - Numerology marriage compatibility</h2>
<p class="fine">{_e(nver.get('headline', ''))}</p>
<table>
<tr><th>Person</th><th>Life path</th><th>Birth-day</th><th>Expression</th><th>Soul urge</th><th>Chaldean name</th><th>LP group</th></tr>
<tr><td>Groom</td><td>{_e(gnum.get('life_path'))}</td><td>{_e(gnum.get('birth_day'))}</td><td>{_e(gnum.get('expression'))}</td><td>{_e(gnum.get('soul_urge'))}</td><td>{_e(gnum.get('chaldean_root'))}</td><td>{_e(gnum.get('avasthi_lp_group'))}</td></tr>
<tr><td>Bride</td><td>{_e(bnum.get('life_path'))}</td><td>{_e(bnum.get('birth_day'))}</td><td>{_e(bnum.get('expression'))}</td><td>{_e(bnum.get('soul_urge'))}</td><td>{_e(bnum.get('chaldean_root'))}</td><td>{_e(bnum.get('avasthi_lp_group'))}</td></tr>
</table>
<p><strong>Life Path:</strong> {_e(lp.get('label'))} - groom LP {_e(lp.get('groom_lp'))} x bride LP {_e(lp.get('bride_lp'))}</p>
<p><strong>Soul Urge:</strong> {_e(su.get('label'))} - groom SU {_e(su.get('groom_su'))} x bride SU {_e(su.get('bride_su'))}</p>
<p><strong>Triads:</strong> LP {_e(av_lp.get('note', ''))}</p>
<p><strong>Soul-urge notes:</strong> {_e(av_su.get('note', ''))}</p>
<p><strong>Relationship number {_e(rel.get('number'))}:</strong> {_e(rel.get('text', ''))}</p>
<p class="fine">Formula: {_e(rel.get('formula', ''))}</p>
{warn_html}
<p><strong>Working with bride Destiny {_e((num.get('partner_tips') or {}).get('destiny_number'))}:</strong></p>
<ul>{tip_items}</ul>
<p class="fine">Numerology is one lane - not a sole determinant. Use full legal / day-to-day names for best letter math.</p>
</div>"""

        adv = num.get("advanced") or {}
        num_html += _render_advanced_numerology(adv)

    extra = ak.get("extra_porutham") or {}
    extra_bits = ", ".join(
        f"{k}: {'yes' if v else 'no'}" for k, v in extra.items()
    )

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>Kundali Match - {_e(groom_meta.get('name'))} &amp; {_e(bride_meta.get('name'))}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;background:#0f1117;color:#e8e8e8}}
h1{{color:#f0c674}} h2{{color:#7ec8e3;margin-top:28px;font-size:1.1rem}}
.card{{background:#1a1d29;border:1px solid #333;border-radius:10px;padding:16px;margin:14px 0}}
.tag{{display:inline-block;padding:4px 12px;border-radius:6px;font-size:.85rem;font-weight:600}}
.yes{{background:#1e4d2b;color:#9fdf9f}}.no{{background:#4d1e1e;color:#f0a0a0}}.warn{{background:#4d3f1e;color:#f0d090}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
td,th{{padding:8px;border-bottom:1px solid #333;text-align:left;vertical-align:top}}
.fine{{color:#999;font-size:.88rem}}
.score{{font-size:1.6rem;font-weight:700;color:#f0c674}}
</style></head><body>
<h1>Kundali Milan - Marriage Compatibility</h1>
<p class="fine">Report date: {_e(date.today().isoformat())} - Method: {_e(ak.get('method', 'North'))}</p>
<p><strong>Groom:</strong> {_e(groom_meta.get('name'))} - {_e(groom_meta.get('dob'))} {_e(groom_meta.get('tob'))} - {_e(groom_meta.get('place'))}</p>
<p><strong>Bride:</strong> {_e(bride_meta.get('name'))} - {_e(bride_meta.get('dob'))} {_e(bride_meta.get('tob'))} - {_e(bride_meta.get('place'))}</p>

<div class="card">
<h2>Final verdict</h2>
<p>{_tag(v.get('verdict', 'caution'))} {_e(v.get('headline', ''))}</p>
<p class="score">{_e(ak.get('total_guna'))} / {_e(ak.get('max_guna', 36))} guns</p>
<p class="fine">{_e(ak.get('band_plain', ''))}</p>
</div>

<div class="card">
<h2>Layer 1 - Ashtakoota (36 Guna Milan)</h2>
<p class="fine">Moon nakshatra: groom <strong>{_e(ak.get('groom_nakshatra'))}</strong> pada {_e(ak.get('groom_pada'))} ({_e(ak.get('groom_moon_display', ak.get('groom_moon_sign')))}) -
bride <strong>{_e(ak.get('bride_nakshatra'))}</strong> pada {_e(ak.get('bride_pada'))} ({_e(ak.get('bride_moon_display', ak.get('bride_moon_sign')))})</p>
<p class="fine">Moon signs: groom {_e(ak.get('groom_moon_sign'))} - bride {_e(ak.get('bride_moon_sign'))}. Nakshatra is computed from exact birth time (PyJHora Lahiri); Hasta in Virgo begins near 10d 00m.</p>
<table>
<tr><th>Koot</th><th>Score</th><th></th></tr>
{koot_rows or '<tr><td colspan="3">South method - see porutham score above</td></tr>'}
</table>
<p class="fine">Supporting porutham: {_e(extra_bits)}</p>
</div>

<div class="card">
<h2>Layer 2 - Doshas (Bhardwaj rules37)</h2>
<table><tr><th>Dosha</th><th>Status</th><th>Note</th></tr>{dosha_rows}</table>
<p class="fine">Groom Manglik: {_e((manglik.get('groom') or {{}}).get('note', 'n/a'))}</p>
<p class="fine">Bride Manglik: {_e((manglik.get('bride') or {{}}).get('note', 'n/a'))}</p>
</div>

{rem_html}

<div class="card">
<h2>Remedies to overcome doshas</h2>
{remedy_html}
</div>

<div class="card">
<h2>Layer 3 - Goel Navamsha synastry (rules3 Ch.3)</h2>
<p class="fine">Passed {_e(goel.get('passed'))} / {_e(goel.get('total'))} checks ({_e(goel.get('score_pct'))}%)</p>
<table><tr><th></th><th>Check</th><th>Detail</th></tr>{goel_rows}</table>
</div>

{d9_html}

{num_html}

<p class="fine">{_e(result.get('audit_note', ''))}</p>
<p class="fine">Sources: {_e(result.get('sources', ''))}. Educational use - confluence with family pandit / muhurat for wedding date.</p>
</body></html>"""

    out_path.write_text(finalize_report_html(html), encoding="utf-8")
    return out_path
