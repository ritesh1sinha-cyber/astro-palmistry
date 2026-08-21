"""One document shell and one stylesheet for every customer-facing report.

The card design lived inside `report_cards.render` as a single f-string, which
was fine while it was the only screen using it. Now horary, numerology, matching
and the palm tab render in the same visual language, and a second copy of ~7 KB
of CSS is a guarantee that the tabs will drift apart.

So the stylesheet lives here once, and `page()` wraps any body fragment in the
document shell. `report_cards` interpolates STYLE rather than carrying its own
copy — one source of truth, so a colour change lands everywhere at once.

Fragments that render inside a report (present_read, report_timing,
tab_renderers, remedy_block, lo_shu, daily_card) assume these class names. They
are deliberately generic — .card, .wrap, .pill — which is safe inside an iframe
and NOT safe injected into the host page, where the site's own .card would
collide. Reports are served as standalone documents through /api/file/{token}
for exactly that reason.
"""

from __future__ import annotations

import html as _html
import re as _re
import unicodedata as _ud
from typing import Any

#: The shared stylesheet. Extracted verbatim from report_cards' original
#: f-string, so the flagship report is pixel-identical to before the refactor.
STYLE = """
:root{--ink:#16181d;--muted:#6a7080;--line:#e6e4df;--bg:#fbfaf8;
--up:#1c6b45;--down:#a3341f;--mixed:#8a6a1f;--card:#fff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,system-ui,sans-serif;
line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:640px;margin:0 auto;padding:0 20px 80px}
header{padding:44px 0 22px}
.eyebrow{font-size:.7rem;letter-spacing:.16em;text-transform:uppercase;
color:var(--muted);font-weight:600}
h1{font-family:Fraunces,Georgia,serif;font-size:2rem;line-height:1.12;
margin:10px 0 12px;font-weight:600;letter-spacing:-.015em}
.chartline{font-size:.86rem;color:var(--muted)}
.planet-strip{margin:18px 0 6px}
.planet-strip .sec-note{margin-bottom:10px}
ul.pchips{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
li.pchip{background:#fff;border:1px solid var(--line);border-left-width:4px;
border-radius:10px;padding:10px 12px;min-width:132px;flex:1 1 140px}
li.pchip.up{border-left-color:var(--up);background:#f3faf6}
li.pchip.down{border-left-color:var(--down);background:#fff6f4}
li.pchip.mixed{border-left-color:var(--mixed);background:#fffbeb}
li.pchip b{display:block;font-family:Fraunces,serif;font-size:1.05rem;font-weight:600}
li.pchip span{display:block;font-size:.78rem;color:#3d4250;margin-top:2px}
li.pchip em.pchip-note{display:block;font-style:normal;font-size:.72rem;line-height:1.35;
color:var(--mixed);margin-top:6px;font-weight:500}
li.pchip small{display:block;font-size:.66rem;letter-spacing:.06em;text-transform:uppercase;
color:var(--muted);margin-top:6px;font-weight:600}
.ni-chart{margin:16px 0 8px;padding:0;border:0}
.ni-chart .ev-label{margin-bottom:8px}
.ni-chart-box{width:100%;max-width:380px;margin:0 auto;aspect-ratio:1/1;
background:#fff;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.ni-svg{display:block;width:100%;height:100%}
.ni-frame{stroke:var(--ink);stroke-width:1.8;fill:#fff}
.ni-grid{stroke:var(--ink);stroke-width:1.35;fill:none}
.ni-house{fill:#fbfaf8;stroke:var(--ink);stroke-width:1.15;fill-opacity:0.35}
.ni-num{font-family:Inter,system-ui,sans-serif;font-size:10px;font-weight:700;
fill:#6b7280}
.ni-pl{font-family:Inter,system-ui,sans-serif;font-size:11px;font-weight:700;
fill:var(--ink)}
.ni-legend{text-align:center;margin:8px 0 0;font-size:.72rem}
.ni-warn{text-align:center;margin:6px 0 0;font-size:.78rem;color:var(--mixed)}
.now-box{background:var(--ink);color:#f7f5f1;border-radius:14px;
padding:20px 22px;margin:22px 0 30px}
.now-box .lbl{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
opacity:.6;font-weight:600}
.now-box h2{font-family:Fraunces,serif;font-size:1.3rem;margin:8px 0 6px;font-weight:600}
.now-box p{margin:0;font-size:.9rem;opacity:.85}
h3.sec{font-family:Fraunces,serif;font-size:1.25rem;margin:38px 0 4px;font-weight:600}
.sec-note{font-size:.82rem;color:var(--muted);margin:0 0 16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:18px 20px;margin-bottom:12px}
.card-top{display:flex;justify-content:space-between;align-items:center;gap:10px}
.area{font-size:.68rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--muted)}
.pill{font-size:.66rem;font-weight:600;padding:3px 9px;border-radius:99px;
letter-spacing:.04em}
.pill.up{background:#e4f2ea;color:var(--up)}
.pill.down{background:#fbeae6;color:var(--down)}
.pill.mixed{background:#fbf1de;color:var(--mixed)}
.claim{font-family:Fraunces,serif;font-size:1.12rem;line-height:1.4;
margin:12px 0 10px}
.when{font-size:.78rem;font-weight:600;color:var(--muted);
letter-spacing:.02em;margin-bottom:10px}
details{border-top:1px solid var(--line);padding-top:10px}
summary{font-size:.78rem;color:var(--muted);cursor:pointer;font-weight:500}
details ul{margin:10px 0 0;padding-left:18px;font-size:.85rem;color:#3d4250}
details li{margin:6px 0}
.action{margin-top:12px;background:#f6f4ef;border-radius:10px;padding:12px 14px}
.act-label{font-size:.66rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--mixed)}
.action p{margin:6px 0 0;font-size:.88rem}
.mantra{font-style:italic;color:var(--muted);font-size:.82rem!important}
.blurred{filter:blur(4.5px);user-select:none;opacity:.6}
.locked-inline .lockicon{color:var(--mixed);font-weight:700}
.when.locked-inline{color:var(--mixed);font-weight:600}
.lock-wrap{position:relative;border:1px solid var(--line);border-radius:14px;
overflow:hidden;background:var(--card);margin-bottom:26px}
.lock-blur{padding:18px 20px;filter:blur(5px);opacity:.55;user-select:none;
pointer-events:none;color:#3d4250;font-size:.86rem;line-height:1.7}
.lock-over{position:absolute;inset:0;display:grid;place-items:center;
background:rgba(251,250,248,.18);pointer-events:none;padding:12px}
.lock-chip{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
font-weight:600;color:var(--mixed);background:#fff;border:1px solid var(--line);
border-radius:999px;padding:7px 14px;box-shadow:0 2px 10px rgba(22,24,29,.08);
white-space:nowrap}
.locked-section{margin-top:28px}
.evidence{border-top:1px solid var(--line);padding-top:10px;margin-top:4px}
.ev-label{font-size:.64rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--muted)}
.agree{float:right;font-size:.66rem;font-weight:600;color:var(--muted);
background:#f1efea;border-radius:99px;padding:2px 9px}
.evidence ul{margin:8px 0 0;padding-left:18px;font-size:.85rem;color:#3d4250}
.evidence li{margin:6px 0}
.confluence-box{border-top:1px solid var(--line);padding-top:10px;margin-top:10px}
.promise-line{font-size:.86rem;color:#3d4250;margin:0 0 8px;line-height:1.45}
.promise-teaser{color:var(--muted)}
.promise-meta{font-size:.78rem;color:var(--muted);font-weight:500}
.promise-evidence{margin:4px 0 8px;padding-left:18px;font-size:.78rem;color:var(--muted)}
.promise-evidence li{margin:3px 0}
.promise-meaning{font-size:.86rem;color:#3d4250;margin:0 0 8px;line-height:1.45}
.conf-mechanism{font-size:.86rem;color:#3d4250;margin:0 0 8px;line-height:1.45}
.promise-manifest,.promise-pressure{margin:0 0 8px}
.promise-manifest ul,.promise-pressure ul,.promise-locked{margin:4px 0 0;padding-left:18px;font-size:.82rem;color:#3d4250}
.promise-manifest li,.promise-pressure li,.promise-locked li{margin:3px 0}
.promise-locked{color:var(--muted)}
.wealth-subs{margin-top:4px}
.wealth-sub-row{display:flex;justify-content:space-between;gap:12px;font-size:.82rem;
  color:#3d4250;padding:3px 0;border-bottom:1px dashed rgba(0,0,0,.08)}
.wealth-sub-row:last-child{border-bottom:none}
.wealth-sub-row b{color:#1f2430;font-weight:600}
details.promise-detail{margin:2px 0 8px}
details.promise-detail summary{font-size:.78rem;color:var(--muted);cursor:pointer}
.dashboard-grid{display:grid;gap:14px;margin:12px 0 20px}
.dash-group{background:var(--card,#fff);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.dash-group h4{margin:0 0 4px;font-size:.95rem}
.dash-note{margin:0 0 8px;font-size:.8rem;color:var(--muted)}
.dash-group ul{margin:0;padding-left:18px;font-size:.85rem}
.dash-group li{margin:3px 0}
.confluence-summary{margin:6px 0 8px;font-size:.88rem}
.confluence-summary span{display:block;font-size:.78rem;color:var(--muted);margin-top:4px}
.confluence-details{margin-top:6px}
.confluence-details summary{font-size:.78rem;color:var(--muted);cursor:pointer;font-weight:500}
.confluence-rows{margin-top:8px}
.conf-row{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-start;padding:8px 0;
border-top:1px solid var(--line);font-size:.82rem}
.conf-row:first-child{border-top:none;padding-top:0}
.conf-method{min-width:120px;font-weight:600;color:var(--ink)}
.conf-signal{font-size:.66rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;
padding:2px 8px;border-radius:99px}
.conf-signal.support{background:#e4f2ea;color:var(--up)}
.conf-signal.caution{background:#fbeae6;color:var(--down)}
.conf-signal.neutral{background:#f1efea;color:var(--muted)}
.conf-why{display:block;width:100%;font-size:.76rem;color:var(--muted);margin-top:2px}
.conf-health-frame{font-size:.84rem;color:#3d4250;margin:0 0 8px;line-height:1.45}
.proof{background:#fff;border:2px solid var(--ink);border-radius:14px;
padding:22px;margin:26px 0}
.proof h3{font-family:Fraunces,serif;font-size:1.22rem;margin:0 0 8px;font-weight:600}
.proof p{font-size:.9rem;margin:0 0 12px}
.proof .hits{list-style:none;margin:14px 0 0;padding:0}
.proof .hits li{display:flex;gap:10px;align-items:flex-start;padding:9px 0;
border-top:1px solid var(--line);font-size:.88rem}
.proof .tick{color:var(--up);font-weight:700}
.proof .miss{color:var(--muted);font-weight:700}
.daily{background:#f2efe9;border-radius:14px;padding:20px 22px;margin:26px 0}
.daily .lbl{font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
font-weight:600;color:var(--muted)}
.daily h3{font-family:Fraunces,serif;font-size:1.16rem;margin:8px 0 10px;font-weight:600}
.dodont{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:12px 0}
@media(max-width:520px){.dodont{grid-template-columns:1fr}}
.dodont>div{border-radius:10px;padding:12px 14px;font-size:.84rem}
.dodont .do{background:#e4f2ea;border:1px solid #b7dcc8;color:#174a32}
.dodont .dont{background:#fbeae6;border:1px solid #e8b6aa;color:#7a2416}
.dodont .t{font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;
font-weight:700;margin-bottom:6px}
.do .t{color:var(--up)} .dont .t{color:var(--down)}
/* Remedies & gemstones — keep wear/do and avoid visually separate */
.remedy-card{margin:22px 0 28px}
.remedy-lede{font-size:.9rem;color:#3d4250;margin:8px 0 14px}
.remedy-do,.remedy-dont,.stones-group{border-radius:12px;padding:14px 16px;margin:0 0 12px}
.remedy-do,.stones-group.up{background:#e4f2ea;border:1px solid #b7dcc8}
.stones-group.trial{background:#fbf6e4;border:1px solid #e6d59a}
.remedy-dont,.stones-group.down{background:#fbeae6;border:1px solid #e8b6aa}
.remedy-do-label,.stones-group-label{font-size:.66rem;letter-spacing:.12em;
text-transform:uppercase;font-weight:700;margin:0 0 8px}
.remedy-do-label,.stones-group.up .stones-group-label{color:var(--up)}
.stones-group.trial .stones-group-label{color:var(--mixed)}
.remedy-dont-label,.stones-group.down .stones-group-label{color:var(--down)}
.remedy-do p,.remedy-dont p{margin:0;font-size:.9rem;line-height:1.5}
ul.stones{list-style:none;margin:0;padding:0}
li.stone{background:#fff;border:1px solid var(--line);border-left-width:4px;
border-radius:10px;padding:12px 14px;margin:0 0 10px}
li.stone:last-child{margin-bottom:0}
li.stone.up{border-left-color:var(--up);background:#f3faf6}
li.stone.trial{border-left-color:var(--mixed);background:#fffbeb}
li.stone.down{border-left-color:var(--down);background:#fff6f4}
li.stone.mixed{border-left-color:var(--mixed);background:#fffbeb}
.stone-top{display:flex;justify-content:space-between;gap:10px;align-items:baseline;
flex-wrap:wrap}
.stone-verdict{font-size:.68rem;font-weight:700;letter-spacing:.04em;
text-transform:uppercase}
li.stone.up .stone-verdict{color:var(--up)}
li.stone.trial .stone-verdict,li.stone.mixed .stone-verdict{color:var(--mixed)}
li.stone.down .stone-verdict{color:var(--down)}
.stone-role,.stone-detail,.stone-why,.stone-alt{font-size:.82rem;color:#3d4250;
margin-top:6px;line-height:1.45}
.remedy-locked{background:#f6f4ef;border-radius:10px;padding:12px 14px;
font-size:.88rem;margin-top:10px}
.windows{list-style:none;margin:10px 0 0;padding:0;font-size:.85rem}
.windows li{display:flex;gap:10px;padding:6px 0;border-top:1px solid #e0dcd4}
.windows b{min-width:96px;font-variant-numeric:tabular-nums}
.windows-list{list-style:none;margin:0;padding:0}
.win{background:#fff;border:1px solid var(--line);border-left-width:4px;
border-radius:12px;padding:16px 18px;margin-bottom:12px}
.win.up{border-left-color:var(--up)}
.win.down{border-left-color:var(--down)}
.win.mixed{border-left-color:var(--mixed)}
.win-when{font-size:.74rem;font-weight:600;letter-spacing:.04em;
color:var(--muted);font-variant-numeric:tabular-nums}
.win-head{font-family:Fraunces,serif;font-size:1.05rem;margin:4px 0 6px;
font-weight:600}
.win-tag{font-size:.64rem;letter-spacing:.1em;text-transform:uppercase;
color:var(--muted);font-family:Inter,sans-serif;font-weight:600}
.win-lead{margin:0 0 10px;font-size:.94rem}
.win-why{margin:0;padding-left:16px;font-size:.83rem;color:#3d4250}
.win-why li{margin:4px 0}
.personal p{margin:8px 0 0;font-size:.83rem;color:#3d4250}
.dasha-conf{margin-top:14px;border-top:1px solid rgba(255,255,255,.18);
padding-top:12px}
.dsys{display:flex;justify-content:space-between;font-size:.82rem;
padding:3px 0;opacity:.9}
.dsys span{opacity:.65}
.dagree{margin-top:9px;font-size:.8rem;opacity:.8}
.dagree-mix{margin-top:6px;font-size:.78rem;opacity:.75;color:#c4a35a}
.persona .traits{list-style:none;margin:0;padding:0}
.persona .traits li{font-family:Fraunces,serif;font-size:1.02rem;
line-height:1.45;padding:9px 0;border-bottom:1px solid var(--line)}
.persona .traits li:last-child{border-bottom:0}
.yogas{margin-top:12px;background:#f6f4ef;border-radius:10px;padding:12px 14px}
.yogas ul{margin:8px 0 0;padding-left:18px;font-size:.84rem}
ol.timeline{list-style:none;margin:0;padding:0;border-left:2px solid var(--line)}
ol.timeline li{position:relative;padding:0 0 20px 20px}
ol.timeline li::before{content:"";position:absolute;left:-7px;top:5px;width:12px;
height:12px;border-radius:50%;background:#fff;border:2px solid var(--line)}
ol.timeline li.now::before{background:var(--ink);border-color:var(--ink)}
.tl-when{font-size:.74rem;font-weight:600;color:var(--muted);letter-spacing:.03em}
.tl-body{font-size:.92rem;margin-top:2px}
.tl-areas{display:block;font-size:.78rem;color:var(--muted);margin-top:2px}
.buy{background:var(--ink);color:#f7f5f1;border-radius:14px;padding:24px;
margin-top:32px;text-align:center}
.buy h3{font-family:Fraunces,serif;font-size:1.2rem;margin:0 0 8px;font-weight:600}
.buy p{font-size:.88rem;opacity:.85;margin:0 0 16px}
.buy .cta{display:inline-block;background:#f7f5f1;color:var(--ink);
padding:12px 26px;border-radius:99px;font-weight:600;font-size:.9rem;
text-decoration:none}
@media print{
  .buy,.mm-overlay,.present-ask,.recog-ask,.pillbtn{display:none!important}
}
@page{size:A4;margin:14mm 12mm}
footer{margin-top:40px;font-size:.74rem;color:var(--muted);text-align:center}
.prediction{margin:14px 0;padding:14px 16px;background:#fff;border:1px solid var(--line);
border-radius:12px}
.pred-scenario{margin:0 0 10px;font-size:.92rem;line-height:1.55}
.pred-details{margin-top:10px}
.pred-details summary{font-size:.78rem;color:var(--muted);cursor:pointer;font-weight:500}
.pred-why{margin:10px 0 0;padding:10px 12px;border-radius:10px;background:#e3eef9;
border:1px solid #b7cfe6;border-left:4px solid #1a5f9e;font-size:.84rem;
color:#163a5c;line-height:1.5}
.pred-why b{display:inline-block;margin-right:4px;color:#0b4f8a;font-size:.72rem;
font-weight:800;letter-spacing:.08em;text-transform:uppercase}
/* Keep Why chip above generic paragraph colour rules (evidence / lists / windows) */
.evidence .pred-why,.win .pred-why,.hits .pred-why,.palm-list .pred-why,
.palm-points .pred-why,.qa .pred-why,.card .pred-why{
  margin:10px 0 0;padding:10px 12px;border-radius:10px;background:#e3eef9;
  border:1px solid #b7cfe6;border-left:4px solid #1a5f9e;font-size:.84rem;
  color:#163a5c;line-height:1.5}
.evidence .pred-why b,.win .pred-why b,.hits .pred-why b,.palm-list .pred-why b,
.palm-points .pred-why b,.qa .pred-why b,.card .pred-why b{
  display:inline-block;margin-right:4px;color:#0b4f8a;font-size:.72rem;
  font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.pred-list .prediction{list-style:none}
.present-list.pred-list{list-style:none;padding:0;margin:0}
.present-list.pred-list>li{margin-bottom:12px}
"""

FONTS = ('<link href="https://fonts.googleapis.com/css2?'
         'family=Fraunces:opsz,wght@9..144,400;9..144,600&'
         'family=Inter:wght@400;500;600&display=swap" rel="stylesheet"/>')

EXTRA = """
/* Shell additions for the tabs that are not the flagship card report. */
.tabhead{padding:38px 0 16px}
.tabhead .eyebrow{font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;
font-weight:700;color:var(--mixed)}
.tabhead h1{font-family:Fraunces,Georgia,serif;font-size:1.75rem;line-height:1.14;
margin:10px 0 8px;font-weight:600;letter-spacing:-.015em}
.tabhead .sub{font-size:.86rem;color:var(--muted);margin:0}
.routes{display:grid;gap:10px;margin:8px 0 26px}
.route{display:flex;justify-content:space-between;align-items:center;gap:12px;
background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:14px 16px;text-decoration:none;color:inherit}
.route b{font-size:.95rem}
.route span{font-size:.8rem;color:var(--muted)}
.route .go{font-size:.72rem;font-weight:700;color:var(--mixed);
letter-spacing:.08em;text-transform:uppercase;white-space:nowrap}
footer.fine{margin-top:44px;padding-top:18px;border-top:1px solid var(--line);
font-size:.72rem;color:var(--muted);line-height:1.6}
details.workings{margin:28px 0;border:1px solid var(--line);border-radius:12px;
background:var(--card);overflow:hidden}
details.workings summary{cursor:pointer;padding:14px 18px;font-size:.82rem;
font-weight:600;color:var(--muted);list-style:none}
details.workings summary::-webkit-details-marker{display:none}
details.workings[open] summary{border-bottom:1px solid var(--line)}
.workings-wrap,.workings-body{padding:14px 18px 18px;font-size:.84rem;
color:#3d4250;line-height:1.55}
.workings-body h4,.workings-body h5{font-family:Fraunces,Georgia,serif;
font-size:1rem;margin:18px 0 8px;color:var(--ink)}
.workings-body table{width:100%;border-collapse:collapse;font-size:.78rem;margin:10px 0}
.workings-body th,.workings-body td{border:1px solid var(--line);padding:6px 8px;
text-align:left;vertical-align:top}
.workings-main>summary{font-size:.88rem;color:var(--ink)}
/* tab_renderers shared dialect */
.tab{margin:8px 0 28px}
.tab-head{margin-bottom:14px}
.tab-kind{font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
font-weight:700;color:var(--mixed)}
.tab-head h2{font-family:Fraunces,Georgia,serif;font-size:1.45rem;line-height:1.2;
margin:8px 0 0;font-weight:600}
.tab-lead{font-size:.98rem;margin:12px 0 8px}
.tab-sub{font-size:.86rem;color:var(--muted);margin:0 0 14px}
.tab-caveat{font-size:.8rem;color:var(--muted);margin:16px 0 0}
.tab-sec{font-family:Fraunces,serif;font-size:1.05rem;margin:22px 0 8px;font-weight:600}
.tab-cta{background:#f6f4ef;border-radius:12px;padding:14px 16px;margin-top:18px;
font-size:.9rem}
.tab-cta .fine{font-size:.78rem;color:var(--muted);margin:8px 0 0}
.score-hero{display:flex;gap:18px;align-items:center;margin:14px 0}
.score-num{font-family:Fraunces,serif;font-size:3rem;font-weight:600;line-height:1}
.score-num span{font-size:1.1rem;color:var(--muted);font-weight:500}
.score-side{flex:1}
.score-band{font-size:.9rem;font-weight:600;margin-bottom:6px}
.bar{height:8px;background:#eeebe4;border-radius:99px;overflow:hidden;margin:6px 0}
.bar span{display:block;height:100%;background:var(--ink);border-radius:99px}
.bar span.good{background:var(--up)}.bar span.bad{background:var(--down)}
.koots{list-style:none;margin:10px 0 0;padding:0}
.koot{padding:10px 0;border-top:1px solid var(--line)}
.koot-top{display:flex;justify-content:space-between;gap:10px;font-size:.9rem}
.koot-score{font-variant-numeric:tabular-nums;font-weight:600}
.koot-what{font-size:.78rem;color:var(--muted);margin:4px 0 6px}
.mm-dosha{background:#fbeae6;border-radius:12px;padding:14px 16px;margin-top:16px}
.btr-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:14px 0}
@media(min-width:560px){.btr-grid{grid-template-columns:repeat(4,1fr)}}
.btr-grid div{background:var(--card);border:1px solid var(--line);border-radius:12px;
padding:12px 14px}
.btr-grid span{display:block;font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);font-weight:600;margin-bottom:4px}
.btr-grid b{font-size:1.05rem}
.btr-stakes{background:#fbeae6;border-radius:12px;padding:14px 16px;margin-top:14px}
.btr-answer{background:#e4f2ea;border-radius:12px;padding:16px 18px;margin-top:16px}
.btr-time{font-family:Fraunces,serif;font-size:2rem;color:var(--up);margin:6px 0}
.muh-hero{background:var(--card);border:1px solid var(--line);border-radius:14px;
padding:18px 20px;margin:12px 0 16px;border-left:4px solid var(--mixed)}
.muh-hero[data-verdict="good"]{border-left-color:var(--up)}
.muh-hero[data-verdict="bad"]{border-left-color:var(--down)}
.muh-verdict{font-family:Fraunces,serif;font-size:1.6rem;font-weight:600;margin:0 0 6px}
.muh-checks{list-style:none;margin:8px 0 0;padding:0}
.muh-checks li{padding:8px 0;border-top:1px solid var(--line);font-size:.88rem}
.muh-checks li.ok b{color:var(--up)}.muh-checks li.bad b{color:var(--down)}
.num-grid{display:grid;gap:10px;margin:12px 0}
.num-card{display:flex;gap:14px;background:var(--card);border:1px solid var(--line);
border-radius:12px;padding:14px 16px}
.num-big{font-family:Fraunces,serif;font-size:2.2rem;font-weight:600;min-width:2.2rem}
.num-body{flex:1}
.num-body p{margin:3px 0 6px;font-size:.88rem;color:#3d4250}
.lo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:0 0 16px}
.lo-cell{border:1px solid var(--line);border-radius:10px;padding:10px 8px;text-align:center;
background:var(--card);min-height:5.4rem}
.lo-cell.empty{border-style:dashed;background:#faf8f4}
.lo-n{display:block;font-size:.64rem;letter-spacing:.1em;color:var(--muted);font-weight:600}
.lo-count{display:block;font-family:Fraunces,serif;font-size:1.5rem;line-height:1.3;
letter-spacing:.06em}
.lo-cell.empty .lo-count{color:var(--down)}
.lo-what{display:block;font-size:.68rem;color:var(--muted);line-height:1.25}
.num-label{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);
font-weight:600}
.num-src{font-size:.74rem;color:var(--muted)}
.num-year,.num-future{background:#f6f4ef;border-radius:12px;padding:14px 16px;margin:14px 0}
.num-seq{list-style:none;margin:8px 0 0;padding:0}
.num-seq li{display:flex;gap:12px;padding:6px 0;border-top:1px solid var(--line)}
.num-extra{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:14px 0}
.num-extra div{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:10px 12px;font-size:.82rem}
.num-extra span{display:block;font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;
color:var(--muted);font-weight:600;margin-bottom:3px}
.fine{font-size:.78rem;color:var(--muted)}
.locked-inline{color:var(--mixed)}
/* daily reading */
.daily .agree{float:right}
.daily .pill{display:inline-block;margin-top:8px}
.lanes{list-style:none;margin:0;padding:0}
.lanes li{display:grid;grid-template-columns:8.5rem 1fr auto;gap:10px;
align-items:baseline;padding:9px 0;border-top:1px solid var(--line);font-size:.86rem}
.lanes li:first-child{border-top:0}
.lanes li>span:first-child{font-weight:600}
@media(max-width:520px){.lanes li{grid-template-columns:1fr auto}
.lanes li>span:first-child{grid-column:1/-1}}
.windows li.w-up{border-left:3px solid var(--up);padding-left:10px}
.windows li.w-down{border-left:3px solid var(--down);padding-left:10px}
/* palm reading */
.pill.faint{background:#f1efea;color:var(--muted)}
.palm-shots{margin:8px 0 18px}
.palm-imgs{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:10px 0 8px}
@media(max-width:480px){.palm-imgs{grid-template-columns:1fr}}
.palm-imgs figure{margin:0}
.palm-imgs img{width:100%;display:block;border:1px solid var(--line);border-radius:12px}
.palm-img-missing{display:flex;align-items:center;justify-content:center;min-height:12rem;
padding:16px;border:1px dashed var(--line);border-radius:12px;text-align:center;
font-size:.82rem;line-height:1.45;color:var(--muted);background:#f6f4ef}
.palm-imgs figcaption{font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;
font-weight:600;color:var(--muted);margin-top:6px;text-align:center}
.palm-scores{list-style:none;margin:10px 0 0;padding:0}
.palm-scores li{display:grid;grid-template-columns:5.5rem 1fr 2.2rem;gap:10px;
align-items:center;padding:6px 0;font-size:.85rem}
.palm-scores b{text-align:right;font-variant-numeric:tabular-nums}
.palm-list{list-style:none;margin:0;padding:0}
.palm-list li{padding:10px 0;border-top:1px solid var(--line);font-size:.9rem}
.palm-list li:first-child{border-top:0}
.palm-list p{margin:4px 0 0;font-size:.88rem;color:#3d4250}
.palm-list .pred-why,.palm-points .pred-why{
  margin:10px 0 0;padding:10px 12px;border-radius:10px;background:#e3eef9;
  border:1px solid #b7cfe6;border-left:4px solid #1a5f9e;font-size:.84rem;
  color:#163a5c;line-height:1.5}
.palm-list .pred-why b,.palm-points .pred-why b{display:inline-block;margin-right:4px;
color:#0b4f8a;font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase}
.palm-list.plain li{font-size:.88rem;color:#3d4250}
.palm-points{list-style:none;margin:8px 0 0;padding:0}
.palm-points li{padding:8px 0;border-top:1px solid var(--line)}
.palm-points p{margin:3px 0 0}
.pt-when{margin-left:8px;font-size:.74rem;font-weight:600;color:var(--mixed);
font-variant-numeric:tabular-nums}
b.both{font-size:.72rem;color:var(--up);letter-spacing:.02em}
/* Present reading + recognition feedback (accuracy pills / mismatch modal) */
.present{margin:22px 0 28px}
.present-head .ev-label,.recog-label{font-size:.64rem;letter-spacing:.13em;
text-transform:uppercase;font-weight:600;color:var(--muted)}
.present-head h3{font-family:Fraunces,serif;font-size:1.22rem;margin:8px 0 6px;font-weight:600}
.present-lede{font-size:.9rem;color:#3d4250;margin:0 0 12px}
.present-list{margin:0 0 14px;padding-left:18px;font-size:.9rem}
.present-list li{margin:8px 0}
.present-ask,.recog-ask{display:flex;flex-wrap:wrap;align-items:center;gap:8px;
margin-top:14px;padding-top:14px;border-top:1px solid var(--line);font-size:.86rem}
.present-ask>span,.recog-ask>span{width:100%;color:var(--muted);font-weight:500}
.pillbtn{appearance:none;border:1px solid var(--line);background:#fff;color:var(--ink);
font:inherit;font-size:.82rem;font-weight:600;padding:8px 14px;border-radius:99px;
cursor:pointer}
.pillbtn:hover{border-color:var(--ink)}
.pillbtn.on{background:var(--ink);color:#f7f5f1;border-color:var(--ink)}
.pillbtn:disabled{opacity:.55;cursor:default}
.feedback-thanks{margin-top:12px;font-size:.88rem;color:var(--up);font-weight:600}
.recognition .recog-ask{margin-top:18px}
.recog-block{margin:16px 0;padding-top:12px;border-top:1px solid var(--line)}
.recog-claim{font-family:Fraunces,serif;font-size:1.02rem;margin:10px 0 4px;font-weight:500}
.recog-why{font-size:.78rem;color:var(--muted);margin:0 0 8px}
.recog-why span{font-weight:700;letter-spacing:.06em;text-transform:uppercase;
font-size:.64rem;margin-right:6px}
.mm-overlay{position:fixed;inset:0;background:rgba(22,24,29,.48);display:flex;
align-items:flex-end;justify-content:center;padding:16px;z-index:40}
@media(min-width:560px){.mm-overlay{align-items:center}}
.mm-overlay[hidden]{display:none!important}
.mm-box{background:#fff;border-radius:16px;padding:22px 20px 18px;max-width:440px;
width:100%;max-height:min(88vh,640px);overflow:auto;box-shadow:0 18px 50px rgba(0,0,0,.18)}
.mm-box h3{font-family:Fraunces,serif;font-size:1.2rem;margin:8px 0 10px;font-weight:600}
.mm-box p{font-size:.88rem;margin:0 0 10px;color:#3d4250}
.mm-routes{margin:8px 0 14px;padding-left:18px;font-size:.86rem;color:#3d4250}
.mm-routes li{margin:8px 0}
.mm-actions{display:grid;gap:8px;margin:14px 0 10px}
.cta-dark,.cta-light{display:block;text-align:center;text-decoration:none;font-weight:600;
font-size:.88rem;padding:12px 14px;border-radius:99px}
.cta-dark{background:var(--ink);color:#f7f5f1}
.cta-light{background:#f6f4ef;color:var(--ink);border:1px solid var(--line)}
.mm-close{appearance:none;display:block;width:100%;border:0;background:transparent;
color:var(--muted);font:inherit;font-size:.82rem;font-weight:600;padding:10px;
cursor:pointer}
/* Six-month validation timeline (free trust layer) */
.past-validation{margin:18px 0 24px}
.past-timeline{border-left:2px solid var(--line);padding-left:16px}
.past-event{position:relative;margin:14px 0;padding:14px 16px;border:1px solid var(--line);border-radius:14px;background:var(--card)}
.past-event:before{content:"";position:absolute;left:-23px;top:18px;width:10px;height:10px;border-radius:50%;background:var(--accent)}
.past-event.up{border-left:4px solid #2c7658}.past-event.mixed{border-left:4px solid #a06d1f}.past-event.down{border-left:4px solid #8b3d3d}
.past-date{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.03em;margin-bottom:5px}
.past-title{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);font-weight:700}
.past-headline{font-size:16px;font-weight:600;margin:5px 0 8px}
.past-noticed{margin:8px 0 10px}
.past-noticed ul{margin:6px 0 0;padding-left:1.15rem}
.past-noticed li{margin:3px 0;font-size:.86rem;color:#3d4250}
.past-meta,.past-why{font-size:12px;color:var(--muted);margin-top:5px}
.past-why{padding-top:7px;border-top:1px solid var(--line)}
.past-signal{margin-left:8px;font-size:11px;letter-spacing:.04em;text-transform:none;color:var(--muted);font-weight:600}
.past-manifest{margin:8px 0 4px}
.past-manifest ul{margin:6px 0 0;padding-left:18px;font-size:.86rem;color:#3d4250}
.past-manifest li{margin:3px 0}
.past-astro{margin-top:8px;font-size:.8rem;color:var(--muted)}
.past-astro summary{cursor:pointer;font-weight:600;color:var(--ink)}
.past-astro p{margin:6px 0 0}
.present-current{margin:18px 0}
/* Paid area-card interactivity */
.card-planets{display:flex;flex-direction:column;gap:8px;margin:10px 0 6px}
.card-planets .ev-label{width:100%;margin:0}
.planet-names{font-size:.9rem;font-weight:600;color:#2b303b;letter-spacing:.01em}
.planet-row{display:flex;gap:8px;align-items:flex-start;font-size:.82rem;color:#3d4250}
.chapter-planets{display:grid;gap:10px;margin:14px 0 4px}
.planet-theme{padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:#fbfaf7}
.planet-theme b{display:block;font-size:.84rem;margin-bottom:4px}
.planet-theme p{margin:0;font-size:.84rem;color:#3d4250;line-height:1.45}
.tl-period{display:block;margin-top:4px;font-size:.78rem;color:var(--muted);font-weight:500}
.planet-chip{display:inline-block;font-size:.72rem;font-weight:600;padding:4px 10px;border-radius:999px;border:1px solid var(--line);background:#f7f5f1;color:var(--ink);white-space:nowrap}
.expect{margin:8px 0}
.expect-note{margin:6px 0 0;font-size:.86rem;color:#3d4250;line-height:1.45}
.chapter-area-note{margin:8px 0 0;font-size:.86rem;color:#3d4250;line-height:1.45}
.trajectory{margin:10px 0 8px;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:#fbfaf7}
.trajectory .ev-label{display:block;margin-bottom:8px}
.trajectory-row{display:grid;grid-template-columns:1fr;gap:4px;font-size:.82rem;padding:10px 0;border-top:1px solid var(--line)}
.trajectory-row:first-of-type{border-top:0}
.traj-when{color:var(--muted);font-weight:600}
.traj-note{margin:0;color:#3d4250}
.trajectory-row small{color:var(--muted)}
.traj-up{color:#2c7658}.traj-mixed{color:#a06d1f}.traj-down{color:#8b3d3d}
.evidence-astro{margin-top:10px;font-size:.86rem}
.evidence-astro summary{cursor:pointer;font-weight:600}
.evidence-astro .pred-why{margin-top:8px}
.evidence-astro p{margin:6px 0;line-height:1.45;color:#3d4250}
.evidence-astro .pred-agree{font-weight:600;color:#2b303b}
"""

#: Click handlers for accuracy pills + mismatch modal. Reports are iframes, so
#: "go to BTR / horary / palm" is a postMessage to the host SPA (same origin
#: and Vercel→Railway cross-origin both).
INTERACT = """
<script>
(function(){
  var MODAL_HTML = '<div class="mm-overlay" id="mismatch" hidden>'
    + '<div class="mm-box">'
    + '<div class="ev-label">A useful next step</div>'
    + '<h3>Your birth time may need checking.</h3>'
    + '<p>Even a small difference in birth time can change the ascendant and house '
    + 'positions, which can affect the timing of a reading. That does not prove the '
    + 'birth time is wrong — but it is a common place to look when a reading feels off.</p>'
    + '<p>Three ways forward:</p>'
    + '<ol class="mm-routes">'
    + '<li><b>Birth-time rectification</b>. Test candidate minutes against dates from your life.</li>'
    + '<li><b>Ask a question instead</b>. Horary needs no birth time.</li>'
    + '<li><b>Read your palms</b>. Needs no birth data.</li>'
    + '</ol>'
    + '<div class="mm-actions">'
    + '<a class="cta-dark" href="#" data-nav="btr">Fix my birth time</a>'
    + '<a class="cta-light" href="#" data-nav="horary">Ask a question instead</a>'
    + '<a class="cta-light" href="#" data-nav="read">Read my palms</a>'
    + '</div>'
    + '<button type="button" class="mm-close" data-close="1">Close</button>'
    + '</div></div>';
  function thanksNear(el, msg){
    var ask = el && el.closest('.present-ask, .recog-ask');
    if(!ask) return;
    ask.querySelectorAll('.pillbtn').forEach(function(b){ b.disabled = true; });
    el.classList.add('on');
    var t = ask.parentNode.querySelector('.feedback-thanks');
    if(!t){
      t = document.createElement('div');
      t.className = 'feedback-thanks';
      ask.insertAdjacentElement('afterend', t);
    }
    t.textContent = msg;
  }
  function ensureMismatch(){
    var m = document.getElementById('mismatch');
    if(m) return m;
    document.body.insertAdjacentHTML('beforeend', MODAL_HTML);
    return document.getElementById('mismatch');
  }
  function showMismatch(){
    var m = ensureMismatch();
    if(m) m.hidden = false;
  }
  function hideMismatch(){
    var m = document.getElementById('mismatch');
    if(m) m.hidden = true;
  }
  function navigate(target){
    var view = 'astro', pane = target;
    if(target === 'read' || target === 'palm'){ view = 'read'; pane = null; }
    else if(target === 'horary' || target === 'question'){ pane = 'horary'; }
    else if(target === 'btr'){ pane = 'btr'; }
    try{
      parent.postMessage({source:'graharekha', action:'navigate', view:view, pane:pane}, '*');
    }catch(e){}
    hideMismatch();
  }
  document.addEventListener('click', function(e){
    var btn = e.target.closest('[data-mm],[data-v],[data-close],[data-nav],[data-unlock],a[href="#unlock"]');
    if(!btn) return;
    e.preventDefault();
    if(btn.hasAttribute('data-close')){ hideMismatch(); return; }
    if(btn.hasAttribute('data-unlock') || btn.getAttribute('href') === '#unlock'){
      try{ parent.postMessage({source:'graharekha', action:'unlock'}, '*'); }catch(err){}
      return;
    }
    if(btn.hasAttribute('data-nav')){ navigate(btn.getAttribute('data-nav')); return; }
    var v = btn.getAttribute('data-mm') || btn.getAttribute('data-v');
    if(v === 'yes'){
      thanksNear(btn, 'Good. The chart is reading you correctly. Keep going.');
      return;
    }
    if(v === 'partly' || v === 'some' || v === 'no'){
      thanksNear(btn, 'Noted. If this does not feel right, your birth time may need checking.');
      showMismatch();
    }
  });
})();
</script>
"""


def esc(t: Any) -> str:
    return _html.escape(str(t or ""))


def lock_sections(rows: list[tuple[str, str]]) -> str:
    """Free-view teaser: real section titles, blurred placeholder bodies.

    ``rows`` is a list of ``(title, body)``. The title is the exact heading the
    paid report uses, so the free half reads as a blurred full document; the
    body is a generic, non-personal placeholder — never the real paid content,
    which the free render path never has in memory. The chip carries no
    ``data-unlock`` attribute; each report adds exactly one unlock CTA via
    :func:`buy_block`.
    """
    parts = []
    for title, body in rows:
        parts.append(
            '<section class="locked-section">\n'
            f'  <h3 class="sec">{_html.escape(str(title))}</h3>\n'
            '  <div class="lock-wrap">\n'
            f'    <div class="lock-blur">{body}</div>\n'
            '    <div class="lock-over"><span class="lock-chip">Locked &#183; '
            'in the full reading</span></div>\n'
            '  </div>\n'
            '</section>')
    return "\n".join(parts)


def buy_block(title: str, text: str, *, price: int | None = None,
              cta: str = "Unlock full reading") -> str:
    """The single unlock CTA. ``data-unlock`` posts ``{action:'unlock'}`` to the
    parent page, which opens the site's pay card for this report."""
    price_bit = f" — ₹{int(price)}" if price else ""
    return (
        '<div class="buy">\n'
        f'  <h3>{_html.escape(title)}</h3>\n'
        f'  <p>{_html.escape(text)}</p>\n'
        f'  <a class="cta" href="#unlock" data-unlock="1">{_html.escape(cta)}'
        f'{price_bit}</a>\n'
        '</div>')


# ---------------------------------------------------------------------------
# section navigation
# ---------------------------------------------------------------------------
#: Reports run long — a paid chart reading is a dozen screens on a phone — and
#: until now the only way to reach the section you paid for was to scroll past
#: everything else. The nav is built from the headings already in the document
#: rather than declared per renderer, so every report gains it at once and none
#: of them can forget to update it.
SECTION_NAV_CSS = """
.secnav{--nav-w:210px}
.secnav ol{list-style:none;margin:0;padding:0}
.secnav a{display:block;text-decoration:none;color:var(--muted);font-size:.78rem;
line-height:1.35;padding:7px 10px;border-radius:8px;border-left:2px solid transparent}
.secnav a:hover{color:var(--ink);background:#f1efea}
.secnav a.here{color:var(--ink);background:#fff;border-left-color:var(--mixed);
font-weight:600}
.secnav .navlbl{font-size:.62rem;letter-spacing:.14em;text-transform:uppercase;
font-weight:700;color:var(--muted);padding:0 10px 8px}
.secnav li.lvl2 a{padding-left:22px;font-size:.74rem;color:#8b909c}
.secnav li.lvl2 a:hover,.secnav li.lvl2 a.here{color:var(--ink)}
@media(min-width:1080px){
  .secnav{position:fixed;top:0;left:50%;margin-left:-560px;width:var(--nav-w);
  max-height:100vh;overflow-y:auto;padding:44px 0 40px;z-index:20}
  .secnav::-webkit-scrollbar{width:6px}
  .secnav::-webkit-scrollbar-thumb{background:#e0ded8;border-radius:99px}
}
@media(max-width:1079px){
  .secnav{position:sticky;top:0;z-index:30;background:rgba(251,250,248,.94);
  backdrop-filter:blur(6px);border-bottom:1px solid var(--line);
  margin:0 -20px 4px;padding:8px 0}
  .secnav .navlbl{display:none}
  .secnav ol{display:flex;gap:6px;overflow-x:auto;padding:0 16px;
  scrollbar-width:none}
  .secnav ol::-webkit-scrollbar{display:none}
  .secnav li{flex:0 0 auto}
  .secnav a{white-space:nowrap;border-left:0;border-bottom:2px solid transparent;
  border-radius:0;padding:6px 4px;font-size:.75rem}
  .secnav li.lvl2 a{padding-left:4px}
  .secnav a.here{background:none;border-bottom-color:var(--mixed)}
}
@media print{.secnav{display:none}}
[id^="sec-"],[id^="domain-"]{scroll-margin-top:64px}
"""

SECTION_NAV_JS = """
<script>
(function(){
  var nav = document.querySelector('.secnav');
  if(!nav || !('IntersectionObserver' in window)) return;
  var links = {};
  Array.prototype.forEach.call(nav.querySelectorAll('a[href^="#"]'), function(a){
    links[a.getAttribute('href').slice(1)] = a;
  });
  var seen = [];
  var io = new IntersectionObserver(function(entries){
    entries.forEach(function(en){
      var id = en.target.id;
      var at = seen.indexOf(id);
      if(en.isIntersecting){ if(at < 0) seen.push(id); }
      else if(at >= 0){ seen.splice(at, 1); }
    });
    if(!seen.length) return;
    var top = null;
    Object.keys(links).forEach(function(id){
      if(seen.indexOf(id) >= 0 && top === null) top = id;
    });
    Object.keys(links).forEach(function(id){
      links[id].classList.toggle('here', id === top);
    });
    var cur = links[top];
    if(cur && nav.scrollWidth > nav.clientWidth){
      cur.scrollIntoView({block:'nearest', inline:'nearest'});
    }
  }, {rootMargin: '-64px 0px -70% 0px'});
  Object.keys(links).forEach(function(id){
    var el = document.getElementById(id);
    if(el) io.observe(el);
  });
})();
</script>
"""

#: Headings that name a section a reader would jump to. `h3.sec` is the card
#: reports' section heading; `h2` is the conversational one.
_NAV_HEADING = _re.compile(r"<(h2|h3)\b([^>]*)>(.*?)</\1>", _re.S | _re.I)
#: A life-area card is the destination most readers are actually looking for —
#: they bought the report for the career answer, not for the section above it.
_NAV_AREA = _re.compile(
    r'<article\b([^>]*\bclass="[^"]*\bcard\b[^"]*"[^>]*)>\s*'
    r'<div class="card-top">\s*<span class="area">(.*?)</span>',
    _re.S | _re.I)
#: Several reports label the section above the heading rather than in it.
#: "ABOUT YOU" is a better rail entry than the sentence it introduces.
_NAV_KICKER = _re.compile(
    r'<div class="[^"]*section-kicker[^"]*">([^<]{2,40})</div>\s*$', _re.I)
#: A few long-standing sections title themselves with a plain <h3> or a small
#: caps label rather than a section heading. They are destinations all the
#: same, so they are named here rather than by loosening the heading rule —
#: `.ev-label` alone appears dozens of times inside cards.
_NAV_SECTION = _re.compile(
    r'<section\b([^>]*\bclass="[^"]*\b'
    r'(?:remedy-card|proof|present-current|locked-preview|top-recognition)'
    r'\b[^"]*"[^>]*)>',
    _re.I)
_NAV_SECTION_TITLE = _re.compile(
    r'<h3\b[^>]*>(.*?)</h3>|<div class="[^"]*\bev-label\b[^"]*">([^<]{2,60})</div>',
    _re.S | _re.I)
_DETAILS_BLOCK = _re.compile(r"<details\b.*?</details>", _re.S | _re.I)
_HAS_CLASS_SEC = _re.compile(r'class\s*=\s*["\'][^"\']*\bsec\b', _re.I)
_HAS_ID = _re.compile(r'\bid\s*=\s*["\']([^"\']+)["\']', _re.I)
#: A heading may carry its own rail label when the full wording is too long to
#: sit in 210px: <h2 data-nav="Special marks">The special marks…</h2>
_NAV_OVERRIDE = _re.compile(r'\bdata-nav\s*=\s*["\']([^"\']+)["\']', _re.I)


def _nav_slug(text: str, taken: set[str]) -> str:
    plain = _ud.normalize("NFKD", text).encode("ascii", "ignore").decode()
    base = _re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:34] or "part"
    slug = f"sec-{base}"
    n = 2
    while slug in taken:
        slug = f"sec-{base}-{n}"
        n += 1
    taken.add(slug)
    return slug


def _nav_label(inner: str) -> str:
    text = _html.unescape(_re.sub(r"<[^>]+>", " ", inner))
    text = _re.sub(r"\s+", " ", text).strip(" .·—-")
    # Long headings are written to be read in place, not in a narrow rail. The
    # rail wraps to two lines, so the cut is generous enough to keep a whole
    # short sentence and only bites on headings that are really a paragraph.
    if len(text) > 34:
        cut = text[:34].rsplit(" ", 1)[0]
        text = (cut or text[:34]).rstrip(",;:") + "…"
    return text


def build_section_nav(body: str, *, label: str = "In this reading") -> tuple[str, str]:
    """Return ``(body_with_ids, nav_html)`` for a report body fragment.

    Headings inside ``<details>`` are skipped: those are the workings a reader
    opens from where they already are, not destinations.
    """
    if not body:
        return body, ""
    skip = [m.span() for m in _DETAILS_BLOCK.finditer(body)]

    def _inside_details(pos: int) -> bool:
        return any(start <= pos < end for start, end in skip)

    taken: set[str] = set(_re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', body))

    # (position, end of the open tag, open tag text, label, depth)
    found: list[tuple[int, int, str, str, str, int]] = []

    for m in _NAV_HEADING.finditer(body):
        tag, attrs = m.group(1).lower(), m.group(2)
        if _inside_details(m.start()):
            continue
        if tag == "h3" and not _HAS_CLASS_SEC.search(attrs):
            continue
        override = _NAV_OVERRIDE.search(attrs)
        if override:
            text = _html.unescape(override.group(1))
        else:
            kicker = _NAV_KICKER.search(body[max(0, m.start() - 320):m.start()])
            text = (_nav_label(kicker.group(1)).capitalize() if kicker
                    else _nav_label(m.group(3)))
        if not text:
            continue
        open_end = m.start() + len(f"<{tag}{attrs}>")
        found.append((m.start(), open_end, tag, attrs, text, 1))

    for m in _NAV_AREA.finditer(body):
        if _inside_details(m.start()):
            continue
        text = _nav_label(m.group(2))
        if not text:
            continue
        open_end = m.start() + len(f"<article{m.group(1)}>")
        found.append((m.start(), open_end, "article", m.group(1), text, 2))

    for m in _NAV_SECTION.finditer(body):
        if _inside_details(m.start()):
            continue
        title = _NAV_SECTION_TITLE.search(body[m.end():m.end() + 500])
        if not title:
            continue
        text = _nav_label(title.group(1) or title.group(2) or "")
        if not text:
            continue
        open_end = m.start() + len(f"<section{m.group(1)}>")
        found.append((m.start(), open_end, "section", m.group(1), text, 1))

    found.sort(key=lambda item: item[0])

    entries: list[tuple[str, str, int]] = []
    out: list[str] = []
    cursor = 0
    labelled: set[str] = set()
    for start, open_end, tag, attrs, text, depth in found:
        if start < cursor:
            continue
        # A named section and the heading inside it carry the same words, and
        # the rail would offer the reader the same destination twice. The
        # section wins because its anchor sits above the heading.
        if text.lower() in labelled:
            continue
        labelled.add(text.lower())
        existing = _HAS_ID.search(attrs)
        if existing:
            anchor = existing.group(1)
            open_tag = f"<{tag}{attrs}>"
        else:
            anchor = _nav_slug(text, taken)
            open_tag = f'<{tag}{attrs} id="{anchor}">'
        entries.append((anchor, text, depth))
        out.append(body[cursor:start])
        out.append(open_tag)
        cursor = open_end
    out.append(body[cursor:])

    # Two links is a heading, not a table of contents.
    if len(entries) < 3:
        return body, ""

    items = "".join(
        f'<li class="lvl{d}"><a href="#{esc(a)}">{esc(t)}</a></li>'
        for a, t, d in entries)
    nav = (f'<nav class="secnav" aria-label="Report sections">'
           f'<div class="navlbl">{esc(label)}</div><ol>{items}</ol></nav>')
    return "".join(out), nav


def inject_section_nav(doc: str, *, label: str = "In this reading") -> str:
    """Add the section rail to a finished HTML document.

    Runs on the assembled document so reports that build their own shell get the
    same rail as the ones that call `page()`, and so it lands after the customer
    sanitizers rather than being scrubbed by them.
    """
    if not doc or "secnav" in doc:
        return doc
    match = _re.search(r"(<body[^>]*>)(.*)(</body>)", doc, _re.S | _re.I)
    if not match:
        return doc
    open_tag, body, close_tag = match.groups()
    new_body, nav = build_section_nav(body, label=label)
    if not nav:
        return doc
    style = f"<style>{SECTION_NAV_CSS}</style>"
    if not _re.search(r"</head>", doc, _re.I):
        nav = style + nav
        style = ""
    out = (doc[:match.start()]
           + open_tag + nav + new_body + SECTION_NAV_JS + close_tag
           + doc[match.end():])
    if style:
        out = _re.sub(r"</head>", style + "</head>", out, count=1, flags=_re.I)
    return out


def page(title: str, body: str, *, eyebrow: str = "", heading: str = "",
         sub: str = "", disclaimer: bool = True, nav: bool = True) -> str:
    """Wrap a fragment in the standard report document."""
    head = ""
    if eyebrow or heading or sub:
        head = (f'<div class="tabhead">'
                + (f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else "")
                + (f"<h1>{esc(heading)}</h1>" if heading else "")
                + (f'<p class="sub">{esc(sub)}</p>' if sub else "")
                + "</div>")
    foot = ""
    if disclaimer:
        foot = ('<footer class="fine">For guidance and self-reflection only. '
                "Astrology, palmistry and numerology are traditional practices "
                "and are not scientifically validated methods of prediction. "
                "Not a substitute for medical, legal, financial or "
                "psychological advice. We never estimate anyone's remaining "
                "years. GrahaRekha · graharekha.com</footer>")
    rail = ""
    if nav:
        body, rail = build_section_nav(body)
    doc = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
           f"<title>{esc(title)}</title>{FONTS}"
           f"<style>{STYLE}{EXTRA}{SECTION_NAV_CSS if rail else ''}</style>"
           f"</head><body>{rail}"
           f'<div class="wrap">{head}{body}{foot}</div>{INTERACT}')
    return doc + (SECTION_NAV_JS if rail else "") + "</body></html>"
