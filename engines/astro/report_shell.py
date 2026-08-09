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
.evidence{border-top:1px solid var(--line);padding-top:10px;margin-top:4px}
.ev-label{font-size:.64rem;letter-spacing:.13em;text-transform:uppercase;
font-weight:600;color:var(--muted)}
.agree{float:right;font-size:.66rem;font-weight:600;color:var(--muted);
background:#f1efea;border-radius:99px;padding:2px 9px}
.evidence ul{margin:8px 0 0;padding-left:18px;font-size:.85rem;color:#3d4250}
.evidence li{margin:6px 0}
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
.remedy-dont,.stones-group.down{background:#fbeae6;border:1px solid #e8b6aa}
.remedy-do-label,.stones-group-label{font-size:.66rem;letter-spacing:.12em;
text-transform:uppercase;font-weight:700;margin:0 0 8px}
.remedy-do-label,.stones-group.up .stones-group-label{color:var(--up)}
.remedy-dont-label,.stones-group.down .stones-group-label{color:var(--down)}
.remedy-do p,.remedy-dont p{margin:0;font-size:.9rem;line-height:1.5}
ul.stones{list-style:none;margin:0;padding:0}
li.stone{background:#fff;border:1px solid var(--line);border-left-width:4px;
border-radius:10px;padding:12px 14px;margin:0 0 10px}
li.stone:last-child{margin-bottom:0}
li.stone.up{border-left-color:var(--up);background:#f3faf6}
li.stone.down{border-left-color:var(--down);background:#fff6f4}
li.stone.mixed{border-left-color:var(--down);background:#fff6f4}
.stone-top{display:flex;justify-content:space-between;gap:10px;align-items:baseline;
flex-wrap:wrap}
.stone-verdict{font-size:.68rem;font-weight:700;letter-spacing:.04em;
text-transform:uppercase}
li.stone.up .stone-verdict{color:var(--up)}
li.stone.down .stone-verdict,li.stone.mixed .stone-verdict{color:var(--down)}
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
"""

#: Click handlers for accuracy pills + mismatch modal. Reports are iframes, so
#: "go to BTR / horary / palm" is a postMessage to the host SPA (same origin
#: and Vercel→Railway cross-origin both).
INTERACT = """
<script>
(function(){
  var MODAL_HTML = '<div class="mm-overlay" id="mismatch" hidden>'
    + '<div class="mm-box">'
    + '<div class="ev-label">Then something upstream is wrong</div>'
    + '<h3>Most likely, your birth time is not accurate.</h3>'
    + '<p>This is the common case, not a rare one. Hospital records round to the '
    + 'nearest five or ten minutes, and families remember approximately. A '
    + '<b>twenty-minute error moves your rising sign</b>. Once that moves, '
    + 'every house shifts, so every prediction built on it shifts with it.</p>'
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
      thanksNear(btn, 'Noted. A wrong present reading usually means the birth time needs a check.');
      showMismatch();
    }
  });
})();
</script>
"""


def esc(t: Any) -> str:
    return _html.escape(str(t or ""))


def page(title: str, body: str, *, eyebrow: str = "", heading: str = "",
         sub: str = "", disclaimer: bool = True) -> str:
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
                "years. GrahaRekha · graharekha.co.in</footer>")
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
            f"<title>{esc(title)}</title>{FONTS}"
            f"<style>{STYLE}{EXTRA}</style></head><body>"
            f'<div class="wrap">{head}{body}{foot}</div>{INTERACT}</body></html>')
