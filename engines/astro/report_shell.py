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
.dodont div{background:#fff;border-radius:10px;padding:10px 12px;font-size:.84rem}
.dodont .t{font-size:.64rem;letter-spacing:.12em;text-transform:uppercase;
font-weight:600;margin-bottom:5px}
.do .t{color:var(--up)} .dont .t{color:var(--down)}
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
footer{margin-top:40px;font-size:.74rem;color:var(--muted);text-align:center}
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
                "years.</footer>")
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>'
            f'<meta name="viewport" content="width=device-width,initial-scale=1"/>'
            f"<title>{esc(title)}</title>{FONTS}"
            f"<style>{STYLE}{EXTRA}</style></head><body>"
            f'<div class="wrap">{head}{body}{foot}</div></body></html>')
