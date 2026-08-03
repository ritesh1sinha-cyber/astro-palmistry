#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render a client-specific HTML report for the 108 predictive-technique rules.

Prediction-first: the rules that hit the user's chart are narrated as plain-English
predictions up top; a full colour-coded verdict table for all 108 rules follows.

Source book: "Saral Jyotish Part V – Astrology Simplified" (predictivetechnique.pdf),
108 chapters, each a distinct predictive rule.
"""
from __future__ import annotations

import html
from pathlib import Path

from prediction108_rules import evaluate_all, summarize, lagna, RuleVerdict
from prediction108_transit import attach_contexts

BASE_DIR = Path(__file__).resolve().parent

CAT_LABEL = {
    "natal": "Birth-chart rule",
    "transit": "Saturn/Jupiter transit rule",
    "annual": "Annual (Varshaphal) rule",
}

VERDICT_STYLE = {
    "HIT": ("hit", "✓ Hits your chart"),
    "PARTIAL": ("partial", "◐ Partly hits"),
    "NO": ("no", "— Not present"),
    "NA": ("na", "Needs transit/annual chart"),
}


def _esc(s: str) -> str:
    return html.escape(str(s or ""))


def _css() -> str:
    return """
:root{
  --bg:#0f1117; --card:#171a23; --card2:#1d212c; --ink:#e8eaf0; --mut:#9aa3b2;
  --line:#2a2f3c; --hit:#3ddc97; --hitbg:#10301f; --partial:#ffcf6b; --partbg:#332a10;
  --no:#5b6273; --na:#7aa2ff; --nabg:#15203b; --accent:#b693ff;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.6;font-size:16px}
.wrap{max-width:980px;margin:0 auto;padding:32px 20px 80px}
.hero{background:linear-gradient(135deg,#1b1f2b,#23192f);border:1px solid var(--line);
  border-radius:18px;padding:30px 28px;margin-bottom:26px}
.hero h1{margin:0 0 6px;font-size:27px;letter-spacing:.2px}
.hero .sub{color:var(--mut);font-size:15px}
.hero .meta{margin-top:16px;display:flex;flex-wrap:wrap;gap:10px}
.chip{background:#0d1019;border:1px solid var(--line);border-radius:999px;
  padding:6px 14px;font-size:13px;color:var(--mut)}
.chip b{color:var(--ink)}
.tally{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0 8px}
.tally .t{flex:1;min-width:120px;background:var(--card);border:1px solid var(--line);
  border-radius:14px;padding:14px 16px;text-align:center}
.tally .t .n{font-size:26px;font-weight:700}
.tally .t .l{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.6px}
.t.hit .n{color:var(--hit)} .t.partial .n{color:var(--partial)}
.t.no .n{color:#aeb4c2} .t.na .n{color:var(--na)}
h2{margin:38px 0 14px;font-size:21px;border-left:4px solid var(--accent);padding-left:12px}
.lead{color:var(--mut);margin:-6px 0 18px;font-size:14.5px}
.cards{display:grid;gap:14px}
.card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--hit);
  border-radius:14px;padding:16px 18px}
.card.partial{border-left-color:var(--partial)}
.card .top{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:6px}
.card .title{font-weight:650;font-size:16.5px}
.card .no{color:var(--mut);font-size:12.5px;white-space:nowrap}
.card .pred{font-size:15.5px;margin:8px 0 6px}
.card .why{color:var(--mut);font-size:13.5px;border-top:1px dashed var(--line);padding-top:8px;margin-top:8px}
.card .why b{color:#c7cedd;font-weight:600}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:14px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.5px;
  position:sticky;top:0;background:var(--bg)}
tr.row-hit{background:var(--hitbg)}
tr.row-partial{background:var(--partbg)}
tr.row-na td{color:#8e96a8}
.v{font-weight:700;white-space:nowrap;font-size:12.5px}
.v.hit{color:var(--hit)} .v.partial{color:var(--partial)} .v.no{color:#8e96a8} .v.na{color:var(--na)}
.badge{display:inline-block;font-size:11px;padding:2px 8px;border-radius:6px;border:1px solid var(--line);color:var(--mut)}
.note{background:var(--nabg);border:1px solid #243056;border-radius:12px;padding:14px 16px;
  color:#cdd6ee;font-size:14px;margin-top:16px}
.cell-rule{color:var(--mut);font-size:13px}
.cell-find{font-size:13.5px}
.foot{color:var(--mut);font-size:12.5px;margin-top:34px;text-align:center;border-top:1px solid var(--line);padding-top:18px}
"""


def _card(v: RuleVerdict) -> str:
    cls = "partial" if v.verdict == "PARTIAL" else ""
    pred = v.prediction or v.finding
    return f"""<div class="card {cls}">
      <div class="top"><span class="title">{_esc(v.title)}</span>
        <span class="no">Rule #{v.no} · {VERDICT_STYLE[v.verdict][1]}</span></div>
      <div class="pred">{_esc(pred)}</div>
      <div class="why"><b>Why this applies:</b> {_esc(v.finding)}</div>
    </div>"""


def _table_row(v: RuleVerdict) -> str:
    vcls, vlabel = VERDICT_STYLE[v.verdict]
    rowcls = {"HIT": "row-hit", "PARTIAL": "row-partial", "NA": "row-na"}.get(v.verdict, "")
    cat = CAT_LABEL.get(v.category, v.category)
    return f"""<tr class="{rowcls}">
      <td>{v.no}</td>
      <td><b>{_esc(v.title)}</b><br><span class="badge">{_esc(cat)}</span></td>
      <td class="cell-rule">{_esc(v.condition)}</td>
      <td><span class="v {vcls}">{_esc(vlabel)}</span></td>
      <td class="cell-find">{_esc(v.finding)}</td>
    </tr>"""


def build_html(pc: dict, client_name: str = "Client") -> str:
    if "_transit" not in pc or "_annual" not in pc:
        attach_contexts(pc)
    verdicts = evaluate_all(pc)
    counts = summarize(verdicts)
    lg = lagna(pc)
    meta = pc.get("meta", {})
    tx = pc.get("_transit") if isinstance(pc.get("_transit"), dict) else {}
    an = pc.get("_annual") if isinstance(pc.get("_annual"), dict) else {}
    tx_ok = tx and not tx.get("error")
    an_ok = an and not an.get("error")

    hits = [v for v in verdicts if v.verdict == "HIT"]
    partials = [v for v in verdicts if v.verdict == "PARTIAL"]

    hit_cards = "\n".join(_card(v) for v in hits) or "<p class='lead'>No rule fully hit the chart.</p>"
    part_cards = "\n".join(_card(v) for v in partials)

    rows = "\n".join(_table_row(v) for v in verdicts)

    na_count = counts.get("NA", 0)

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>108 Predictive Rules — {_esc(client_name)}</title>
<style>{_css()}</style></head>
<body><div class="wrap">

  <div class="hero">
    <h1>The 108 Predictive Rules — read against your chart</h1>
    <div class="sub">A chapter-by-chapter check of every rule in <i>Saral Jyotish Part V (Astrology Simplified)</i>,
    judged against your birth chart and written as plain-English predictions.</div>
    <div class="meta">
      <span class="chip">Name: <b>{_esc(client_name)}</b></span>
      <span class="chip">Lagna: <b>{_esc(lg)}</b></span>
      <span class="chip">DOB: <b>{_esc(meta.get('dob',''))}</b></span>
      <span class="chip">Time: <b>{_esc(meta.get('birth_time',''))}</b></span>
      <span class="chip">Place: <b>{_esc(meta.get('birth_place',''))}</b></span>
    </div>
    <div class="meta">
      {f'<span class="chip">Transits as of: <b>{_esc(tx.get("date",""))}</b> · Saturn in <b>{_esc(tx.get("positions",{}).get("Saturn",{}).get("sign",""))}</b></span>' if tx_ok else ''}
      {f'<span class="chip">Annual year from: <b>{_esc(an.get("return_date",""))}</b> · Ascendant <b>{_esc(an.get("lagna_sign",""))}</b> · Year Lord <b>{_esc(an.get("year_lord",""))}</b></span>' if an_ok else ''}
    </div>
  </div>

  <div class="tally">
    <div class="t hit"><div class="n">{counts.get('HIT',0)}</div><div class="l">Hit your chart</div></div>
    <div class="t partial"><div class="n">{counts.get('PARTIAL',0)}</div><div class="l">Partly hit</div></div>
    <div class="t no"><div class="n">{counts.get('NO',0)}</div><div class="l">Not present</div></div>
    <div class="t na"><div class="n">{na_count}</div><div class="l">Need transit / year chart</div></div>
  </div>

  <h2>What these rules say about you</h2>
  <p class="lead">These are the chapters whose conditions are actually present in your chart — the predictions that apply to you.</p>
  <div class="cards">{hit_cards}</div>

  <h2>Conditions that are partly present</h2>
  <p class="lead">Some — but not all — of the rule's requirements are met, so the effect is present in a softer form.</p>
  <div class="cards">{part_cards}</div>

  <h2>Full verdict table — all 108 rules</h2>
  <p class="lead">Every chapter of the book, the exact condition it tests, and whether it is present in your chart.
  Green rows hit; amber rows partly hit.</p>
  <table>
    <thead><tr><th>#</th><th>Chapter / rule</th><th>What the rule checks</th><th>Verdict</th><th>Finding in your chart</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <div class="note"><b>Chapters 84–108 — transit &amp; annual (Varshaphal) rules — are now computed live.</b>
  The Saturn/Jupiter <i>transit</i> rules (84–97, incl. Sade Sati) are judged against your planetary positions
  {f'as of <b>{_esc(tx.get("date",""))}</b>' if tx_ok else 'for today'}, and the <i>Varshaphal</i> annual rules (98–108 — Year Lord,
  Muntha, Tri-Rashi-Pati, annual Raj-Yoga, etc.) against your current solar-return year
  {f'(starting <b>{_esc(an.get("return_date",""))}</b>, ascendant {_esc(an.get("lagna_sign",""))})' if an_ok else ''}.
  These results are <b>time-specific</b> — they shift as transits move and each year as a new annual chart begins, unlike the
  birth-chart rules (1–83) which hold for life. {f'Only {na_count} rule(s) could not be auto-evaluated.' if na_count else 'Every one of the 108 rules has been evaluated.'}</div>

  <div class="foot">Generated from predictivetechnique.pdf · 108 chapters · birth-chart rules evaluated automatically,
  transit/annual rules flagged for time-specific review. For guidance, not a substitute for a personal consultation.</div>

</div></body></html>"""


def write_report(pc: dict, out_dir: Path, client_name: str = "Client") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"Predictive_108_Rules_{client_name}.html"
    html = build_html(pc, client_name)
    try:
        from client_report_html import finalize_report_html
        html = finalize_report_html(html, client_name)
    except ImportError:
        pass
    out.write_text(html, encoding="utf-8")
    return out


if __name__ == "__main__":
    import argparse
    from astro_chart_bridge import compute_chart

    ap = argparse.ArgumentParser(description="108 predictive-technique rules report")
    ap.add_argument("--name", default="Ritesh")
    ap.add_argument("--dob", default="1985-03-08")
    ap.add_argument("--time", default="13:05")
    ap.add_argument("--place", default="Patna, India")
    ap.add_argument("--lat", type=float, default=25.5941)
    ap.add_argument("--lon", type=float, default=85.1376)
    ap.add_argument("--tz", type=float, default=5.5)
    ap.add_argument("-o", "--out", default="")
    args = ap.parse_args()

    pc = compute_chart(client_name=args.name, dob=args.dob, birth_time=args.time,
                       place=args.place, latitude=args.lat, longitude=args.lon, timezone=args.tz)
    attach_contexts(pc, latitude=args.lat, longitude=args.lon, timezone=args.tz)
    out_dir = Path(args.out) if args.out else (BASE_DIR / "reports" / args.name)
    path = write_report(pc, out_dir, args.name)
    print(f"Wrote {path}")
