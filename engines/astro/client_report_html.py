#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""User-friendly HTML sections for confluence + client hub reports."""
from __future__ import annotations

import html
import re
from datetime import date, datetime
from typing import Any, Optional

from confluence_longevity_lane import (
    LongevityContext,
    build_longevity_context,
    classify_ad_risk,
    health_light_for_risk,
    _ad_window,
    _parse_date_short,
)

DOMAIN_CLIENT = {
    "career": "Career & Profession",
    "finance": "Wealth & Finances",
    "marriage": "Partnership & Marriage",
    "children": "Children & Creativity",
    "health": "Health & Vitality",
    "property": "Home & Property",
    "travel": "Travel & Purpose",
    "spiritual": "Inner Life",
    "personality": "Who You Are",
    "current": "Right Now",
    "father": "Father & Authority",
    "mother": "Mother & Roots",
    "family": "Family Bonds",
    "future": "Road Ahead",
}


def _e(s) -> str:
    return html.escape(str(s))


# Plain-English swaps for any astrology labels that leak in from shared
# engines (e.g. the gemstone module). Keeps the reader in everyday language.
_HUMANIZE_REMEDY = (
    (re.compile(r"Lagna lord \(H1\)", re.I), "your ruling planet"),
    (re.compile(r"\bH1 lord\b", re.I), "your ruling planet"),
    (re.compile(r"\bLagna lord\b", re.I), "your ruling planet"),
    (re.compile(r"Current antardasha lord", re.I), "the planet guiding this phase"),
    (re.compile(r"\bantardasha lord\b", re.I), "phase planet"),
    (re.compile(r"\bMahadasha lord\b", re.I), "the planet of your current life chapter"),
    (re.compile(r"Current dasha:", re.I), "Current life chapter:"),
    (re.compile(r"\(AD until", re.I), "(this phase runs until"),
    (re.compile(r"favourable antardasha", re.I), "a more favourable phase"),
    (re.compile(r"\bantardasha\b", re.I), "phase"),
    (re.compile(r"\bmahadasha\b", re.I), "life chapter"),
    (re.compile(r"\bgraha balance\b", re.I), "overall balance"),
    (re.compile(r"\brules?\d+:?\s*", re.I), ""),
    (re.compile(r"(rules?/)?occupies\s+dusthana\s+H?\d+", re.I), "sits in a challenging part of your chart"),
    (re.compile(r"\bdusthana\s+H?\d+", re.I), "a challenging area"),
    (re.compile(r"\bdusthana\b", re.I), "challenging area"),
    (re.compile(r"debilitated during active (dasha|life chapter)", re.I), "weak during your current chapter"),
    (re.compile(r"\bdebilitated\b", re.I), "weak"),
    (re.compile(r"\bmaraka[- ]awareness window\b", re.I), "health-sensitive window"),
    (re.compile(r"\bmaraka\b", re.I), "health-sensitive"),
    (re.compile(r"\bMrtyunjaya\b", re.I), "Mrityunjaya"),
    (re.compile(r"\.\s*Source:[^<.]*\.", re.I), "."),
)


def humanize_remedy_html(raw: str) -> str:
    """Strip stray astrology jargon from engine-generated remedy/gemstone HTML."""
    if not raw:
        return raw
    out = raw
    for pat, repl in _HUMANIZE_REMEDY:
        out = pat.sub(repl, out)
    return out


def client_css() -> str:
    return """
:root {
  --ink:#1c1c28; --soft:#f4f1ec; --card:#fff; --border:#ddd5cb;
  --accent:#4a3f6b; --green:#1f6b42; --amber:#b86b00; --red:#a82828;
  --muted:#64647a; --blue:#1a5f8a;
}
* { box-sizing:border-box; }
body { font-family: Georgia, 'Palatino Linotype', serif; background:var(--soft); color:var(--ink); margin:0; line-height:1.72; }
.wrap { max-width:860px; margin:0 auto; padding:28px 18px 64px; }
.hero { background:linear-gradient(145deg,#1a1530,#3d3560); color:#f8f5f0; padding:34px 30px; border-radius:12px; margin-bottom:22px; }
.hero h1 { margin:0 0 6px; font-size:1.85rem; font-weight:400; }
.hero .tag { opacity:.85; font-size:1.02rem; margin-bottom:14px; }
.hero .meta { display:flex; flex-wrap:wrap; gap:14px; font-size:.82rem; opacity:.78; }
.note { background:#fff8e6; border-left:4px solid var(--amber); padding:12px 16px; border-radius:8px; margin-bottom:20px; font-size:.9rem; }
.section-h { font-size:1.15rem; color:var(--accent); margin:28px 0 12px; padding-bottom:6px; border-bottom:2px solid var(--accent); font-weight:600; }
.card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:20px 22px; margin-bottom:16px; }
.card h3 { margin:0 0 8px; font-size:1.05rem; font-weight:600; color:var(--ink); }
.card .when { font-size:.82rem; color:var(--muted); margin-bottom:8px; letter-spacing:.02em; }
.card .body { margin:0; font-size:.98rem; }
.card.green { border-left:4px solid var(--green); }
.card.amber { border-left:4px solid var(--amber); }
.card.red { border-left:4px solid var(--red); }
.card.blue { border-left:4px solid var(--blue); }
.pill { display:inline-block; font-size:.72rem; font-weight:600; padding:3px 10px; border-radius:20px; margin-top:10px; }
.pill.hi { background:#d8f0e0; color:var(--green); }
.pill.mid { background:#fdebd0; color:var(--amber); }
.pill.lo { background:#ececf0; color:var(--muted); }
.bullets { margin:0; padding-left:0; list-style:none; }
.bullets li { margin:10px 0; padding-left:1.4rem; position:relative; }
.bullets li::before { content:"\\25C6"; position:absolute; left:0; color:var(--accent); font-size:.75rem; top:.15rem; }
.tl { width:100%; border-collapse:collapse; font-size:.88rem; margin-top:8px; }
.tl th, .tl td { border:1px solid var(--border); padding:8px 10px; text-align:left; vertical-align:top; }
.tl th { background:#f0ebe4; font-weight:600; }
.dot-g { color:var(--green); font-weight:700; }
.dot-a { color:var(--amber); font-weight:700; }
.dot-r { color:var(--red); font-weight:700; }
.grid2 { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:640px) { .grid2 { grid-template-columns:1fr; } }
.fine { font-size:.82rem; color:var(--muted); margin-top:10px; }
.remedy { background:#f6f2fa; border-radius:8px; padding:10px 14px; margin-top:12px; font-size:.9rem; }
.footer { margin-top:36px; padding-top:16px; border-top:1px solid var(--border); font-size:.82rem; color:var(--muted); }
.nature-row { display:flex; gap:12px; margin:10px 0; align-items:flex-start; }
.nature-icon { width:1.4rem; flex-shrink:0; color:var(--accent); }
.nature-text { flex:1; font-size:.96rem; }
.past-card { margin:12px 0; padding:12px 0; border-bottom:1px dashed var(--border); }
.past-label { font-size:.82rem; color:var(--muted); margin-bottom:4px; font-weight:600; }
"""


def floating_toc_html() -> str:
    """
    Self-contained section navigation pane for big reports. Drop the returned
    markup just before </body>; a small script scans the page's h1/h2 headings,
    builds a clickable side pane, smooth-scrolls on click, highlights the active
    section on scroll, and collapses to a hamburger on narrow screens.

    Fixes vs original:
    - Hash-on-load: scrolls to #sec-N-slug after JS assigns IDs (browser fires
      hash before JS runs so native scroll always misses).
    - Mobile close: tap-backdrop and × button close the pane on phones/tablets.
    - Touch-friendly: 48px min tap targets on the toggle button.
    No dependencies; safe to inject into any report HTML document.
    """
    return """
<style>
:root{ --toc-w:240px; }
#toc-pane{position:fixed;top:0;left:0;width:var(--toc-w);height:100vh;overflow-y:auto;
  background:#ffffff;border-right:1px solid #ddd5cb;padding:14px 12px 32px;box-sizing:border-box;
  z-index:9999;font-family:system-ui,'Segoe UI',Arial,sans-serif;font-size:.86rem}
#toc-pane-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
#toc-pane-header h4{margin:0;font-size:.74rem;text-transform:uppercase;letter-spacing:.08em;color:#9a93a8}
#toc-close{display:none;background:none;border:none;cursor:pointer;font-size:1.3rem;color:#9a93a8;
  padding:4px 6px;line-height:1;border-radius:6px}
#toc-close:hover{background:#f3f1f7;color:#333}
#toc-pane a{display:block;padding:8px 9px;margin:2px 0;color:#3a3a4a;text-decoration:none;border-radius:7px;
  line-height:1.35;border-left:3px solid transparent;overflow:hidden;text-overflow:ellipsis;
  min-height:36px;display:flex;align-items:center}
#toc-pane a:hover{background:#f3f1f7}
#toc-pane a.active{background:#efeaf6;border-left-color:#b0106b;color:#111;font-weight:600}
#toc-pane a.lvl1{font-weight:700;color:#2a2440}
#toc-pane a.lvl2{padding-left:18px;color:#55556a;font-size:.83rem}
body.has-toc{margin-left:var(--toc-w)}
#toc-toggle{position:fixed;top:14px;left:14px;z-index:10000;background:#b0106b;color:#fff;border:none;
  border-radius:10px;padding:10px 14px;cursor:pointer;font-size:1rem;line-height:1;display:none;
  box-shadow:0 2px 10px rgba(0,0,0,.28);min-width:48px;min-height:48px;touch-action:manipulation}
#toc-backdrop{display:none;position:fixed;inset:0;z-index:9998;background:rgba(0,0,0,.35)}
@media(max-width:980px){
  body.has-toc{margin-left:0}
  #toc-pane{transform:translateX(-102%);transition:transform .25s ease;box-shadow:3px 0 20px rgba(0,0,0,.22)}
  #toc-pane.open{transform:translateX(0)}
  #toc-toggle{display:flex;align-items:center;justify-content:center}
  #toc-close{display:block}
  #toc-backdrop.open{display:block}
}
@media print{ #toc-pane,#toc-toggle,#toc-backdrop{display:none!important} body.has-toc{margin-left:0!important} }

/* ── Mobile / small-screen rendering (phones, in-app browser) ───────── */
.tbl-scroll{max-width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch}
@media(max-width:760px){
  html,body{max-width:100%;overflow-x:hidden}
  .wrap,.container,main{padding-left:14px!important;padding-right:14px!important}
  .hero{padding:20px 16px!important}
  .hero h1{font-size:1.45rem!important;line-height:1.25}
  h1{font-size:1.4rem!important}
  h2,.section-h{font-size:1.08rem!important}
  img,svg,canvas{max-width:100%!important;height:auto}
  table{font-size:.82rem}
  .grid2,.grid3,.grid4,.daily-grid,.downloads-grid,.individual-grid,
  .two-col,.cols,.cards{grid-template-columns:1fr!important;display:grid}
  pre,code{white-space:pre-wrap;word-break:break-word}
  .card{padding:14px 14px!important}
}
@media(max-width:420px){
  .wrap,.container,main{padding-left:10px!important;padding-right:10px!important}
  table{font-size:.78rem}
}
</style>
<div id="toc-backdrop"></div>
<button id="toc-toggle" aria-label="Report sections">&#9776; Sections</button>
<nav id="toc-pane" aria-label="Report sections">
  <div id="toc-pane-header"><h4>Jump to</h4><button id="toc-close" aria-label="Close">&#10005;</button></div>
  <div id="toc-links"></div>
</nav>
<script>
(function(){
  // Guarantee a mobile viewport so width-based CSS applies on phones even if
  // a report template forgot the <meta> tag.
  try{
    if(!document.querySelector('meta[name="viewport"]')){
      var mv=document.createElement('meta');mv.name='viewport';
      mv.content='width=device-width, initial-scale=1';
      (document.head||document.documentElement).appendChild(mv);
    }
  }catch(e){}

  // Wrap every table in a horizontal-scroll container so wide tables never
  // break the mobile layout (runs regardless of how many headings exist).
  try{
    [].slice.call(document.querySelectorAll('table')).forEach(function(t){
      var p=t.parentNode;
      if(p&&p.className==='tbl-scroll')return;
      var w=document.createElement('div');w.className='tbl-scroll';
      p.insertBefore(w,t);w.appendChild(t);
    });
  }catch(e){}

  function slug(t,i){return 'sec-'+i+'-'+String(t||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/(^-|-$)/g,'').slice(0,48);}
  var heads=[].slice.call(document.querySelectorAll('h1,h2')).filter(function(h){
    return h.textContent.trim() && !h.closest('#toc-pane');});
  var box=document.getElementById('toc-links'),pane=document.getElementById('toc-pane'),
      tgl=document.getElementById('toc-toggle'),bdrop=document.getElementById('toc-backdrop'),
      cls=document.getElementById('toc-close'),links=[];

  if(heads.length<2){
    if(pane){pane.style.display='none';}
    if(tgl){tgl.style.display='none';}
    if(bdrop){bdrop.style.display='none';}
    return;
  }

  function openPane(){pane.classList.add('open');bdrop.classList.add('open');}
  function closePane(){pane.classList.remove('open');bdrop.classList.remove('open');}

  heads.forEach(function(h,i){
    if(!h.id){h.id=slug(h.textContent,i);}
    var a=document.createElement('a');
    a.href='#'+h.id;
    a.textContent=h.textContent.trim().replace(/\\s+/g,' ');
    a.className=(h.tagName==='H1'?'lvl1':'lvl2');
    a.addEventListener('click',function(e){e.preventDefault();
      h.scrollIntoView({behavior:'smooth',block:'start'});
      if(window.innerWidth<=980){closePane();}
      history.replaceState(null,'','#'+h.id);});
    box.appendChild(a);links.push({a:a,h:h});
  });

  document.body.classList.add('has-toc');
  tgl.addEventListener('click',function(){pane.classList.contains('open')?closePane():openPane();});
  if(cls){cls.addEventListener('click',closePane);}
  if(bdrop){bdrop.addEventListener('click',closePane);}

  // Scroll to URL hash after IDs are assigned (browser fires hash before JS runs)
  var hash=window.location.hash;
  if(hash){
    var target=links.filter(function(l){return '#'+l.h.id===hash;})[0];
    if(target){setTimeout(function(){target.h.scrollIntoView({behavior:'smooth',block:'start'});spy();},80);}
  }

  var ticking=false;
  function spy(){ticking=false;var y=window.scrollY+96,cur=null;
    links.forEach(function(l){if(l.h.getBoundingClientRect().top+window.scrollY<=y){cur=l;}});
    links.forEach(function(l){l.a.classList.toggle('active',l===cur);});}
  window.addEventListener('scroll',function(){if(!ticking){requestAnimationFrame(spy);ticking=true;}},{passive:true});
  spy();
})();
</script>"""


def inject_section_nav(html: str) -> str:
    """
    Idempotently add the clickable section pane to a full HTML document.
    Safe to call on any report string: it inserts the pane before the first
    </body> only if one exists and the pane isn't already present.
    """
    if not html or 'id="toc-pane"' in html or "</body>" not in html:
        return html
    return html.replace("</body>", floating_toc_html() + "</body>", 1)


# ─────────────────── Author / source / proof sanitiser ─────────────────────
# Reports must read as plain predictions. The underlying technique names and
# book sources stay in the engines for computation, but they must NOT surface
# in the client HTML. Modern method authors are masked; the two private
# composite lanes are renamed; classical systems (Jaimini, Ashtakavarga,
# Bhrigu/BNN, Vimshottari, Yogini, KP, Navamsha, Parashara) are left intact.
#
# IMPORTANT: token replacement runs on the final HTML, so the client's own
# name is masked out first (a user really can be surnamed "Mehta"/"Bhardwaj"),
# then restored — only genuine author mentions get rewritten.

# 1) Structural citation/proof blocks — removed wholesale.
_CITE_BLOCKS = (
    re.compile(r'<ul class="aspect-cites">.*?</ul>', re.S | re.I),
    re.compile(r'<span class="src">.*?</span>', re.S | re.I),
    re.compile(r'<span class="quote">.*?</span>', re.S | re.I),
)
# 2) Parentheticals that are pure citations (carry a page ref or a rulesNN id).
_CITE_PARENS = (
    re.compile(r"\s*\([^()]*\bp\.?\s*\d[^()]*\)"),
    re.compile(r"\s*\([^()]*\brules?\d+[^()]*\)", re.I),
)
# 3) "Source(s)/Reference(s)/Citation(s): …" run-on text up to the next tag.
_CITE_LABELS = re.compile(
    r"\s*\b(?:sources?|references?|citations?)\s*:\s*[^<]*", re.I
)
# 4) Leftover technique-file tokens.
_CITE_TOKENS = (
    re.compile(r"\brules?\d+[a-z]*\b", re.I),
    re.compile(r"\bMODERN TECHNIQUES(?:\.pdf)?\b", re.I),
    re.compile(r"\bOCR(?:\s+corpus)?\b", re.I),
    re.compile(r"\b[\w-]+\.(?:pdf|md|txt|json)\b", re.I),
    re.compile(r"\s*\((?:reference|references|book citation below)\)", re.I),
)
# 4b) Code / model / LLM mentions — reports never name the tooling. Order
#     matters: drop the parenthetical "(no LLM)" forms before bare tokens.
_TECH_TOKENS = (
    re.compile(r"\s*[·•]\s*no\s*LLM\b", re.I),
    re.compile(r"\s*\((?:no|not)\s*LLM(?:\s*prose)?\)", re.I),
    re.compile(r"\bno\s*LLM(?:\s*prose)?\b", re.I),
    re.compile(r"\bGenerated by\s+palm_api\b", re.I),
    re.compile(r"\ball-MiniLM-L6-v2\b", re.I),
    re.compile(r"\bMiniLM\b", re.I),
    re.compile(r"\bPyJHora\b", re.I),
    re.compile(r"\bpalm_api\b", re.I),
    re.compile(r"\bLLM\b"),
)
# 5) Author / book-name masking. Longer names first; classical names omitted.
#    (key, replacement) — applied with word boundaries, case-sensitive on the
#    proper noun to avoid hitting ordinary words.
_AUTHOR_SUBS = (
    (r"Krishan\s+Kant\s+Bhardwaj", "Vedic Confluence 2"),
    (r"M\.?\s*S\.?\s*Mehta", "Vedic Confluence 1"),
    (r"\bMehta\b", "Vedic Confluence 1"),
    (r"\bBhardwaj\b", "Vedic Confluence 2"),
    (r"Dr\.?\s*K\.?\s*Guru\s+Rajesh", "the Nāḍī method"),
    (r"\bGuru\s+Rajesh\b", "the Nāḍī method"),
    (r"\bMarc\s+Boney\b", "the classical method"),
    (r"\bBoney\b", "the classical method"),
    (r"\bGoel\b", "the classical text"),
    (r"\bAvasthi\b", "the classical text"),
    (r"\bBoland\b", "the lunar tradition"),
    (r"\bAnthony\s+Louis\b", "classical horary"),
    (r"\bWilliam\s+Lilly\b", "classical horary"),
    (r"\bLilly\b", "classical horary"),
    (r"\bLouis\b", "classical horary"),
    (r"\bSaint-?Germain\b", "traditional palmistry"),
    (r"\bCheiro\b", "traditional palmistry"),
    (r"\bBenham\b", "traditional palmistry"),
    (r"Saraswati\s+Astro-?Palmistry", "traditional palmistry"),
)
_AUTHOR_SUBS = tuple((re.compile(p), r) for p, r in _AUTHOR_SUBS)

# Tidy-up after removals.
_TIDY = (
    (re.compile(r"\(\s*\)"), ""),
    (re.compile(r"\(\s*[,;]\s*"), "("),
    (re.compile(r"\s*[,;]\s*\)"), ")"),
    (re.compile(r"\s*,\s*\."), "."),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\s+([.,;:)])"), r"\1"),
    (re.compile(r"\(\s+"), "("),
    (re.compile(r"\s+\)"), ")"),
)


def strip_attributions(html: str, client_name: str = "") -> str:
    """
    Remove author names, book sources, and proof/citation blocks from finished
    report HTML, leaving only the prediction text. The client's own name is
    protected so a user surnamed like an author is never rewritten.

    Script and style blocks are shielded first — the tidy rules that strip empty
    parentheses ``()`` would otherwise break sidebar JavaScript (``trim()``,
    ``function(){`` …).
    """
    if not html:
        return html

    protected: list[str] = []

    def _shield(m: re.Match) -> str:
        protected.append(m.group(0))
        return f"\x00BLOCK{len(protected) - 1}\x00"

    out = html
    for pat in (
        re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I),
        re.compile(r"<style\b[^>]*>.*?</style>", re.S | re.I),
    ):
        out = pat.sub(_shield, out)

    # Protect the client name (and its escaped form) from author rewrites.
    guards: list[tuple[str, str]] = []
    for i, nm in enumerate({n for n in (client_name, html_escape_safe(client_name)) if n and len(n) >= 2}):
        token = f"\x00CN{i}\x00"
        if nm in out:
            out = out.replace(nm, token)
            guards.append((token, nm))

    for pat in _CITE_BLOCKS:
        out = pat.sub("", out)
    for pat in _CITE_PARENS:
        out = pat.sub("", out)
    out = _CITE_LABELS.sub("", out)
    for pat in _CITE_TOKENS:
        out = pat.sub("", out)
    for pat in _TECH_TOKENS:
        out = pat.sub("", out)
    for pat, repl in _AUTHOR_SUBS:
        out = pat.sub(repl, out)
    for pat, repl in _TIDY:
        out = pat.sub(repl, out)

    for token, nm in guards:
        out = out.replace(token, nm)
    for i, block in enumerate(protected):
        out = out.replace(f"\x00BLOCK{i}\x00", block)
    return out


def html_escape_safe(s: Any) -> str:
    try:
        return html.escape(str(s)) if s else ""
    except Exception:
        return ""


def finalize_report_html(html_doc: str, client_name: str = "") -> str:
    """
    One call to make a report client-ready: strip author/source/proof
    attributions, then add the section-navigation pane. Idempotent and safe to
    apply at every report's write step.
    """
    return inject_section_nav(strip_attributions(html_doc, client_name))


def confluence_css() -> str:
    return client_css() + """
.wrap { max-width:1040px; }
.section { margin:24px 0; }
.section h2 { color:var(--accent); font-size:1.2rem; border-bottom:2px solid var(--border); padding-bottom:6px; }
.verdict { background:#f8f6ff; border-left:4px solid var(--accent); padding:14px 16px; border-radius:8px; margin-top:12px; font-size:.94rem; }
table.methods { width:100%; border-collapse:collapse; font-size:.86rem; margin:10px 0; }
table.methods th, table.methods td { border:1px solid var(--border); padding:7px 9px; }
"""


def _conf_pill(n_systems: int, confidence: str) -> tuple[str, str]:
    c = confidence.upper()
    if c in ("VERY HIGH", "HIGH") or n_systems >= 5:
        return "hi", c if c != "SPECULATIVE" else "HIGH"
    if c == "MODERATE" or n_systems >= 3:
        return "mid", c
    return "lo", c


def _future_ads(pc: dict) -> list[dict]:
    return [
        a for a in pc.get("vimshottari", {}).get("current_md_antardashas", [])
        if a.get("status") in ("current", "future")
    ]


def transition_calendar_html(pc: dict) -> str:
    rows = ""
    for ad in _future_ads(pc)[:12]:
        lord = ad["ad_lord"]
        theme_map = {
            "Venus": "Partnership warmth, income polish, creative finish",
            "Ketu": "Quiet reset, skill depth, release old clutter",
            "Mercury": "Contracts, study, visible delivery",
            "Saturn": "Structure, proof, elder duties, health discipline",
            "Mars": "Drive, competition, body heat - pace yourself",
            "Jupiter": "Growth, learning, joint resources",
            "Moon": "Home rhythm, emotional load, preventive care",
            "Sun": "Visibility, authority, moderate workload",
            "Rahu": "Ambition with paperwork, network expansion",
        }
        theme = theme_map.get(lord, "Life recalibration and duty themes")
        rows += f"<tr><td>{_e(_ad_window(ad))}</td><td>{_e(theme)}</td></tr>"
    if not rows:
        return ""
    return f"""
<div class="section-h">Major Life Transitions (next chapters)</div>
<table class="tl"><thead><tr><th>Window</th><th>Plain-English theme</th></tr></thead><tbody>{rows}</tbody></table>
<p class="fine">Each row is a sub-chapter in your timeline - not a single-day event.</p>"""


def traffic_light_html(pc: dict, lctx: Optional[LongevityContext] = None) -> str:
    lctx = lctx or build_longevity_context(pc)
    today_yr = date.today().year
    rows = ""
    for yr in range(today_yr, today_yr + 7):
        mid = date(yr, 7, 1)
        ad = None
        md_lord = pc.get("vimshottari", {}).get("current_md", {}).get("md_lord", "")
        for a in _future_ads(pc):
            try:
                s = datetime.strptime(a["start"][:10], "%Y-%m-%d").date()
                e = datetime.strptime(a["end"][:10], "%Y-%m-%d").date()
            except ValueError:
                continue
            if s <= mid <= e:
                ad = a
                break
        if not ad:
            continue
        lord = ad["ad_lord"]
        _cls, _mb, risk, _theme = classify_ad_risk(pc, lord)
        if risk in ("High", "Highest"):
            dot, cls = "\u25cf", "dot-r"
            desc = "Go gently — rest well, get a check-up, don't overdo it"
        elif risk == "Moderate":
            dot, cls = "\u25cf", "dot-a"
            desc = "A mixed year — keep your routines steady"
        elif lord == "Venus":
            dot, cls = "\u25cf", "dot-g"
            desc = "Love and money both favour calm, steady moves"
        elif lord == "Ketu":
            dot, cls = "\u25cf", "dot-a"
            desc = "A quieter year — tidy up, rest, and prepare"
        elif lord in ("Mercury", "Jupiter"):
            dot, cls = "\u25cf", "dot-g"
            desc = "Good for deals, learning and getting things done"
        else:
            dot, cls = "\u25cf", "dot-g"
            desc = "A steady year — your usual good habits are enough"
        rows += f"<tr><td><strong>{yr}</strong></td><td class='{cls}'>{dot}</td><td>{_e(desc)}</td></tr>"
    return f"""
<div class="section-h">The Years Ahead, At a Glance</div>
<table class="tl"><thead><tr><th>Year</th><th style='width:40px'>Feel</th><th>In a nutshell</th></tr></thead><tbody>{rows}</tbody></table>
<p class="fine">Green is an easy, favourable year · amber means pace yourself · red simply means be kind to your health and don't rush big risks.</p>"""


def health_section_html(pc: dict, lctx: Optional[LongevityContext] = None, cluster_text: str = "") -> str:
    lctx = lctx or build_longevity_context(pc)
    vim = pc.get("vimshottari", {})
    ad = next((a for a in vim.get("current_md_antardashas", []) if a.get("status") == "current"), {})
    ad_rng = _ad_window(ad) if ad else "right now"

    now_card = """
<div class="card amber">
  <h3>How Your Health Feels Right Now</h3>
  <div class="when">""" + _e(ad_rng) + """</div>
  <p class="body">You're neither running on empty nor at peak fitness — it's a steady, look-after-yourself patch.
  Your body responds beautifully to rhythm: regular meals, sleep before midnight, and an honest check-up when work gets heavy.
  When you do feel run down, it's usually the weight of duty and stress talking — not some hidden weakness.</p>
</div>"""

    watch_lines = ""
    for w in lctx.health_watch_windows[:3]:
        watch_lines += (
            f"<li><strong>{_e(w)}</strong> — a season to slow down a little: get a check-up, sleep properly, "
            "and don't push through if your body asks for rest.</li>"
        )
    if not watch_lines and lctx.high_risk_ads:
        for ad in lctx.high_risk_ads[:3]:
            watch_lines += f"<li><strong>{_e(ad['window'])}</strong> — a good time to be kind to yourself and book that overdue check-up.</li>"
    watch_card = ""
    if watch_lines:
        watch_card = f"""
<div class="card blue">
  <h3>Times to Be Extra Kind to Your Body</h3>
  <ul class="bullets">{watch_lines}</ul>
  <p class="fine">These are gentle nudges to rest and get checked — not warnings to be afraid of. For any real symptom, see a doctor.</p>
</div>"""
    elif lctx.max_future_risk == "Low" and not lctx.critical_mb:
        watch_card = """
<div class="card green">
  <h3>Your Health Outlook</h3>
  <p class="body">The years just ahead look steady on the health front. Nothing alarming stands out — your usual good habits
  and a yearly check-up are plenty to keep you well.</p>
</div>"""

    prot = []
    pillar = pc.get("pillar", {})
    if pillar.get("lagna_lord_dignity") in ("exalted", "own_sign", "moolatrikona"):
        prot.append("You're built to recover well — when you actually rest, you bounce back faster than most people do.")
    if not lctx.critical_mb:
        prot.append("Nothing in your make-up suggests a fragile constitution — your baseline is solid and workable.")
    else:
        prot.append("A couple of areas just need steady, sensible habits — discipline, not worry, is all they ask of you.")
    prot_card = "<div class='card green'><h3>What's On Your Side (and Recovery)</h3><ul class='bullets'>"
    prot_card += "".join(f"<li>{_e(p)}</li>" for p in prot)
    prot_card += "<li>Bouncing back from an illness or a rough patch is genuinely one of your strengths — give yourself permission to rest fully and you heal well.</li>"
    if cluster_text:
        prot_card += f"<li>{_e(cluster_text[:220])}</li>"
    prot_card += "</ul></div>"

    return f"""
<div class="section-h">Your Health — Now &amp; The Near Future</div>
{now_card}
{watch_card}
{prot_card}"""


def seven_pillars_html(
    pc: dict,
    by_domain: dict[str, Any],
    lctx: Optional[LongevityContext] = None,
    *,
    personality_text: str = "",
) -> str:
    lctx = lctx or build_longevity_context(pc)
    lagna = pc["meta"]["lagna_sign"]
    moon = pc.get("planets", {}).get("Moon", {}).get("sign", "")

    def synth(dom: str, fallback: str) -> str:
        cl = by_domain.get(dom)
        if cl and getattr(cl, "affirmation", None):
            return cl.affirmation
        if cl and getattr(cl, "synthesis", None):
            return cl.synthesis
        return fallback

    pers_fallback = (
        f"You present as quick and verbal with {lagna} rising and a precise {moon} emotional core."
    )
    pers_body = personality_text.strip() if personality_text.strip() else synth("personality", pers_fallback)
    pillars = [
        ("Personality", pers_body),
        ("Profession", synth("career", "Public standing and craft mastery stay central - visibility rewards finished work.")),
        ("Wealth", synth("finance", "Money arrives in chapters; paperwork and patient compounding beat speculation.")),
        ("Spouse and relationships", synth("marriage", "Partnership quality reflects daily habits more than grand gestures.")),
        ("Children", synth("children", "Creative and parenting themes need patience - forcing timelines backfires.")),
        ("Health", synth("health", "Preventive rhythm beats heroic overwork; stress and digestion are the usual first signals.")),
        ("Longevity", (
            "Later-life mobility depends on habits you build now - walking, sleep, and annual labs. "
            + (
                lctx.plain_lines[0]
                if lctx.plain_lines
                else "No death timing is stated; this is wellness awareness only."
            )
        )),
    ]
    blocks = ""
    for title, body in pillars:
        sents = re.split(r"(?<=[.!?])\s+", body.strip())
        para = " ".join(sents[:4]) if sents else body
        blocks += f"<div class='card'><h3>{_e(title)}</h3><p class='body'>{_e(para)}</p></div>"
    return f"""
<div class="section-h">Seven Life Pillars (cross-checked summary)</div>
<div class="grid2">{blocks}</div>"""


def prediction_card(when: str, title: str, body: str, tone: str = "green", confidence: str = "MODERATE") -> str:
    pill_cls, pill_txt = _conf_pill(3, confidence)
    return f"""
<div class="card {tone}">
  <div class="when">{_e(when)}</div>
  <h3>{_e(title)}</h3>
  <p class="body">{_e(body)}</p>
  <span class="pill {pill_cls}">{_e(pill_txt)} confidence</span>
</div>"""


def remedies_html(
    pc: dict,
    lctx: Optional[LongevityContext] = None,
    *,
    question: str = "",
    domain: str = "",
) -> str:
    lctx = lctx or build_longevity_context(pc)
    gem_block = ""
    try:
        from gemstone_remedy import build_remedy_report, render_remedy_section_html
        gem_report = build_remedy_report(pc, question=question, domain=domain)
        gem_block = humanize_remedy_html(render_remedy_section_html(gem_report, compact=False))
    except Exception:
        gem_block = ""
    daily = [
        ("A few quiet minutes each morning", "Before the phone, before the rush — sit still for five minutes. It steadies the whole day, especially in heavier seasons."),
        ("One honest conversation a week", "Pick the person who matters most and really talk. Small, regular repair beats one big grand gesture every time."),
        ("Give a little, regularly", "A small act of generosity each week — time, money, or help — tends to lighten the load on the areas you worry about most."),
    ]
    life = [
        "Walk for 30 minutes in the morning, a few days a week.",
        "Book a proper check-up each year — and especially before the gentler health seasons above.",
        "Screens off by 10:30 PM when work is heavy; protect your sleep fiercely.",
        "Read anything you sign twice — slowly — before you commit, especially in big-money years.",
    ]
    d_html = "".join(f"<li><strong>{_e(t)}</strong> — {_e(b)}</li>" for t, b in daily)
    l_html = "".join(f"<li>{_e(x)}</li>" for x in life)
    return f"""
{gem_block}
<div class="section-h">Small Things That Genuinely Help</div>
<div class="grid2">
  <div class="card"><h3>Gentle Daily Habits</h3><ul class="bullets">{d_html}</ul></div>
  <div class="card"><h3>Practical Adjustments</h3><ul class="bullets">{l_html}</ul></div>
</div>"""
