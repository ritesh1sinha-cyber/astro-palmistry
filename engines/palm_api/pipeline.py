"""
palm_api.pipeline — callable entry points for the Vedic report generator (no HTTP).

Same analysis path as palm_api.app /api/analyze/both; writes lane HTML matching the
palm_api web UI (numbered checklist, confluence, book-backed points).
"""
from __future__ import annotations

import base64
import html
import re
import uuid
from datetime import date
from pathlib import Path
from typing import Any, Optional

from palm_api.analyzer import extract_features, features_for_json, save_overlay
from palm_api.confluence import build_confluence
from palm_api.engine import predict
from palm_api.reference import build_reference_text
from palm_api.report_links import enrich_checklist_with_predictions, linked_prediction_count
from palm_api.rules_builder import load_corpus, save_corpus

_corpus: dict[str, Any] | None = None

PALM_CATEGORY_TO_DOMAIN = {
    "career": "career",
    "vitality": "health",
    "heart": "marriage",
    "mind": "career",
    "fame": "career",
    "travel": "travel",
    "remedies": "health",
    "mounts": "personality",
    "fingers": "personality",
    "general": "personality",
}

AGREEMENT_BADGE = {
    "reinforced": "Reinforced (both hands)",
    "developed": "Developed beyond blueprint",
    "latent": "Innate strength, under-used",
    "one_hand": "Shows on one hand",
}


def ensure_corpus() -> dict[str, Any]:
    global _corpus
    if _corpus is None:
        from palm_api.paths import RULES_CORPUS
        if not RULES_CORPUS.is_file():
            save_corpus()
        _corpus = load_corpus()
    return _corpus


def _guess_hand(path: Path) -> str:
    n = path.name.lower()
    if re.search(r"\bleft\b|leftpalm|l_palm|_l\.|lhand", n):
        return "left"
    if re.search(r"\bright\b|rightpalm|r_palm|_r\.|rhand", n):
        return "right"
    return "unknown"


def _e(s) -> str:
    return html.escape(str(s))


def analyze_one(
    path: Path,
    hand: str,
    *,
    corpus: dict[str, Any],
    exclude_rule_ids: set[str] | None = None,
    overlay_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Single palm — same logic as palm_api.app._analyze_image."""
    feats = extract_features(path, hand=hand)
    if overlay_path:
        save_overlay(path, feats, overlay_path)
    clean = features_for_json(feats)
    pred = predict(clean, corpus=corpus, exclude_rule_ids=exclude_rule_ids)
    shape = feats.get("_warped_shape") or [400, 400]
    palm_size = int(max(shape))
    checklist = enrich_checklist_with_predictions(
        feats.get("numbered_checklist", []),
        pred,
        features=clean,
        line_groups=feats.get("_line_groups") or {},
        palm_size=palm_size,
        corpus=corpus,
        lines=clean.get("lines") or {},
    )
    pred["linked_quote_count"] = linked_prediction_count(checklist)
    return {
        "path": str(path),
        "features": clean,
        "numbered_checklist": checklist,
        "not_detected": feats.get("not_detected", []),
        "prediction": pred,
        "hand": hand,
        "overlay_path": str(overlay_path) if overlay_path else None,
    }


def analyze_image_paths(
    image_paths: list[str | Path],
    *,
    active_hand: str = "right",
    overlay_dir: Optional[Path] = None,
) -> dict[str, Any]:
    """Analyze one or two palm photos — same result shape as POST /api/analyze/both."""
    corpus = ensure_corpus()
    used: set[str] = set()
    ordered: list[tuple[str, Path]] = []
    unknown: list[Path] = []

    for raw in image_paths:
        p = Path(raw)
        if not p.is_file():
            continue
        h = _guess_hand(p)
        if h == "unknown":
            unknown.append(p)
        else:
            ordered.append((h, p))

    for i, p in enumerate(unknown):
        h = "right" if i == 0 and not any(x[0] == "right" for x in ordered) else "left"
        ordered.append((h, p))

    results: dict[str, Any] = {"active_hand": active_hand, "corpus_rules": corpus.get("rule_count", 0)}
    blocks_for_conf: dict[str, Any] = {}

    for hand, path in ordered:
        ov = None
        if overlay_dir:
            overlay_dir.mkdir(parents=True, exist_ok=True)
            ov = overlay_dir / f"Palmistry_{hand}_overlay.jpg"
        block = analyze_one(path, hand, corpus=corpus, exclude_rule_ids=used, overlay_path=ov)
        for p in block.get("prediction", {}).get("predictions", []):
            if p.get("id"):
                used.add(p["id"])
        results[hand] = block
        blocks_for_conf[hand] = block

    if results.get("right") and results.get("left"):
        results["confluence"] = build_confluence(blocks_for_conf, active_hand)

    results["reference_text"] = build_reference_text(blocks_for_conf if blocks_for_conf else results)
    return results


def signals_for_confluence(analysis: dict[str, Any]) -> list[dict[str, str]]:
    """Export palm_api analysis as confluence signal dicts."""
    out: list[dict[str, str]] = []
    conf = analysis.get("confluence") or {}
    if conf.get("summary"):
        out.append({"system": "Palmistry", "text": conf["summary"], "direction": "positive", "timing": "life chart"})
    for item in conf.get("lines") or []:
        out.append({
            "system": "Palmistry",
            "domain": "personality",
            "text": item.get("statement", ""),
            "direction": "positive",
            "timing": "life chart",
        })
    for hand_key in ("right", "left"):
        block = analysis.get(hand_key)
        if not block:
            continue
        for it in block.get("numbered_checklist") or []:
            conc = it.get("conclusive") or {}
            verdict = conc.get("verdict")
            if not verdict or len(verdict) < 40:
                continue
            title = (it.get("title") or "").lower()
            dom = "personality"
            for kw, d in (
                ("career", "career"), ("fate", "career"), ("heart", "marriage"), ("marriage", "marriage"),
                ("life", "health"), ("health", "health"), ("travel", "travel"), ("child", "children"),
            ):
                if kw in title:
                    dom = d
                    break
            timing = it.get("timing") or {}
            age = timing.get("estimated_age")
            out.append({
                "system": "Palmistry",
                "domain": dom,
                "text": verdict[:320],
                "direction": "caution" if re.search(r"\b(watch|risk|weak|broken)\b", verdict, re.I) else "positive",
                "timing": f"age ~{age}" if age else "life chart",
            })
    return out


def _img_src(overlay_path: Optional[str], embed: bool) -> str:
    if not overlay_path or not Path(overlay_path).is_file():
        return ""
    if embed:
        data = Path(overlay_path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"
    return Path(overlay_path).name


def _render_checklist(hand_data: dict[str, Any]) -> str:
    lst = hand_data.get("numbered_checklist") or []
    missing = hand_data.get("not_detected") or []
    q = hand_data.get("features", {}).get("quality") or {}
    html_out = ""
    if q.get("grade"):
        html_out += f'<p class="note">Photo quality: <strong>{_e(q["grade"])}</strong></p>'
    if not lst:
        return html_out + '<p class="callout-warn">No findings detected clearly enough to number.</p>'
    html_out += '<p class="note">Match each <strong>dot on your palm</strong> to the same <strong>Point N</strong> below.</p><ul class="numbered-checklist">'
    for it in lst:
        n = it.get("num", "?")
        on_palm = (
            f' <span class="note">(dot <strong>{n}</strong> on palm)</span>'
            if it.get("x") is not None
            else ' <span class="note">(whole hand)</span>'
        )
        conc = it.get("conclusive") or {}
        conc_html = ""
        if conc.get("verdict"):
            conc_html = (
                f'<div class="conclusive-block"><strong>Your reading — point {n}</strong>'
                f'<p class="verdict-line">{_e(conc["verdict"])}</p>'
            )
            if conc.get("conclusion"):
                conc_html += f'<p class="conclusion-line">{_e(conc["conclusion"])}</p>'
            conc_html += "</div>"
        timing = it.get("timing") or {}
        timing_html = ""
        if timing.get("estimated_age") is not None:
            age = timing["estimated_age"]
            rng = timing.get("age_range") or []
            if len(rng) == 2 and rng[1] > rng[0]:
                when = f"approximately <strong>{rng[0]}–{rng[1]}</strong> (around {age})"
            else:
                when = f"around age <strong>{age}</strong> (approximate)"
            timing_html = (
                f'<div class="timing-block"><strong>When on your palm:</strong> {when}</div>'
            )
        html_out += (
            f'<li class="check-item"><span class="palm-num">{n}</span><div class="check-body">'
            f'<strong>Point {n} — {_e(it.get("title", ""))}</strong>{on_palm}{timing_html}{conc_html}</div></li>'
        )
    html_out += "</ul>"
    if missing:
        html_out += f'<p class="note"><strong>Not on photo:</strong> {_e(", ".join(missing))}.</p>'
    return html_out


_ASPECT_STRENGTH_CLASS = {
    "strong": "aspect-strong",
    "moderate": "aspect-moderate",
    "tentative": "aspect-tentative",
}


def _render_life_aspects(aspects: Optional[list[dict[str, Any]]]) -> str:
    if not aspects:
        return ""
    cards = ""
    for a in aspects:
        scls = _ASPECT_STRENGTH_CLASS.get(a.get("strength", ""), "")
        badge = a.get("strength", "").title()
        rein = a.get("reinforced_count", 0)
        rein_badge = (
            f'<span class="badge">{rein} on both hands</span>' if rein else ""
        )
        cites = ""
        seen_q: set[str] = set()
        for p in a.get("points") or []:
            q = (p.get("quote") or "").strip()
            if not q or q in seen_q:
                continue
            seen_q.add(q)
            lbl = p.get("book_label") or ""
            pg = f" p{p['page']}" if p.get("page") else ""
            mark = " \u2713 both" if p.get("reinforced") else ""
            cites += (
                f'<li><span class="quote">&ldquo;{_e(q)}&rdquo;</span>'
                f'<span class="src">— {_e(lbl)}{_e(pg)}{mark}</span></li>'
            )
        cites_html = f'<ul class="aspect-cites">{cites}</ul>' if cites else ""
        cards += f"""
<div class="aspect-card {scls}">
  <h3>{_e(a.get('title',''))} <span class="aspect-strength">{_e(badge)}</span> {rein_badge}</h3>
  <p class="aspect-body">{_e(a.get('summary',''))}</p>
  <p class="fine">{_e(a.get('strength_note',''))}</p>
  {cites_html}
</div>"""
    return f"""
<article class="report-card" style="border-left:4px solid var(--magenta)">
  <h2>Your life, read by confluence</h2>
  <p class="lead">Like a human palmist, each area below combines several palm signs.
  Where signs agree — especially across both hands — the reading is stronger.</p>
  {cards}
</article>"""


def _render_confluence(c: Optional[dict[str, Any]]) -> str:
    if not c:
        return ""
    lines = "".join(
        f'<li class="check-item"><div class="check-body"><strong>{_e(li.get("title",""))}</strong>'
        f'<span class="badge">{_e(AGREEMENT_BADGE.get(li.get("agreement",""), li.get("agreement","")))}</span>'
        f'<p class="verdict-line">{_e(li.get("statement",""))}</p></div></li>'
        for li in c.get("lines") or []
    )
    mounts = ""
    if c.get("mounts"):
        mounts = "<h3>Mount confluence</h3><ul class=" + '"plain"' + ">" + "".join(
            f"<li>{_e(m.get('statement',''))}</li>" for m in c["mounts"]
        ) + "</ul>"
    marks = ""
    if c.get("marks"):
        marks = "<h3>Special marks</h3><ul class=" + '"plain"' + ">" + "".join(
            f"<li>{_e(m.get('statement',''))}</li>" for m in c["marks"]
        ) + "</ul>"
    pred_parts = []
    for p in c.get("predictions") or []:
        age_bit = f" — around age {_e(p['age'])}" if p.get("age") is not None else ""
        pred_parts.append(
            f'<div class="conclusive-block"><strong>{_e(p.get("title","Reading"))}{age_bit}</strong>'
            f'<p class="verdict-line">{_e(p.get("text",""))}</p></div>'
        )
    preds = "".join(pred_parts)
    return f"""
<article class="report-card" style="border-left:4px solid var(--accent)">
  <h2>Confluence reading — both hands combined</h2>
  <p class="lead">{_e(c.get("summary",""))}</p>
  <h3>Major lines (left + right synthesis)</h3>
  <ul class="check-list">{lines}</ul>
  {mounts}{marks}
  <h3>What this means for you</h3>
  {preds or '<p class="note">No clear timed prediction could be drawn.</p>'}
</article>"""


def render_lane_html(
    analysis: dict[str, Any],
    *,
    client_name: str = "Client",
    embed_overlays: bool = True,
    extra_sections_html: str = "",
    lead_sections_html: str = "",
) -> str:
    """HTML report using the same structure as palm_api/templates/index.html."""
    active = analysis.get("active_hand", "right")
    today = date.today().isoformat()
    primary = analysis.get(active) or analysis.get("right") or analysis.get("left") or {}

    sections = ""
    for label, key in (("Right", "right"), ("Left", "left")):
        hand_data = analysis.get(key)
        if not hand_data:
            continue
        is_active = key == active
        badge = '<span class="badge">Dominant</span>' if is_active else (
            '<span style="font-size:0.85rem;color:var(--muted);font-weight:normal">— innate blueprint</span>'
        )
        src = _img_src(hand_data.get("overlay_path"), embed_overlays)
        img_html = ""
        if src:
            img_html = (
                f'<div style="max-width:22rem;margin:0.5rem 0 1rem">'
                f'<img src="{src}" alt="{label}" style="width:100%;border:1px solid var(--border);border-radius:4px" />'
                f'<p class="note" style="margin-top:0.35rem;text-align:center">Numbered dots match <strong>Point N</strong> below.</p></div>'
            )
        # Keep the marked-up palm photo visible; only the long numbered-point
        # list is collapsed by default so the report opens short.
        sections += f"""
<article class="report-card per-hand-detail">
  <h2>{label} palm {badge}</h2>
  {img_html}
  <details>
    <summary style="cursor:pointer;font-size:1.02rem;font-weight:600;color:var(--heading);list-style:none;padding:.2rem 0">
      Show the numbered palm points
    </summary>
    <h3>Your numbered palm points</h3>
    {_render_checklist(hand_data)}
  </details>
</article>"""

    conf = analysis.get("confluence") or {}
    aspects_section = _render_life_aspects(conf.get("life_aspects"))
    conf_section = _render_confluence(analysis.get("confluence"))

    # When a combined confluence leads the report, the palm-only sections become
    # the "detailed palmistry" block sitting under their own divider.
    palm_detail_hdr = (
        '<h2 class="section-divider" style="margin:2rem 0 .4rem;color:var(--muted);'
        'border-top:1px solid var(--border);padding-top:1.2rem">Section 1 — Your palms in detail</h2>'
        if lead_sections_html else ""
    )
    per_hand_hdr = '<h3 style="margin:1.5rem 0 0.5rem;color:var(--muted)">Per-hand detail</h3>' if conf_section else ""

    body = f"""
<div class="report-wrap">
  <article class="report-card">
    <h1 class="report-title">Palmistry analysis report</h1>
    <dl class="meta">
      <dt>Client</dt><dd>{_e(client_name)}</dd>
      <dt>Reading date</dt><dd>{today}</dd>
      <dt>Dominant hand</dt><dd>{_e(active.title())} — lived patterns. Other hand = innate wiring.</dd>
    </dl>
    <p class="lead">Each <strong>dot</strong> on your palm matches <strong>Point N</strong> in the report.</p>
  </article>
  {lead_sections_html}
  {palm_detail_hdr}
  {aspects_section}
  {conf_section}
  {per_hand_hdr}
  {sections}
  {extra_sections_html}
  <p class="note">For learning and reflection only — not medical diagnosis.</p>
</div>"""

    # CSS subset from palm_api index.html
    css = TEMPLATE_CSS
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Palmistry — {_e(client_name)}</title>
<style>{css}</style></head><body>{body}</body></html>"""


TEMPLATE_CSS = """
:root{--magenta:#b0106b;--heading:#0d47a1;--accent:#1b5e20;--text:#1a1a1a;--muted:#555;--bg:#f0f2f5;--card:#fff;--border:#dde2e8}
body{font-family:Georgia,serif;background:var(--bg);color:var(--text);line-height:1.55;margin:0;padding:1rem}
.report-wrap{max-width:52rem;margin:0 auto}
.report-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:1.5rem 1.75rem;box-shadow:0 2px 8px rgba(0,0,0,.06);margin-bottom:1.25rem}
.meta{color:var(--magenta);font-size:.95rem;margin-bottom:1rem}
.meta dt{font-weight:bold;margin-top:.35rem}.meta dd{margin:0}
h1.report-title{font-size:1.35rem;color:var(--heading);margin-bottom:.5rem}
h2{color:var(--heading);font-size:1.12rem;margin-top:1rem}
h3{font-size:1.02rem;color:var(--heading)}
.lead{font-size:1.05rem;margin-bottom:1rem}
.note{font-size:.85rem;color:var(--muted);margin-top:.5rem}
.badge{font-family:system-ui,sans-serif;display:inline-block;font-size:.7rem;background:var(--heading);color:#fff;padding:.15rem .45rem;border-radius:4px;margin-left:.35rem}
.numbered-checklist,.check-list,.plain{list-style:none;padding:0}
.check-item{display:flex;gap:.75rem;margin:.85rem 0;align-items:flex-start}
.palm-num{font-family:system-ui,sans-serif;font-weight:700;color:#fff;background:var(--heading);min-width:2rem;height:2rem;line-height:2rem;text-align:center;border-radius:50%;font-size:.85rem}
.conclusive-block{background:#f5f9ff;border-left:3px solid var(--heading);padding:.6rem .85rem;margin:.5rem 0}
.verdict-line{margin:.35rem 0;font-size:.95rem}
.conclusion-line{font-size:.88rem;color:var(--muted);margin:.25rem 0 0}
.timing-block{font-size:.88rem;color:var(--accent);margin:.35rem 0}
.callout-warn{background:#fff3e0;border-left:4px solid #f9a825;padding:.75rem 1rem}
.aspect-card{border:1px solid var(--border);border-radius:8px;padding:.85rem 1.1rem;margin:.7rem 0;background:#fafbfc}
.aspect-card.aspect-strong{border-left:4px solid var(--accent)}
.aspect-card.aspect-moderate{border-left:4px solid #f9a825}
.aspect-card.aspect-tentative{border-left:4px solid var(--muted)}
.aspect-card h3{margin:.1rem 0 .4rem}
.aspect-strength{font-family:system-ui,sans-serif;font-size:.68rem;font-weight:700;color:#fff;background:var(--accent);padding:.1rem .4rem;border-radius:4px;vertical-align:middle}
.aspect-body{margin:.3rem 0;font-size:.97rem}
.aspect-cites{list-style:none;padding:.4rem 0 0;margin:.4rem 0 0;border-top:1px dashed var(--border)}
.aspect-cites li{margin:.3rem 0;font-size:.82rem}
.aspect-cites .quote{color:var(--text);font-style:italic}
.aspect-cites .src{color:var(--magenta);margin-left:.3rem;font-style:normal}
.fine{font-size:.8rem;color:var(--muted);margin:.25rem 0}
"""


def generate_lane_report(
    image_paths: list[str | Path],
    out_html_path: Path,
    *,
    client_name: str = "Client",
    active_hand: str = "right",
    embed_overlays: bool = True,
) -> dict[str, Any]:
    """One-call entry for astro_report_generator: analyze → write HTML → return analysis."""
    out_html_path = Path(out_html_path)
    overlay_dir = out_html_path.parent
    analysis = analyze_image_paths(image_paths, active_hand=active_hand, overlay_dir=overlay_dir)
    html_doc = render_lane_html(analysis, client_name=client_name, embed_overlays=embed_overlays)
    out_html_path.write_text(html_doc, encoding="utf-8")
    ref_path = overlay_dir / f"Palmistry_{out_html_path.stem}_reference.txt"
    ref_path.write_text(analysis.get("reference_text", ""), encoding="utf-8")
    return analysis
