"""
astro_report_generator.py — Vedic Astrology Report Generator
=============================================================

Enter client birth data (DOB, time, place) + optional palm print images.
Charts are computed via PyJHora (no AstroSage PDF required).
Produces downloadable multi-lane reports including:

  1. Vedic_Confluence_<Name>_<Date>.html  — Technical multi-system analysis
  2. user_report_<name>.html              — Plain-English client-facing report
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

# Deterministic, rule-based report generators (replace the LLM for these lanes).
from numerology_report import generate_numerology_html
from vedic_bnn_report import generate_bnn_html
from vedic_bhardwaj_report import generate_bhardwaj_html
from vedic_ashtakavarga_report import generate_ashtakavarga_html
from vedic_jaimini_report import generate_jaimini_html
from vedic_kp_report import generate_kp_html
from vedic_rtvd_report import generate_rtvd_html
from vedic_longevity_report import generate_longevity_html
from vedic_blindchart_report import generate_blindchart_html
from vedic_pillar_report import generate_pillar_html
from vedic_vimshottari_report import generate_vimshottari_html
from vedic_yogini_report import generate_yogini_html
from vedic_confluence_report import generate_confluence_reports
from palm_api.pipeline import generate_lane_report
from combined_report import generate_combined_report
from daily_moon_prediction import compute_daily_moon_guide, load_pc_for_session
from daily_moon_report import write_daily_moon_report
try:
    from client_report_html import finalize_report_html
except Exception:  # pragma: no cover
    finalize_report_html = lambda h, client_name="": h  # noqa: E731
from muhurat_checker import check_muhurat, event_catalog, resolve_pc_for_muhurat
from muhurat_event_rules import event_requirements, get_event_rule
from kundali_match import build_person_chart, match_kundali, _slug as match_slug
from kundali_match_report import write_kundali_match_report
from cursor_confluence_chat import (
    CursorChatMemory,
    collect_lane_files,
    find_cursor_cmd,
    load_session_manifest,
    run_cursor_chat,
    run_cursor_human_report,
    save_session_manifest,
)
from server_urls import get_server_urls

# ─────────────────────────────── paths ───────────────────────────────
BASE_DIR     = Path(__file__).parent          # test8/ — the Cursor workspace
SESSIONS_DIR = BASE_DIR / "_astro_sessions"
REPORTS_DIR  = BASE_DIR / "reports"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TODAY = datetime.now().strftime("%Y%m%d")


def _reload_deterministic_modules() -> None:
    """Reload lane engines so on-disk fixes apply without restarting this server."""
    import importlib

    global generate_numerology_html, generate_bnn_html, generate_bhardwaj_html, generate_ashtakavarga_html
    global generate_jaimini_html, generate_kp_html, generate_rtvd_html
    global generate_longevity_html, generate_blindchart_html, generate_pillar_html
    global generate_vimshottari_html, generate_yogini_html, generate_confluence_reports
    global generate_lane_report, generate_combined_report

    import astro_precompute
    importlib.reload(astro_precompute)

    for mod_name in (
        "numerology_report",
        "vedic_bnn_report",
        "bnn_analysis",
        "bnn_human",
        "bnn_foundation",
        "bnn_chart_text",
        "bnn_combination",
        "bnn_book_data",
        "vedic_bhardwaj_report",
        "bhardwaj_semantic",
        "bhardwaj_prose",
        "vedic_ashtakavarga_report",
        "ashtakavarga_analysis",
        "ashtakavarga_book_data",
        "vedic_jaimini_report",
        "jaimini_books_merge",
        "jaimini_books_prose",
        "jaimini_books_analysis",
        "jaimini_books_chart",
        "jaimini_book_data",
        "jaimini_prose",
        "vedic_kp_report",
        "kp_analysis",
        "kp_human",
        "kp_foundation",
        "kp_chart_text",
        "kp_combination",
        "kp_book_data",
        "kp_chart",
        "vedic_rtvd_report",
        "rtvd_foundation",
        "rtvd_year",
        "rtvd_book_data",
        "vedic_longevity_report",
        "longevity_analysis",
        "longevity_book_data",
        "vedic_blindchart_report",
        "vedic_pillar_report",
        "vedic_vimshottari_report",
        "vim_mehta_merge",
        "mehta_analysis",
        "mehta_prose",
        "mehta_chart",
        "mehta_book_data",
        "mehta_semantic",
        "vedic_yogini_report",
        "vedic_confluence_report",
        "palm_api.analyzer",
        "palm_api.palm_lines",
        "palm_api.special_marks",
        "palm_api.confluence",
        "palm_api.conclusive",
        "palm_api.life_aspects",
        "palm_api.curated_rules",
        "palm_api.timing",
        "palm_api.pipeline",
        "astro_palmistry_engine",
        "astro_palmistry_phalange_cv",
        "astro_palmistry_longevity",
        "astro_palmistry_morphology",
        "astro_palmistry_book_cv",
        "astro_palmistry_zone_cv",
        "astro_palmistry_anchor_engine",
        "astro_palmistry_chart_lane",
        "astro_chart_bridge",
        "combined_report",
    ):
        if mod_name in sys.modules:
            importlib.reload(sys.modules[mod_name])

    from numerology_report import generate_numerology_html as _gen_num
    from vedic_bnn_report import generate_bnn_html as _gen_bnn
    from vedic_bhardwaj_report import generate_bhardwaj_html as _gen_bhardwaj
    from vedic_ashtakavarga_report import generate_ashtakavarga_html as _gen_ash
    from vedic_jaimini_report import generate_jaimini_html as _gen_jai
    from vedic_kp_report import generate_kp_html as _gen_kp
    from vedic_rtvd_report import generate_rtvd_html as _gen_rtvd
    from vedic_longevity_report import generate_longevity_html as _gen_long
    from vedic_blindchart_report import generate_blindchart_html as _gen_blind
    from vedic_pillar_report import generate_pillar_html as _gen_pillar
    from vedic_vimshottari_report import generate_vimshottari_html as _gen_vim
    from vedic_yogini_report import generate_yogini_html as _gen_yog
    from vedic_confluence_report import generate_confluence_reports as _gen_conf
    from palm_api.pipeline import generate_lane_report as _gen_palm
    from combined_report import generate_combined_report as _gen_combined

    generate_numerology_html = _gen_num
    generate_bnn_html = _gen_bnn
    generate_bhardwaj_html = _gen_bhardwaj
    generate_ashtakavarga_html = _gen_ash
    generate_jaimini_html = _gen_jai
    generate_kp_html = _gen_kp
    generate_rtvd_html = _gen_rtvd
    generate_longevity_html = _gen_long
    generate_blindchart_html = _gen_blind
    generate_pillar_html = _gen_pillar
    generate_vimshottari_html = _gen_vim
    generate_yogini_html = _gen_yog
    generate_confluence_reports = _gen_conf
    generate_lane_report = _gen_palm
    generate_combined_report = _gen_combined


# ─────────────────────── Cursor automation ────────────────────────────
class CursorAutomation:
    """Thin wrapper around cursor-agent CLI.

    Invocation (Linux/macOS):
        cursor-agent -p --yolo --trust --workspace <dir> [prompt]
    Prompt is written to a temp file and piped via stdin to avoid
    shell argument length limits.
    """

    def __init__(self):
        self.cmd = self._find_cmd()
        if self.cmd:
            logger.info(f"cursor-agent found: {self.cmd}")
        else:
            logger.warning("cursor-agent not found. Run: cursor agent  (first run auto-installs it)")

    def _find_cmd(self) -> Optional[str]:
        # Ensure ~/.local/bin is in PATH (Linux default install location)
        local_bin = os.path.expanduser("~/.local/bin")
        os.environ["PATH"] = local_bin + os.pathsep + os.environ.get("PATH", "")

        for name in ("cursor-agent", "agent"):
            p = shutil.which(name)
            if p:
                return p
        for p in (
            os.path.expanduser("~/.local/bin/cursor-agent"),
            os.path.expanduser("~/.local/bin/agent"),
            "/usr/local/bin/cursor-agent",
            "/usr/local/bin/agent",
        ):
            if os.path.exists(p) and os.access(p, os.X_OK):
                return p
        return None

    def send_prompt(self, cwd: str, prompt: str) -> bool:
        if not self.cmd:
            return False
        import tempfile
        fd, prompt_path = tempfile.mkstemp(suffix=".txt", prefix="astro_prompt_", text=True)
        fh = None
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(prompt)

            cmd = [
                self.cmd, "-p",
                "--yolo",
                "--trust",
                "--workspace", cwd,
            ]
            # Open file handle and keep it open until the process finishes.
            # Do NOT use a `with` block here — that would close fh the moment
            # Popen() returns (before the subprocess has read from stdin).
            fh = open(prompt_path, "r", encoding="utf-8")
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=fh,
                text=True,
                encoding="utf-8",
                cwd=cwd,
            )
            if proc.stdout:
                for line in proc.stdout:
                    logger.debug(f"[cursor] {line.rstrip()}")
            proc.wait()
            return proc.returncode == 0
        except Exception as e:
            logger.error(f"send_prompt error: {e}")
            return False
        finally:
            if fh:
                try:
                    fh.close()
                except Exception:
                    pass
            try:
                os.unlink(prompt_path)
            except Exception:
                pass

    def wait_for_done(self, done_path: str, max_minutes: int = 25) -> Optional[dict]:
        """Poll until DONE.json appears. Returns its content or None on timeout."""
        deadline = time.time() + max_minutes * 60
        while time.time() < deadline:
            if os.path.exists(done_path):
                try:
                    with open(done_path, encoding="utf-8") as f:
                        return json.load(f)
                except Exception:
                    pass
            time.sleep(8)
        return None

    def run(self, workspace: str, prompt: str, done_path: str, max_minutes: int = 25) -> Tuple[bool, Optional[dict]]:
        if not os.path.exists(workspace):
            logger.error(f"Workspace not found: {workspace}")
            return False, None
        ok = self.send_prompt(workspace, prompt)
        if not ok:
            logger.warning("cursor-agent returned non-zero; still polling for DONE.json…")
        result = self.wait_for_done(done_path, max_minutes)
        return (True, result) if result else (False, None)


_cursor = None
try:
    _cursor = CursorAutomation()
    if not _cursor.cmd:
        _cursor = None
except Exception:
    _cursor = None

# ──────────────────────── Cursor prompt ───────────────────────────────
ASTRO_SYSTEM_RULES = """\
=== HOW TO USE THIS SKILL — DEFAULT RULES ===

You are an expert Vedic astrologer operating inside the test8 workspace.
All skills, rules, and book OCR are already present in this directory.

PIPELINE AUTHORITY: .cursor/skills/vedic-report-prediction/SKILL.md
  — Read this file FIRST. The MANDATORY PIPELINE RULE section defines the
    complete 15-step execution sequence. Follow it without skipping any step.

BOOK CORPUS: rules1.md through rules38.md (growing)
  — Route each lane to its correct rules files per §E of the skill.
  — Never fabricate rules. If a rule is not in the corpus, say "not in corpus."

CRITICAL — NO GARBAGE CHARACTERS IN HTML OUTPUT:
  — NEVER use Sanskrit/IAST diacritical characters in any HTML output file.
  — These characters (ā ī ū ṣ ś ṭ ḍ ṇ ḥ ṅ ñ ṁ ṃ) get corrupted to "?" when written to disk.
  — Use plain ASCII equivalents ONLY:
      Mahadasha       (NOT Mahādaśā)
      Antardasha      (NOT Antardaśā)
      Vimshottari     (NOT Vimśottarī)
      Rashi           (NOT Rāśi)
      Lagna           (NOT Lagn / Lagnā)
      Karakamsha      (NOT Kārakāṃśa)
      Amatyakaraka    (NOT Amātyakāraka)
      Atmkaraka       (NOT Ātmakāraka)
      Chara           (NOT Cāra)
      Nakshatra       (NOT Nakṣatra)
      Dashamsha       (NOT Daśāṃśa)
      Navamsha        (NOT Navāṃśa)
      Saptamsha       (NOT Saptāṃśa)
  — Use HTML entities (&amp; &mdash; &middot;) for punctuation, NOT Unicode.
  — Test: if you see a character with a dot below/above or a macron over a vowel, REPLACE it.

CALIBRATION: If no life event data is provided, mark all reports UNCALIBRATED.
  — Still generate all reports. Add "⚠ Uncalibrated — first pass" to each header.
  — Add a calibration request block at the end of user_report.

INDIVIDUAL REPORTS: Each must be a FULL, DETAILED HTML report — they feed the confluence vote table.
  — Do NOT skip any lane unless its data is literally absent from the extract.
  — Mark any skipped lane in the confluence header.

CRITICAL — HOW TO WRITE REPORTS — QUALITY IS SEMANTIC, NOT LINE COUNT:
  — Write HTML files DIRECTLY using file write tools. DO NOT create Python scripts to generate HTML.
  — DO NOT create _generate_reports.py, helper scripts, or any intermediary code. Write the HTML now.
  — DO NOT repeat the same paragraph multiple times with "angle 1", "angle 2" etc. This is padding and is BANNED.
  — DO NOT use emoji characters anywhere in HTML reports. Emoji (🧠🏠✈️❤️⚡🟢🟡 etc.) render as "?" boxes on Linux/Windows
    without emoji fonts. Use plain Unicode symbols instead: ★ ● → ♦ ♥ ♠ ♣ ✦ ✧ ※ + ► ◄ • ◦ or text labels only.

  HUMAN ASTROLOGER VOICE & CONFIRMATION (all client HTML — see .cursor/skills/vedic-report-prediction/SKILL.md):
  — Write as ONE trusted reader explaining what **rules + extract + confluence** support for THIS person — not generic horoscope filler.
  — **Confirmatory:** strong claims need receipts (named chart fact, dated period, score, palm feature, cipher, or explicit multi-lane agreement in plain words on the user hub).
  — **Banned:** SaaS tone, motivational clichés, identical card templates, meta filler ("This section covers…"), fake accuracy percentages on the client hub.

  THE REAL QUALITY TEST — every report must pass this:
  A reviewer reads one randomly picked paragraph and asks "does this sentence ONLY make sense for THIS client's
  chart, or could it apply to any chart?" If it could apply to any chart → it is FILLER and the report FAILS.

  EVERY SENTENCE must contain at least one specific item from this list:
      • A named planet (e.g. "Mercury", "Saturn", "Rahu")
      • A specific house number (e.g. "10th house", "6th lord")
      • A specific sign (e.g. "Pisces", "Capricorn")
      • A specific date or age (e.g. "from Aug 2026", "age 41")
      • A specific score (e.g. "BAV score 4 bindus", "SAV 28")
      • A specific nakshatra (e.g. "Uttarabhada Pada 2")
      • A specific yoga or rule result (e.g. "Neecha Bhanga via Venus in kendra")

  EXAMPLES OF BANNED FILLER SENTENCES:
      ✗ "This is a favorable period for career growth and expansion."
      ✗ "The native's personality reflects strong leadership qualities."
      ✗ "This combination shows good potential for relationships."
      ✗ "angle 1... angle 2... angle 3..." (repeated paragraph)

  EXAMPLES OF REQUIRED SPECIFIC SENTENCES:
      ✓ "Mercury, lagna lord, sits debilitated in Pisces (10th house), but Neecha Bhanga fires because Venus exalts in the same sign — the debility converts to a career raja yoga."
      ✓ "Jupiter's BAV score in Gemini is 6 bindus (high), making the Aug 2026 transit ingress a strong career window."
      ✓ "Saturn Antardasha runs from March 2024 to April 2025; Saturn owns the 8th and 9th houses — this brought sudden changes in career direction while also enabling foreign or academic opportunities."

  GOLD STANDARD REFERENCES — all under reports/Ritz_reprot/ (Ritz client HTML family — copy scaffold + CSS):
      reports/Ritz_reprot/Vedic_Pillar_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_BNN_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_KP_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Jaimini_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Vimshottari_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Yogini_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Ashtakavarga_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_RTVD_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Longevity_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_BlindChart_Ritz_20260408.html
      reports/Ritz_reprot/Vedic_Confluence_Ritz_20260408.html
      reports/Ritz_reprot/Palmistry_Ritz_20260408.html
      reports/Ritz_reprot/Numerology_Ritz_19850308.html
      reports/Ritz_reprot/user_report_ritz.html       ← plain-English user hub

CONFLUENCE (TECHNICAL): {slug}/Vedic_Confluence_{slug}_{date}.html
  — Full vote table, confidence scores, all domains, remedies.
  — TIMING (vedic_confluence_skill.md Part 2A + Part 5 Step 0): Before any HIGH/VERY HIGH dated verdict, scan ALL book-sourced
    clocks that have extract data — Vimshottari, Yogini, KP (rules21), Jaimini Chara, RTVD, Ashtakavarga transit/BAV,
    Blind chart progression, BNN+extract dasha dates, Longevity/maraka, Pillar delivery, Goel D9/D10/D7/disease vargas,
    Numerology (if lane ran). List skips in header. Each yearly traffic-light row: cite >=2 timing families.
    Vote table: add Pillar + Blind Chart rows when those lane HTMLs exist.
  — MUST include: Character & Personality Profile section (6–8 traits, specific not generic)
  — MUST include: "Your Past — What the Chart Suggests" section (5+ past narrative points)
  — When Dashamamsha row exists: MUST include D10 career subsection (rules13.md) + vote row "Goel D10"
  — When Navamamsha row exists: MUST include D9 marriage subsection (rules3.md) + vote row "Goel D9" in spouse domain
  — When book_ocr/nakshatra_karmic_stories/*_ocr_full.txt exists: MUST include §3b Nakshatra karmic tale + vote row "KVS pada tale" (rules42.md)
  — Match layout + semantic depth of reports/Ritz_reprot/Vedic_Confluence_Ritz_20260408.html (vote tables, callouts, cards). Quality is semantic, not line count.
  — **Anti-padding:** no 100+ row month-by-month micro-task grids; cap any appendix or checklist table at **24 data rows** unless the user explicitly requests exhaustive workbook mode.

USER REPORT: {slug}/user_report_{slug_lower}.html  ← MANDATORY alongside confluence
  — Plain English ONLY. No house numbers, no dasha names, no planet positions.
  — MUST include ALL Part 8 sections from vedic_confluence_skill.md (11 base + **2c Seven-pillar confirmation summary** + **9a Major transition calendar** + **5a Work & Independence** when Dashamsha exists + **2b Birth-star karmic lesson** when nakshatra handbook OCR exists)
  — **2c:** seven titled paragraphs (Personality, Profession, Wealth, Spouse and relationships, Children, Health, Longevity) with dated anchors and cross-hub confirmation stitches per vedic_confluence_skill.md Part 8
  — **9a:** plain-English date windows + themes before traffic light (Vimshottari boundaries translated, no jargon)
  — Spouse/Partnership card: FULL **rules3.md** Navamsha themes in plain English when Navamsha exists (long-term vs early impression, home harmony, partner sketch, timing)
  — "Who You Are": 6–8 bullets with plain text icons (★ ● ►) — NO emoji, 2–3 sentences each
  — "Your Past Chapters": 3–5 cards describing past life phases from chart (builds confidence)
  — Ashtakavarga: translated to plain English — strongest zone + weakest zone cards
  — BNN: minimum 3 cards (education, career phases, home/property)
  — Traffic light: minimum 7 rows covering 2026–2032
  — Remedies: 2 full cards (Daily practices + Lifestyle)
  — GOLD HUB LAYOUT: reports/Ritz_reprot/user_report_ritz.html — match section completeness, card depth, and warmth; **no arbitrary minimum line count** and **no filler tables**.
  — VOICE: Human astrologer + confirmatory synthesis per vedic-report-prediction SKILL (opening like a conversation, bullets chart-led in plain English, calibration without fake %).

CHILDREN ANALYSIS — MANDATORY DETAILED SECTION IN ALL REPORTS (rules14.md = D7 Saptamsha):
  THIS IS ONE OF THE MOST IMPORTANT SECTIONS — clients care deeply about children.
  Every report (Confluence, User Report, BNN, KP, Jaimini, Vimshottari, BlindChart, Pillar) MUST include 5 sub-topics:

  1. PROMISE/DENIAL: D7 lagna condition (benefic = promise; malefic = delay/denial); D1 5th lord + Jupiter
     → BS (male) = Jupiter+Venus+Sun in ODD sign in D1/D9/D7; KS (female) = Jupiter+Moon+Mars in EVEN sign
     → Santana Tithi: (Moon-Sun longitude) × 5, expunge 360s → SP=promise; KP=challenges
     → Verdict: Natural children / Delayed children / Adoption path / Denial

  2. TIMING & COUNT: D7 child numbering (odd lagna: 5,7,9,11,1,3... / even lagna: 9,7,5,3,1,11...)
     → Ketu alone in child's house = that child is the last
     → Saturn on D7 lagna/5th/9th = delay (benefic relief = short; malefic only = long)
     → Dasha timing: 5th lord dasha + Jupiter transit over 5th = key window

  3. GENDER OF FIRST CHILD: child's house lord → navamsha placement → decider → D7 sign
     → Male signs: Aries, Cancer, Leo, Libra, Scorpio, Sag | Female: Taurus, Virgo, Cap, Aquarius
     → Male planets: Sun, Mars, Jupiter, Rahu | Female: Moon, Venus, Ketu | Neutral: Mercury, Saturn

  4. CHILD'S HEALTH: D7 6th/8th from child's house (disease/longevity); D7 4th = happiness from children

  5. CHILD'S PROFESSION & DEVOTION: D7 lagna lord nature + raj yoga from child's house + Jupiter in 5th from child

  USER REPORT children card MUST state in plain English:
  — Overall verdict (1 direct sentence: children YES/delayed/adoption)
  — Count estimate + timing window (specific years)
  — Gender of first child (conclusive)
  — Child's personality and likely career direction
  — Child's health (strong / specific concern)
  — Happiness from children (D7 4th verdict)
  — Remedy: Yellow Sapphire + Brihaspati Gayatri (Jupiter) if 5th lord/Jupiter afflicted

PROFESSION & DASHAMSHA (D10) — MANDATORY WHEN EXTRACT HAS DASHAMAMSHA DATA (rules13.md):
  When `|| Dashamsha` or Shodashvarga **Dashamamsha** row exists, EVERY report (Confluence, User, BNN, KP, Jaimini,
  Vimshottari, BlindChart, Pillar) MUST weave in Goel D10 career logic — not optional.

  1. D10 LAGNA + LORD: sign, house of lord, dignity, who aspects/conjoins — inward career drive.
  2. D10 10TH + LORD: outward face of work; **where D10 tenth lord sits** (1st–12th meanings in rules13.md).
  3. DASHAMSHA DEITIES: for D10 lagna lord AND D10 10th lord — Indra/Agni/Yama/Rakshasa/Varuna/Vayu/Kubera/Ishana/Brahma/Ananta
     (odd sign = direct 3° segments; even sign = reversed segment order in sign) → one sentence flavour each.
  4. SELF-EMPLOYED vs SERVICE: Saturn Gocharastha (exalted/own, not trik-tied) vs Agocharastha (debilitated/Rahu-Ketu/combust/war loser/trik);
     shift D1→D9→D10 = career path change; PP grahas (Sun,Moon,Mars,Rahu) on D10 lagna or D10 10th for independence;
     five-planet arc (houses 7–12 or 10–3) with ≥2 PP; 3rd–10th link for courage.
  5. CAPRICORN: planets in Capricorn in D1 and D10 — status amplifier per Goel.
  6. COMPOSITE TABLE: add row **Goel D10** with evidence string.

  USER REPORT (plain English, no jargon): one **Work & Independence** card — organisation vs self-direction pattern,
  public recognition vs behind-scenes, stability vs job-change signature — derived from D10 + Saturn mode, without citing houses/planets by name.

MARRIAGE & NAVAMSHA (D9) — MANDATORY WHEN EXTRACT HAS NAVAMAMSHA DATA (rules3.md = *Predict with Navamsha*, Goel):
  When `|| Navamsha` or Shodashvarga **Navamsha** row exists, EVERY report (Confluence, User, BNN, KP, Jaimini, Vimshottari,
  BlindChart, Pillar) MUST apply Goel D9 marriage logic for **spouse / partnership** — not D1-only.

  1. D9 LAGNA: benefic/malefic relations — desire toward marriage and approach to partnership.
  2. D9 7TH: occupants, aspects — parallel analysis to D1 seventh; promise vs chronic stress.
  3. KARAKAS IN D9: Venus (male native), Jupiter (female native) — affliction count; **D9 = long-term outcome tone** vs D1.
  4. D9 4TH: marital home / happiness; papa kartari or malefics → domestic strain.
  5. D9 7TH LORD: malefic PAC → difficulty sustaining marriage; link separation chapter when relevant.
  6. DENIAL / DELAY: triple affliction on 7th in **both** D1 and D9 without benefic relief; malefic in 7th + graha in 9th;
     Venus alone in D9 lagna (male) / Jupiter alone in D9 lagna (female) — state verdict.
  7. DK + Rahu/Ketu/Saturn: foreign / “other” / status-mismatch union — **confirm in D9**.
  8. TIMING: Jupiter transit or MD/AD to D9 lagna lord / 7th axis — cross Vimshottari, Jaimini, RTVD 7th year.
  9. FLAGS: pushkar / vargottama / visha navamsha on 7th lord, Venus, Jupiter, DK — when degrees exist.
  10. COMPOSITE / VOTE ROW: **Goel D9** with evidence string.

  USER REPORT: expand **Spouse / Partnership** card per vedic_confluence_skill.md Part 8 — plain English only; no “Navamsha”, no house numbers.

NAKSHATRA KARMIC TALES (Karam Vipak handbook) — WHEN OCR EXISTS (rules42.md):
  If `book_ocr/nakshatra_karmic_stories/*_ocr_full.txt` is present, Confluence + User Report MUST add the **KVS** lane.

  1. Read Moon nakshatra + pada (required), Lagna/Sun pada if useful, from extract JSON or planetary table.
  2. Grep OCR for "{Nakshatra} {1st|2nd|3rd|4th} pada" — try spelling variants (Kritika/Krittika, Jyestha, etc.).
  3. Summarize story theme + lesson; MATCH to chart houses/dasha — state resonance confidence.
  4. CONFLUENCE: subsection **3b** + vote row **KVS pada tale** | evidence: Moon [nak] pada [n] — [one-line theme].
  5. USER REPORT: card **2b Birth-star karmic lesson** — metaphor only, growth habit, no gore, no jargon (see vedic_confluence_skill.md).
  6. If OCR missing: skip lane; one line in confluence header optional.

GEMSTONE & REMEDY — MANDATORY IN ALL REPORTS (rules40.md + rules41.md):
  Every individual report AND the user report MUST include a dedicated "Remedies & Gemstone" section.
  rules40.md = Graha Shanti (Marc Boney) — mantra-first approach, K.N. Rao method
  rules41.md = Book of Remedies (Avasthi) — gemstone table + practical daily remedies

  GEMSTONE TABLE (primary / affordable alternative):
    Sun     → Ruby (Manik) / Garnet        | Gold ring finger        | Sunday
    Moon    → Pearl (Moti) / Moonstone      | Silver little finger    | Monday
    Mars    → Red Coral (Moonga) / Red Hakik | Copper ring finger     | Tuesday
    Mercury → Emerald (Panna) / Green Onyx  | Gold little finger     | Wednesday
    Jupiter → Yellow Sapphire / Sunela      | Gold index finger      | Thursday
    Venus   → Diamond / White Opal, Zircon  | Platinum middle finger | Friday
    Saturn  → Blue Sapphire / Amethyst      | Iron middle finger     | Saturday ← TEST 3 days first
    Rahu    → Hessonite (Gomed) / Black Onyx | Silver middle finger  | Saturday
    Ketu    → Cat's Eye / Turquoise         | Panchdhatu ring finger | Wednesday

  MANTRA PRESCRIPTIONS (rules40.md — Formula: Intention + Intensity + Duration = Effect):
    Sun dasha/problems     → Aditya Hridayam Stotram (31 verses), Sundays
    Moon problems          → Chandra Gayatri 108x daily, Mondays
    Mars/Saturn troubles   → Hanuman Chalisa, Tuesdays + Saturdays
    Mercury affliction     → Vishnu Sahasranama, Wednesdays
    Jupiter/education      → Sarasvati Mantra (OM AIM SHRIM HRIM SARASVATI DEVYAI NAMAH) 108x, Thursdays
    Venus/marriage delay   → Lakshmi Mantra (OM SHRIM MAHA LAKSHMIYI NAMAH) + 100 Names, Fridays
    Rahu/enemies/legal     → Durga Mantra (OM DUM DURGAYE NAMAH) 108x
    Health/longevity risk  → Maha Mrityunjaya Mantra 108x/day for 40 days, start Monday
    Universal background   → Vishnu Sahasranama 1x weekly (Wednesday) — K.N. Rao's highest recommendation

  CHARITY (DAN) — one item per report:
    Sun→wheat+jaggery Sunday | Moon→rice+silver Monday | Mars→red lentils Tuesday
    Mercury→moong dal Wednesday | Jupiter→chana dal Thursday | Venus→ghee/cow donation Friday
    Saturn→udad dal+oil Saturday | Rahu→udad dal Amavasya | Ketu→blankets Tuesday

  USER REPORT REMEDY FORMAT (2 cards):
    Card 1 — "Your Gemstone": Primary gem → affordable alt → what it supports → activation day
    Card 2 — "Daily Practices": Mantra name + count + day + duration + 1 charity action

  PRIORITY LOGIC:
    1. Current dasha lord → that planet's remedy is #1 priority
    2. Most afflicted planet in chart → second remedy
    3. Life challenge → marriage=Venus/Lakshmi; health=Maha Mrityunjaya; career=Sun/Jupiter
    4. Lagna lord's gemstone = ALWAYS safe base recommendation
    5. ALWAYS offer affordable alternative alongside primary gem

PREDICTION-FIRST WRITING LAW — APPLIES TO EVERY INDIVIDUAL AND CONFLUENCE REPORT:
  ═══════════════════════════════════════════════════════════════════════════════
  The PURPOSE of every section is the PREDICTION / LIFE MEANING — not to teach astrology.
  Planet positions, house placements, and tables are EVIDENCE, not the message.

  STRUCTURE OF EVERY SECTION:
    1. HEADLINE = life meaning (career, health, marriage — NOT "Mercury in 10th")
    2. BODY = the prediction / what will happen or did happen — stated directly
    3. SUPPORT = ONE brief clause naming the planet/house/score that justifies it
    4. DATE/WINDOW = when, if applicable

  WRONG — planet-first, buries the meaning:
    ✗ "Mercury is placed in the 10th house in Gemini, its own sign. This makes Mercury
       very strong. Mercury rules the lagna and 4th house. Being in the 10th, it aspects
       the 4th house. Mercury's natural significations include communication..."
  RIGHT — prediction-first, planet fact as brief support:
    ✓ "Your career is built on analytical communication and technical precision.
       You thrive in IT, writing, finance, or any role requiring logical problem-solving.
       (Mercury, lagna lord, occupies its own sign Gemini in the 10th — strong professional identity.)"

  WRONG — table dumping:
    ✗ "Planet | Sign | House | Nakshatra | Dignity
        Sun   | Sco  |  5th  | Anuradha  | Neutral
        Moon  | Pis  |  9th  | Revati    | Good..."
    Then zero interpretation follows.
  RIGHT — table as SUMMARY, interpretation immediately after each row or after table:
    ✓ A small fact-strip table is acceptable ONLY at the top of a report for reference.
      Every row or every section that follows MUST have a 2–4 sentence interpretation
      stating what that planet's placement MEANS for this client's life.

  SECTION TITLES must state life domains — NOT planet names:
    ✗ "Mercury in Gemini in 10th" → ✓ "Career & Profession"
    ✗ "7th lord Venus in 4th"    → ✓ "Marriage & Partnership"
    ✗ "Rahu-Ketu Axis"           → ✓ "Life Direction & Past-Life Themes"
    ✗ "6th house analysis"       → ✓ "Health & Challenges"

  PLANET FACT BUDGET PER SECTION — maximum ONE mention of the supporting combination.
    After that, focus entirely on what it means for the person's LIFE.

USER REPORT WRITING STYLE — CONCLUSIVE, NO CONDITIONAL HEDGING:
  The user report must guide, not hedge. These rules apply to user_report_*.html ONLY:
  — BANNED: "If you are single/married/a parent..." — NEVER write these.
  — BANNED: "You may feel..." / "This could indicate..." / "If this resonates..."
  — REQUIRED: State chart observations as facts. Give consequence. Give action.
  — WRONG: "If you are planning children, treat it as a project."
  — RIGHT:  "Children themes in your chart carry a serious-blessing signature. Treat the process as a project with medical and emotional support, not a race."
  — WRONG: "If you change jobs you may succeed."
  — RIGHT:  "The chart favours a role change between mid-2027 and mid-2028 — 3 systems point outward vs 1 pointing to stability."
  — When genuinely two outcomes exist: state the probabilities, not conditions.
  — The report is a guidance document for someone facing real problems. Be honest, direct, useful.

DONE SIGNAL — write _astro_sessions/{session_id}/DONE.json only when ALL are true:
  1) Confluence HTML exists at the path you will list under "confluence".
  2) User report HTML exists at the path you will list under "user".
  3) **Blind Chart lane (BLOCKING):** {out}/Vedic_BlindChart_{slug}_{today}.html MUST exist on disk before DONE.json.
     The extract always has D1 data — do not skip step 10, do not write DONE without this file.
  4) Every other path you list in the "individual" array MUST exist. If Palmistry or Numerology was explicitly
     [SKIP] in your task block, omit those entries from "individual" rather than listing missing files.
  See exact JSON format in the task below.
=== END RULES ===
"""

def build_prompt(
    session_id: str,
    extracted_txt: str,
    palm_paths: List[str],
    client_name: str,
    dob: str,
    gender: str,
    slug: str,
    slug_lower: str,
    today: str,
    life_events: str,
    precomputed_json: str = None,
    bnn_done: bool = False,
    bhardwaj_done: bool = False,
    jaimini_done: bool = False,
    ashtakavarga_done: bool = False,
    kp_done: bool = False,
    rtvd_done: bool = False,
    longevity_done: bool = False,
    blindchart_done: bool = False,
    pillar_done: bool = False,
    vimshottari_done: bool = False,
    yogini_done: bool = False,
    confluence_done: bool = False,
    palm_done: bool = False,
    client_question: str = "",
) -> str:
    done_path = f"_astro_sessions/{session_id}/DONE.json"

    # All reports go into reports/{slug}/ subfolder for easy per-client browsing
    out = f"reports/{slug}"

    if palm_done:
        palm_section = (
            f"PALMISTRY: Generated deterministically by palm_api.pipeline (CV + book corpus, no LLM). "
            f"DO NOT regenerate {out}/Palmistry_{slug}_{today}.html — use as-is for confluence."
        )
    elif palm_paths:
        palm_section = f"""
PALM IMAGES available at:
{chr(10).join(f'  - {p}' for p in palm_paths)}
Right palm = dominant/lived life. Left palm = innate blueprint.
Generate: {out}/Palmistry_{slug}_{today}.html via palm_api.pipeline if Python step failed.
"""
    else:
        palm_section = "PALM IMAGES: Not provided — skip Palmistry lane. Note [SKIPPED: Palmistry — no images] in confluence header."

    question_section = ""
    if client_question.strip():
        question_section = f"""
CLIENT FOCUS QUESTION (semantic domain routing — same engine as horary topic detection):
  "{client_question.strip()}"
A focused confluence report Vedic_Focus_*_{slug}_{today}.html should already exist if Python confluence ran.
Lead the user report with an affirmative answer to this question; full technique table lives in the focus file.
"""

    dob_compact = dob.replace('-', '') if dob else ""
    # Numerology is now produced deterministically in Python (numerology_report.py) —
    # the LLM must NOT regenerate it (avoids hallucinated cycles/numbers).
    numerology_section = (
        "NUMEROLOGY: Generated deterministically by numerology_report.py (rule-based, no LLM). "
        "DO NOT generate, edit, or include any Numerology HTML — skip that lane entirely."
    )
    # BNN is now produced deterministically in Python (vedic_bnn_report.py).
    bnn_section = (
        "BNN: Generated deterministically by vedic_bnn_report.py (rule-based, no LLM). "
        "DO NOT generate, edit, or include any Bhrigu Nandi Nadi HTML — skip that lane entirely. "
        "Treat the existing Vedic_BNN_*.html as final for confluence input."
    ) if bnn_done else (
        "BNN: Python generator unavailable for this run — generate the BNN lane yourself per item 2 below."
    )
    bhardwaj_section = (
        "Bhardwaj: Generated deterministically by vedic_bhardwaj_report.py (semantic MiniLM + book corpus, no LLM). "
        "DO NOT generate, edit, or include any Bhardwaj HTML — skip that lane entirely. "
        "Treat the existing Vedic_Bhardwaj_*.html as final for confluence input."
    ) if bhardwaj_done else (
        "Bhardwaj: Python generator unavailable for this run — generate the Bhardwaj lane yourself per item 2b below."
    )
    py_lanes = []
    if bhardwaj_done:
        py_lanes.append("Bhardwaj")
    if jaimini_done:
        py_lanes.append("Jaimini")
    if ashtakavarga_done:
        py_lanes.append("Ashtakavarga")
    if kp_done:
        py_lanes.append("KP")
    if rtvd_done:
        py_lanes.append("RTVD")
    if longevity_done:
        py_lanes.append("Longevity")
    if blindchart_done:
        py_lanes.append("BlindChart")
    if pillar_done:
        py_lanes.append("Pillar")
    if vimshottari_done:
        py_lanes.append("Vimshottari")
    if yogini_done:
        py_lanes.append("Yogini")
    if palm_done:
        py_lanes.append("Palmistry")
    if confluence_done:
        py_lanes.append("Confluence+UserReport")
    extra_py_section = (
        f"PYTHON LANES (rule-based, no LLM) already generated — DO NOT regenerate or edit: {', '.join(py_lanes)}. "
        f"Use the existing HTML files as-is for confluence input."
    ) if py_lanes else ""
    bnn_lane = (
        f" 2. [PYTHON] Vedic BNN — already generated deterministically by vedic_bnn_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_BNN_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if bnn_done else (
        f" 2. {out}/Vedic_BNN_{slug}_{today}.html\n"
        f"    → Read vedic_bnn_report_skill.md · Reference: reports/Ritz_reprot/Vedic_BNN_Ritz_20260408.html\n"
        f"    → MUST include: lagna lord + moon sign traits (named planets), 6th/8th lord health analysis (planets named),\n"
        f"      10th lord career analysis (planet named), 7th lord spouse analysis (planet named), antardasha table with\n"
        f"      exact dates from extract and per-period prediction reason stated"
    )
    bhardwaj_lane = (
        f" 2b. [PYTHON] Vedic Bhardwaj — already generated deterministically by vedic_bhardwaj_report.py "
        f"(semantic MiniLM + Bhardwaj OCR corpus, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Bhardwaj_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if bhardwaj_done else (
        f" 2b. {out}/Vedic_Bhardwaj_{slug}_{today}.html\n"
        f"    → Reference: reports/Bhardwaj_Ritz_preview.html\n"
        f"    → MUST include: lagna + moon chapter, planet-in-house predictions from Bhardwaj book,\n"
        f"      dasha/antardasha cards with dates from extract, gochar from Moon sign, remedy cards"
    )
    jaimini_lane = (
        f" 4. [PYTHON] Vedic Jaimini — already generated deterministically by vedic_jaimini_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Jaimini_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if jaimini_done else (
        f" 4. {out}/Vedic_Jaimini_{slug}_{today}.html\n"
        f"    → Read vedic_jaimini_report_skill.md · Reference: reports/Ritz_reprot/Vedic_Jaimini_Ritz_20260408.html\n"
        f"    → MUST include: all 7 cara karakas named with assigned planets, Atmakarak planet named and analyzed,\n"
        f"      Karakamsha sign and its implications, Chara dasha timeline with all periods and dates from extract,\n"
        f"      past events cross-matched with Chara periods"
    )
    kp_lane = (
        f" 3. [PYTHON] Vedic KP — already generated deterministically by vedic_kp_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_KP_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if kp_done else (
        f" 3. {out}/Vedic_KP_{slug}_{today}.html\n"
        f"    → Read vedic_kp_report_skill.md · Reference: reports/Ritz_reprot/Vedic_KP_Ritz_20260408.html\n"
        f"    → MUST include: cuspal table for ALL 12 cusps with sub lord named for each, planet positions with\n"
        f"      sub lords from KP block, 10th cusp sub lord career analysis, 7th cusp sub lord marriage verdict,\n"
        f"      current AD significator analysis with specific house significations stated"
    )
    ashtaka_lane = (
        f" 7. [PYTHON] Vedic Ashtakavarga — already generated deterministically by vedic_ashtakavarga_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Ashtakavarga_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if ashtakavarga_done else (
        f" 7. {out}/Vedic_Ashtakavarga_{slug}_{today}.html\n"
        f"    → Read vedic_ashtakavarga_skill.md · Reference: reports/Ritz_reprot/Vedic_Ashtakavarga_Ritz_20260408.html\n"
        f"    → MUST include: SAV table all 12 houses with scores, Jupiter BAV in all 12 houses, Saturn BAV in all\n"
        f"      12 houses, current Jupiter transit sign + BAV score + donor count stated, 5-year snapshot table"
    )
    rtvd_lane = (
        f" 8. [PYTHON] Vedic RTVD — already generated deterministically by vedic_rtvd_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_RTVD_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if rtvd_done else (
        f" 8. {out}/Vedic_RTVD_{slug}_{today}.html\n"
        f"    → Read vedic_rtvd_skill.md · Reference: reports/Ritz_reprot/Vedic_RTVD_Ritz_20260408.html\n"
        f"    → MUST include: Age→House mapping table for native's life, past 10 years cross-matched (house active +\n"
        f"      year lord named + life event derived), current year analysis (house + year lord + dignity + prediction),\n"
        f"      next 5 years year-by-year with year lord named and prediction reason stated"
    )
    longevity_lane = (
        f" 9. [PYTHON] Vedic Longevity — already generated deterministically by vedic_longevity_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Longevity_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if longevity_done else (
        f" 9. {out}/Vedic_Longevity_{slug}_{today}.html\n"
        f"    → Read vedic_longevity_skill.md · Reference: reports/Ritz_reprot/Vedic_Longevity_Ritz_20260408.html\n"
        f"    → MUST include: 2nd and 7th lords named with natal position, Mrityu Bhaga table for all planets with\n"
        f"      degrees checked, longevity span estimate, maraka activation periods listed with dates,\n"
        f"      disclaimer block at top"
    )
    blindchart_lane = (
        f"10. [PYTHON] Vedic BlindChart — already generated deterministically by vedic_blindchart_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_BlindChart_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if blindchart_done else (
        f"10. {out}/Vedic_BlindChart_{slug}_{today}.html\n"
        f"    → Read vedic_blind_chart_skill.md · Reference: reports/Ritz_reprot/Vedic_BlindChart_Ritz_20260408.html\n"
        f"    → BLIND CHART = predict from chart alone. ALL sections MANDATORY regardless of calibration data.\n"
        f"    → NEVER write \"uncalibrated — withheld\" or skip a section because no events were provided.\n"
        f"    → MUST include ALL of: Father, Mother, Siblings, Education, Career, Partner, Children, Wealth, Health,\n"
        f"      Past Reconstruction, Right Now, Near Future (6+ dated predictions), 5-Year Arc.\n"
        f"    → Tone: conclusive plain English throughout."
    )
    pillar_lane = (
        f" 1. [PYTHON] Vedic Pillar — already generated deterministically by vedic_pillar_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Pillar_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if pillar_done else (
        f" 1. {out}/Vedic_Pillar_{slug}_{today}.html\n"
        f"    → Read vedic_pillar_skill.md · Reference: reports/Vedic_Pillar_Ritz_20260408.html\n"
        f"    → MUST include: exact lagna degree + nakshatra, lagna lord dignity + neecha bhanga analysis (if any),\n"
        f"      7-factor lagna checklist table (each row answers YES/NO with specific planet named), dispositor chain\n"
        f"      traced step-by-step, current MD/AD lord connection to lagna lord stated"
    )
    vim_lane = (
        f" 5. [PYTHON] Vedic Vimshottari — already generated deterministically by vedic_vimshottari_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Vimshottari_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if vimshottari_done else (
        f" 5. {out}/Vedic_Vimshottari_{slug}_{today}.html\n"
        f"    → Read vedic_vimshottari_skill.md · Reference: reports/Ritz_reprot/Vedic_Vimshottari_Ritz_20260408.html\n"
        f"    → MUST include: full dasha sequence table with dates, current MD 7-step analysis (each step answered\n"
        f"      with specific planet/sign/house data), current AD verdict, all upcoming ADs with dates and specific\n"
        f"      predictions, health stress periods identified by MD/AD lord house ownership"
    )
    yogini_lane = (
        f" 6. [PYTHON] Vedic Yogini — already generated deterministically by vedic_yogini_report.py (rule-based, no LLM).\n"
        f"    DO NOT generate it. The file {out}/Vedic_Yogini_{slug}_{today}.html already exists; use it as-is for confluence."
    ) if yogini_done else (
        f" 6. {out}/Vedic_Yogini_{slug}_{today}.html\n"
        f"    → Read vedic_yogini_skill.md · Reference: reports/Ritz_reprot/Vedic_Yogini_Ritz_20260408.html\n"
        f"    → MUST include: Moon nakshatra named, Yogini at birth calculated and named, full 36-year cycle table\n"
        f"      with all Yogini periods and dates, each past period matched to life tone, current period specific\n"
        f"      prediction, confluence check with Vimshottari running period"
    )
    palm_lane = (
        f"11. [PYTHON] Palmistry — already generated by palm_api.pipeline (no LLM).\n"
        f"    DO NOT regenerate. Use {out}/Palmistry_{slug}_{today}.html as-is."
    ) if palm_done else (
        f"11. {out}/Palmistry_{slug}_{today}.html\n"
        f"    → palm_api.pipeline if images present"
        if palm_paths else "11. [SKIP] Palmistry — no images"
    )
    confluence_lane = (
        f"PHASE C — CONFLUENCE + USER REPORT [PYTHON] — already generated by vedic_confluence_report.py "
        f"(semantic MiniLM clustering, rule-based, no LLM).\n"
        f"  DO NOT generate or edit:\n"
        f"  • {out}/Vedic_Confluence_{slug}_{today}.html\n"
        f"  • {out}/user_report_{slug_lower}.html\n"
        f"  Use both files as-is. Write DONE.json listing these paths."
    ) if confluence_done else (
        f"PHASE C — CONFLUENCE (BOTH mandatory):\n"
        f"13. {out}/Vedic_Confluence_{slug}_{today}.html      (read vedic_confluence_skill.md)\n"
        f"    → Gold layout: reports/Ritz_reprot/Vedic_Confluence_Ritz_20260408.html\n"
        f"14. {out}/user_report_{slug_lower}.html             (vedic_confluence_skill.md Part 8)\n"
        f"    → Gold hub: reports/Ritz_reprot/user_report_ritz.html"
    )

    life_events_section = ""
    if life_events.strip():
        life_events_section = f"""
CALIBRATION DATA (confirmed past life events — use to validate rules):
{life_events}
Calibrate each lane against these events. Remove/downgrade rules that fail.
Mark validated rules as CALIBRATED in the confluence confidence scores.
"""
    else:
        life_events_section = """
CALIBRATION DATA: None provided.
Mark ALL reports as UNCALIBRATED — first pass.
Add calibration request block at the end of the user report.
"""

    return f"""{ASTRO_SYSTEM_RULES}

=== YOUR TASK ===

CLIENT: {client_name or "Extract from report"}
DOB: {dob or "Extract from report"}
GENDER: {gender}
TODAY: {today}
SLUG: {slug}
SESSION_ID: {session_id}
OUTPUT FOLDER: {out}/   ← ALL reports must go here (create folder if needed)

EXTRACTED VEDIC REPORT: {extracted_txt}
  (Read this file to get lagna, planets, all dasha tables, KP block, Jaimini block, etc.)

PRE-COMPUTED ASTROLOGY DATA: {precomputed_json if precomputed_json else "NOT AVAILABLE (DOB missing)"}
  *** READ THIS JSON FILE FIRST — it contains verified math you must use ***
  It contains: nakshatra for every planet, dignity for every planet, Neecha Bhanga analysis,
  dispositor chain, 7-factor lagna checklist, full Vimshottari sequence with current MD/AD dates,
  full Yogini cycle, RTVD year-by-year table, longevity maraka analysis, Mrityu Bhaga degrees,
  Jaimini cara karakas ranked by degree, numerology core numbers, and per-lane LLM instructions.
  RULE: Use the values from the JSON — do NOT recompute what is already computed.
  The JSON key "llm_lane_instructions" has specific instructions for each report type.
  The JSON key "pillar.seven_factors" has the pre-answered 7-factor checklist — copy into report table.
  The JSON key "vimshottari.sequence" has the full dasha timeline with verified dates.
  The JSON key "yogini.full_cycle" has the complete Yogini timeline.
  The JSON key "rtvd.table" has the year-by-year RTVD table.
{palm_section}
{numerology_section}
{bhardwaj_section}
{bnn_section}
{extra_py_section}
{life_events_section}
{question_section}

=== EXECUTE THE MANDATORY PIPELINE ===

Read .cursor/skills/vedic-report-prediction/SKILL.md for the full sequence.
Then generate ALL of the following in order (save ALL files to {out}/):

PHASE B — INDIVIDUAL LANE REPORTS (each is a FULL standalone HTML report):
QUALITY RULE: Every sentence must contain a specific planet name / house number / date / score from THIS client's
chart. Generic sentences that apply to any chart are BANNED. Reviewer test: "Does this sentence only make
sense for this specific client?" If NO → rewrite it.

{pillar_lane}

{bnn_lane}

{bhardwaj_lane}

{kp_lane}

{jaimini_lane}

{vim_lane}

{yogini_lane}

{ashtaka_lane}

{rtvd_lane}

{longevity_lane}

{blindchart_lane}

{palm_lane}
12. [PYTHON] Numerology — already generated deterministically by numerology_report.py. DO NOT generate it.

{confluence_lane}

=== DONE SIGNAL ===

After generating BOTH Phase C reports, write exactly this file:
  {done_path}

Content must be valid JSON:
{{
  "confluence": "{out}/Vedic_Confluence_{slug}_{today}.html",
  "user": "{out}/user_report_{slug_lower}.html",
  "individual": [
    "{out}/Vedic_Pillar_{slug}_{today}.html",
    "{out}/Vedic_BNN_{slug}_{today}.html",
    "{out}/Vedic_Bhardwaj_{slug}_{today}.html",
    "{out}/Vedic_KP_{slug}_{today}.html",
    "{out}/Vedic_Jaimini_{slug}_{today}.html",
    "{out}/Vedic_Vimshottari_{slug}_{today}.html",
    "{out}/Vedic_Yogini_{slug}_{today}.html",
    "{out}/Vedic_Ashtakavarga_{slug}_{today}.html",
    "{out}/Vedic_RTVD_{slug}_{today}.html",
    "{out}/Vedic_Longevity_{slug}_{today}.html",
    "{out}/Vedic_BlindChart_{slug}_{today}.html",
    "{out}/Palmistry_{slug}_{today}.html"
  ],
  "client": "{client_name}",
  "generated": "{today}"
}}

IMPORTANT: Write DONE.json ONLY after confluence, user_report, AND the Blind Chart HTML
({out}/Vedic_BlindChart_{slug}_{today}.html) are complete. Missing Blind Chart = incomplete session.
Do not write partial JSON. The UI polls for this file to show download buttons.
"""

# ─────────────────────────── session store ────────────────────────────
class Session:
    def __init__(self, sid: str):
        self.id = sid
        self.dir = SESSIONS_DIR / sid
        self.dir.mkdir(parents=True, exist_ok=True)
        self.events: List[str] = []
        self.status: str = "idle"
        self.ws_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def emit(self, msg: str, kind: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = json.dumps({"ts": ts, "msg": msg, "kind": kind})
        self.events.append(entry)
        await self._broadcast(entry)

    async def emit_raw(self, payload: dict):
        if "ts" not in payload:
            payload["ts"] = datetime.now().strftime("%H:%M:%S")
        entry = json.dumps(payload)
        self.events.append(entry)
        await self._broadcast(entry)

    async def _broadcast(self, entry: str):
        dead = []
        for ws in list(self.ws_connections):
            try:
                await ws.send_text(entry)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.ws_connections.remove(ws)
            except Exception:
                pass

_sessions: Dict[str, Session] = {}
_cursor_human_running: Dict[str, bool] = {}

def get_session(sid: str) -> Session:
    if sid not in _sessions:
        _sessions[sid] = Session(sid)
    return _sessions[sid]


# ─────────────────────── Report generation queue ──────────────────────
# The pipeline reloads shared Python modules and is CPU-heavy, so report
# generation must run one-at-a-time on a laptop. Extra requests wait in a
# FIFO queue and receive live position + estimated-wait messages over the
# same WebSocket. Tune with env vars MAX_CONCURRENT / REPORT_AVG_SECONDS.
MAX_CONCURRENT       = int(os.getenv("MAX_CONCURRENT", "1"))
_REPORT_AVG_DEFAULT  = float(os.getenv("REPORT_AVG_SECONDS", "150"))


def _fmt_wait(seconds: float) -> str:
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s" if s else f"{m}m"


def _queue_msg(pos: int, wait: float) -> str:
    return (f"You're #{pos} in the queue · about {_fmt_wait(wait)} wait. "
            f"Your report starts automatically when it's your turn.")


class _GenQueue:
    """FIFO gate that serialises heavy report generation and broadcasts
    queue position + ETA to each waiting session."""

    def __init__(self) -> None:
        self._cond: Optional[asyncio.Condition] = None
        self.active: int = 0
        self.waiting: List[str] = []        # session ids, arrival order
        self.durations: List[float] = []     # recent completed run seconds

    def _ensure(self) -> None:
        if self._cond is None:
            self._cond = asyncio.Condition()

    def avg_seconds(self) -> float:
        if self.durations:
            recent = self.durations[-5:]
            return sum(recent) / len(recent)
        return _REPORT_AVG_DEFAULT

    async def _emit_positions(self) -> None:
        avg = self.avg_seconds()
        for idx, sid in enumerate(list(self.waiting)):
            pos = idx + 1
            eta = pos * avg
            s = _sessions.get(sid)
            if s:
                await s.emit_raw({
                    "kind": "queued", "position": pos, "ahead": pos,
                    "eta_seconds": int(eta), "msg": _queue_msg(pos, eta),
                })

    async def acquire(self, session: "Session") -> None:
        self._ensure()
        async with self._cond:
            if self.active < MAX_CONCURRENT and not self.waiting:
                self.active += 1
                return
            self.waiting.append(session.id)
        await self._emit_positions()
        async with self._cond:
            while not (self.active < MAX_CONCURRENT
                       and self.waiting and self.waiting[0] == session.id):
                await self._cond.wait()
            self.waiting.pop(0)
            self.active += 1
        # Refresh everyone still waiting (positions shifted up by one).
        await self._emit_positions()

    async def release(self, duration: Optional[float] = None) -> None:
        self._ensure()
        async with self._cond:
            self.active = max(0, self.active - 1)
            if duration and duration > 0:
                self.durations.append(duration)
                self.durations = self.durations[-10:]
            self._cond.notify_all()
        await self._emit_positions()


_gen_queue = _GenQueue()


def resolve_extracted_txt_path(input_dir: Path, pdf_path: Path) -> Optional[Path]:
    """Pick extracted text for the PDF just uploaded, not stale session files."""
    expected = input_dir / f"{pdf_path.stem}_extracted.txt"
    if expected.is_file():
        return expected
    candidates = sorted(
        input_dir.glob("*_extracted.txt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# ──────────────────── extract client info from txt ────────────────────
def parse_client_info(extracted_txt_path: str) -> Tuple[str, str]:
    """Return (name, dob) extracted from AstroSage extracted text.

    AstroSage format has lines like:
      Name                   Ritz              Julian Day ...
      Date                   8.3.1985          Ayan Type ...
    Also the very first line starts with the name before lots of spaces.
    """
    name = ""
    dob  = ""
    BAD_WORDS = {
        "pisces","aries","taurus","gemini","cancer","leo","virgo","libra",
        "scorpio","sagittarius","capricorn","aquarius","male","female",
        "silver","gold","copper","bronze","obliquity","ayanamsa","lahiri",
        "devta","manav","vaisya","mahis","adi","monday","tuesday","wednesday",
        "thursday","friday","saturday","sunday",
    }
    try:
        with open(extracted_txt_path, encoding="utf-8", errors="ignore") as f:
            text = f.read(8000)

        # Strategy 1: first non-empty line starts with the name before a long gap
        # e.g. "    Ritz                      Get free chart … http://AstroSage"
        for raw_line in text.split("\n")[:5]:
            stripped = raw_line.strip()
            if not stripped:
                continue
            m1 = re.match(r'^([A-Za-z][A-Za-z .]{1,40}?)\s{5,}', stripped)
            if m1:
                candidate = m1.group(1).strip()
                if candidate.lower() not in BAD_WORDS and len(candidate) >= 2:
                    name = candidate
                    break

        # Strategy 2: explicit "Name      Ritz      Julian Day" line
        # Use MULTILINE so ^ anchors to line start — avoids "Ayanamsa Name↵ Obliquity"
        if not name:
            m2 = re.search(
                r'^\s*Name\s{2,}([A-Za-z][A-Za-z .]{1,40}?)\s{2,}',
                text, re.MULTILINE
            )
            if m2:
                candidate = m2.group(1).strip()
                if candidate.lower() not in BAD_WORDS:
                    name = candidate

        # DOB: "Date of Birth    8 : 3 : 1985"  or  "Date    8.3.1985"
        m_dob = re.search(
            r'Date(?:\s+of\s+Birth)?\s{1,20}(\d{1,2})\s*[.:]\s*(\d{1,2})\s*[.:]\s*(\d{4})',
            text, re.IGNORECASE
        )
        if m_dob:
            d, mo, yr = m_dob.group(1), m_dob.group(2), m_dob.group(3)
            dob = f"{yr}-{int(mo):02d}-{int(d):02d}"

    except Exception:
        pass

    return (name or "Client", dob)


def make_slug(name: str) -> str:
    """Convert 'Ashish Mathur' → 'Ashish_Mathur'."""
    return re.sub(r"[^A-Za-z0-9]+", "_", name.strip()).strip("_") or "Client"

# ─────────────────────────── FastAPI app ──────────────────────────────
app = FastAPI(title="Vedic Astrology Report Generator")
app.mount("/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")
app.mount("/sessions", StaticFiles(directory=str(SESSIONS_DIR)), name="sessions")

# ─────────────────────────── Authentication ───────────────────────────
# Single shared credential (override via env). Web uses an HttpOnly cookie;
# the Android app sends the same token as a Bearer header. Static report
# files (/reports, /sessions) stay open so report links work in any browser.
import hashlib
import hmac as _hmac

AUTH_USER    = os.getenv("ASTRO_USER", "astro")
AUTH_PASS    = os.getenv("ASTRO_PASS", "astro123")
_AUTH_SECRET = os.getenv("ASTRO_SECRET", "astro-vedic-2026-change-me")
AUTH_COOKIE  = "astro_auth"


def _make_token(user: str) -> str:
    return _hmac.new(_AUTH_SECRET.encode(), user.encode(), hashlib.sha256).hexdigest()


_VALID_TOKEN = _make_token(AUTH_USER)


def _token_ok(token: Optional[str]) -> bool:
    return bool(token) and _hmac.compare_digest(token, _VALID_TOKEN)


def _request_authed(request: Request) -> bool:
    if _token_ok(request.cookies.get(AUTH_COOKIE)):
        return True
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and _token_ok(auth[7:].strip()):
        return True
    if _token_ok(request.headers.get("x-auth-token")):
        return True
    return False


_PUBLIC_EXACT  = {"/", "/health", "/api/login", "/favicon.ico", "/robots.txt"}
_PUBLIC_PREFIX = ("/reports", "/sessions", "/ws", "/static")


def _is_public_path(path: str) -> bool:
    if path in _PUBLIC_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") for p in _PUBLIC_PREFIX)


@app.middleware("http")
async def _auth_middleware(request: Request, call_next):
    path = request.url.path
    if _is_public_path(path) or _request_authed(request):
        return await call_next(request)
    accept = request.headers.get("accept", "")
    if path.startswith("/api/") or path.startswith("/download") \
            or request.method != "GET" or "application/json" in accept:
        return JSONResponse({"detail": "Authentication required"}, status_code=401)
    return RedirectResponse(url="/")


# ──────────────────────── HTML frontend ───────────────────────────────
HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Vedic Astrology Report Generator</title>
<style>
  :root {
    --bg:#0a0a1a; --surface:#12122a; --surface2:#1a1a3a; --border:#2a2a5a;
    --gold:#d4af37; --gold2:#e8c96a; --green:#22c55e; --amber:#f59e0b;
    --red:#ef4444; --text:#e8e0d0; --muted:#7a7a9a; --radius:12px;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;
    min-height:100vh;padding:0}

  .app-header{text-align:center;padding:20px 16px 12px;border-bottom:1px solid var(--border);
    background:linear-gradient(180deg,rgba(18,18,42,.98),var(--bg))}
  .app-header h1{font-size:1.55rem;font-weight:800;
    background:linear-gradient(135deg,#d4af37,#e8c96a,#c8a951);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
  .app-header p{color:var(--muted);margin-top:4px;font-size:0.82rem}

  .app-shell{display:flex;min-height:calc(100vh - 108px)}
  .sidebar{width:220px;flex-shrink:0;background:var(--surface);border-right:1px solid var(--border);
    padding:12px 10px 24px;position:sticky;top:0;height:calc(100vh - 108px);overflow-y:auto}
  .sidebar-title{font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:1.2px;
    color:var(--muted);padding:8px 12px 10px}
  .nav-item{display:flex;align-items:center;gap:10px;width:100%;text-align:left;padding:10px 12px;
    margin-bottom:4px;border:none;border-radius:8px;background:transparent;color:var(--muted);
    font-size:0.84rem;font-weight:600;cursor:pointer;transition:background .15s,color .15s}
  .nav-item:hover{background:rgba(212,175,55,.08);color:var(--text)}
  .nav-item.active{background:rgba(212,175,55,.14);color:var(--gold2);border:1px solid rgba(212,175,55,.25)}
  .nav-icon{font-size:1rem;width:22px;text-align:center;flex-shrink:0}
  .main-content{flex:1;min-width:0;padding:20px 24px 48px;max-width:920px}
  .section-panel{display:none}
  .section-panel.active{display:block}
  .section-head{margin-bottom:16px}
  .section-head h2{font-size:1.15rem;font-weight:700;color:var(--gold2);margin-bottom:4px}
  .section-head p{font-size:0.82rem;color:var(--muted);line-height:1.5}
  .client-strip{margin-bottom:18px;padding:18px 20px}
  .client-strip .card-title{margin-bottom:10px}
  .sidebar-toggle{display:none;position:fixed;bottom:16px;left:16px;z-index:50;padding:10px 14px;
    border-radius:99px;background:var(--gold);color:#000;border:none;font-weight:700;cursor:pointer;
    box-shadow:0 4px 20px rgba(0,0,0,.4)}

  .card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
    padding:24px;margin-bottom:20px}
  .card-title{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;
    color:var(--muted);margin-bottom:16px}

  label{font-size:0.83rem;color:var(--muted);display:block;margin-bottom:6px}
  .field{margin-bottom:16px}
  .field-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:16px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  input[type=text],input[type=date],select,textarea{
    width:100%;background:var(--surface2);border:1px solid var(--border);
    border-radius:8px;color:var(--text);padding:10px 14px;font-size:0.88rem;
    outline:none;transition:border-color .2s}
  input[type=text]:focus,input[type=date]:focus,select:focus,textarea:focus{border-color:var(--gold)}
  input::placeholder,textarea::placeholder{color:var(--muted)}
  select option{background:#1a1a3a}
  textarea{resize:vertical;font-family:inherit;line-height:1.6}

  .place-wrap{position:relative}
  .place-suggestions{position:absolute;left:0;right:0;top:100%;margin-top:4px;z-index:40;
    background:var(--surface2);border:1px solid var(--border);border-radius:8px;
    max-height:220px;overflow-y:auto;list-style:none;box-shadow:0 8px 24px rgba(0,0,0,.35)}
  .place-suggestions li{padding:10px 14px;font-size:0.84rem;cursor:pointer;
    border-bottom:1px solid var(--border);display:flex;flex-direction:column;gap:2px}
  .place-suggestions li:last-child{border-bottom:none}
  .place-suggestions li:hover,.place-suggestions li.active{background:rgba(212,175,55,.12)}
  .place-suggestions .ps-label{color:var(--text);font-weight:600}
  .place-suggestions .ps-meta{color:var(--muted);font-size:0.72rem}
  .place-selected{margin-top:6px;font-size:0.74rem;color:var(--green)}
  .profile-bar{display:flex;flex-wrap:wrap;gap:8px;align-items:flex-end;margin-bottom:14px;padding:12px;background:var(--surface);border:1px solid var(--border);border-radius:10px}
  .profile-bar label{font-size:0.78rem;color:var(--muted);display:block;margin-bottom:4px}
  .profile-bar select,.profile-bar input[type=text]{padding:8px 10px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:0.88rem}
  .profile-bar .profile-grow{flex:1;min-width:140px}
  .profile-inline{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
  .profile-inline select{padding:6px 10px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-size:0.82rem}
  .btr-result{margin-top:10px;padding:12px 14px;border-radius:8px;font-size:0.82rem;line-height:1.5}
  .btr-result.ok{background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.35);color:var(--green)}
  .btr-result.warn{background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.35);color:var(--amber)}
  .btr-result.info{background:rgba(212,175,55,.08);border:1px solid var(--border);color:var(--text)}
  .btr-table{width:100%;border-collapse:collapse;font-size:0.76rem;margin-top:8px}
  .btr-table th,.btr-table td{border:1px solid var(--border);padding:4px 6px;text-align:left}

  .drop-zone{display:block;border:2px dashed var(--border);border-radius:var(--radius);
    padding:32px 20px;text-align:center;cursor:pointer;
    transition:border-color .2s,background .2s;user-select:none}
  .drop-zone:hover,.drop-zone.dragover{border-color:var(--gold);background:rgba(212,175,55,.06)}
  .drop-icon{font-size:2.2rem;margin-bottom:8px;display:block}
  .drop-label{font-size:0.9rem;color:var(--text);display:block}
  .drop-hint{font-size:0.76rem;color:var(--muted);margin-top:4px;display:block}
  input[type=file]{display:none}

  .file-list{margin-top:12px}
  .file-item{display:flex;align-items:center;gap:10px;background:var(--surface2);
    border:1px solid var(--border);border-radius:8px;padding:8px 12px;
    margin-bottom:6px;font-size:0.83rem}
  .file-item .file-name{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .remove-btn{background:none;border:none;color:var(--muted);cursor:pointer;
    font-size:.9rem;padding:2px 6px;border-radius:4px;transition:color .2s,background .2s}
  .remove-btn:hover{color:var(--red);background:rgba(239,68,68,.1)}

  .btn{display:inline-flex;align-items:center;gap:8px;padding:11px 24px;border-radius:8px;
    font-size:0.88rem;font-weight:600;cursor:pointer;border:none;
    transition:opacity .2s,transform .1s}
  .btn:active{transform:scale(.98)}
  .btn:disabled{opacity:.4;cursor:not-allowed}
  .btn-gold{background:linear-gradient(135deg,#c8a020,#d4af37);color:#000}
  .btn-gold:hover:not(:disabled){opacity:.88}
  .btn-success{background:var(--green);color:#fff}
  .btn-success:hover:not(:disabled){opacity:.88}
  .btn-outline{background:transparent;border:1px solid var(--border);color:var(--text)}
  .btn-outline:hover:not(:disabled){border-color:var(--gold);color:var(--gold)}
  .btn-row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:4px}

  .progress-wrap{margin:10px 0}
  .progress-bar-bg{background:var(--surface2);border-radius:99px;height:6px;overflow:hidden}
  .progress-bar-fill{height:100%;background:linear-gradient(90deg,var(--gold),var(--gold2));
    border-radius:99px;transition:width .4s ease;width:0%}

  .queue-banner{display:flex;align-items:center;gap:14px;margin:12px 0;padding:14px 16px;
    background:linear-gradient(90deg,rgba(212,175,55,.12),rgba(212,175,55,.04));
    border:1px solid var(--gold);border-radius:var(--radius)}
  .queue-banner .qb-spinner{width:22px;height:22px;flex:0 0 auto;border-radius:50%;
    border:3px solid rgba(212,175,55,.25);border-top-color:var(--gold);animation:qbspin 1s linear infinite}
  @keyframes qbspin{to{transform:rotate(360deg)}}
  .queue-banner .qb-title{font-weight:600;color:var(--gold2)}
  .queue-banner .qb-sub{font-size:.85rem;color:var(--muted);margin-top:2px}

  .log-box{background:#050510;border:1px solid var(--border);border-radius:8px;
    padding:14px;height:280px;overflow-y:auto;
    font-family:'Fira Code','Cascadia Code',Consolas,monospace;font-size:0.76rem;line-height:1.6}
  .log-box::-webkit-scrollbar{width:4px}
  .log-box::-webkit-scrollbar-thumb{background:var(--border);border-radius:99px}
  .log-entry{display:flex;gap:10px;padding:2px 0}
  .log-ts{color:#333355;flex-shrink:0}
  .log-msg{color:var(--text);word-break:break-word}
  .log-msg.success{color:var(--green)}
  .log-msg.error{color:var(--red)}
  .log-msg.warn{color:var(--amber)}

  .downloads-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .dl-card{background:var(--surface2);border:1px solid var(--border);
    border-radius:10px;padding:20px;text-align:center}
  .dl-card .dl-title{font-size:0.95rem;font-weight:700;color:var(--gold);margin-bottom:6px}
  .dl-card .dl-sub{font-size:0.78rem;color:var(--muted);margin-bottom:14px;line-height:1.5}
  .individual-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px}
  .ind-card{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
    padding:12px 14px;display:flex;flex-direction:column;gap:8px}
  .ind-card .ind-name{font-size:0.78rem;font-weight:600;color:var(--text);
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .ind-card .ind-type{font-size:0.68rem;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}

  .status-pill{display:inline-flex;align-items:center;gap:6px;font-size:0.76rem;
    font-weight:600;padding:4px 12px;border-radius:99px;margin-left:8px}
  .pill-idle{background:rgba(122,122,154,.12);color:var(--muted)}
  .pill-running{background:rgba(212,175,55,.15);color:var(--gold)}
  .pill-done{background:rgba(34,197,94,.15);color:var(--green)}
  .pill-error{background:rgba(239,68,68,.15);color:var(--red)}
  .dot{width:7px;height:7px;border-radius:50%;background:currentColor}
  .dot.pulse{animation:pulse 1.4s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

  .section-label{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
  .hint{font-size:0.76rem;color:var(--muted);margin-top:4px}
  .divider{border:none;border-top:1px solid var(--border);margin:20px 0}
  .hidden{display:none!important}
  a{color:var(--gold2);text-decoration:none}
  a:hover{text-decoration:underline}
  .pipeline-steps{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}
  .step{background:var(--surface2);border:1px solid var(--border);border-radius:8px;
    padding:10px 12px;font-size:0.78rem;color:var(--muted)}
  .step.done{border-color:rgba(34,197,94,.4);color:var(--green)}
  .step.active{border-color:var(--gold);color:var(--gold2)}
  .verdict-yes     {background:rgba(63,185,80,.15)!important;color:#3fb950!important;border-color:#3fb950!important}
  .verdict-likely  {background:rgba(88,166,255,.15)!important;color:#58a6ff!important;border-color:#58a6ff!important}
  .verdict-uncertain{background:rgba(240,165,0,.15)!important;color:#f0a500!important;border-color:#f0a500!important}
  .verdict-unlikely{background:rgba(163,113,247,.15)!important;color:#a371f7!important;border-color:#a371f7!important}
  .verdict-no      {background:rgba(224,85,85,.15)!important;color:#e05555!important;border-color:#e05555!important}
  .horary-dual-grid{display:grid;gap:20px;grid-template-columns:1fr 1fr}
  .horary-lane{border:1px solid var(--border);border-radius:12px;padding:16px;background:var(--surface2)}
  .horary-lane-title{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:10px}
  .horary-na{font-size:0.8rem;color:var(--muted);font-style:italic}
  @media(max-width:720px){.horary-dual-grid{grid-template-columns:1fr}}
  @media(max-width:900px){
    .app-shell{flex-direction:column}
    .sidebar{width:100%;height:auto;position:relative;border-right:none;border-bottom:1px solid var(--border);
      display:flex;flex-wrap:wrap;gap:4px;padding:10px}
    .sidebar-title{display:none}
    .nav-item{width:auto;flex:1 1 calc(50% - 4px);min-width:140px;margin:0;justify-content:center;padding:8px 10px;font-size:0.78rem}
    .main-content{padding:16px 12px 40px}
  }
  @media(max-width:600px){.field-row{grid-template-columns:1fr}.downloads-grid{grid-template-columns:1fr}
    .pipeline-steps{grid-template-columns:1fr 1fr}.nav-item{flex:1 1 100%}}
</style>
</head>
<body>

<div class="app-header">
  <h1>✦ Vedic Astrology Report Generator</h1>
  <p>Multi-system Vedic predictions · PyJHora charts · Book-backed lanes</p>
  <div style="margin-top:10px;display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap">
    <span id="session-badge" style="font-size:0.72rem;color:var(--muted);background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:3px 10px;font-family:monospace"></span>
    <button class="btn btn-outline" onclick="clearSession()" style="font-size:0.75rem;padding:5px 14px;color:var(--muted);border-color:var(--border)">
      <span>🔄</span> New Session
    </button>
  </div>
</div>

<div class="app-shell">
<nav class="sidebar" id="sidebar">
  <div class="sidebar-title">Sections</div>
  <button type="button" class="nav-item active" data-section="vedic" onclick="showSection('vedic')"><span class="nav-icon">☸</span>Vedic Reports</button>
  <button type="button" class="nav-item" data-section="palmistry" onclick="showSection('palmistry')"><span class="nav-icon">🖐️</span>Palmistry</button>
  <button type="button" class="nav-item" data-section="numerology" onclick="showSection('numerology')"><span class="nav-icon">🔢</span>Numerology</button>
  <button type="button" class="nav-item" data-section="btr" onclick="showSection('btr')"><span class="nav-icon">🕐</span>BTR</button>
  <button type="button" class="nav-item" data-section="event" onclick="showSection('event')"><span class="nav-icon">📆</span>Event Predictor</button>
  <button type="button" class="nav-item" data-section="question" onclick="showSection('question')"><span class="nav-icon">❓</span>User Question</button>
  <button type="button" class="nav-item" data-section="horary" onclick="showSection('horary')"><span class="nav-icon">🔮</span>Horary</button>
  <button type="button" class="nav-item" data-section="marriage" onclick="showSection('marriage')"><span class="nav-icon">💑</span>Marriage Match</button>
  <button type="button" class="nav-item" data-section="muhurat" onclick="showSection('muhurat')"><span class="nav-icon">🕉</span>Muhurat</button>
  <button type="button" class="nav-item" data-section="daily" onclick="showSection('daily')"><span class="nav-icon">📅</span>Daily Forecast</button>
</nav>

<main class="main-content">

<!-- Shared client birth data (all sections) -->
<details class="card client-strip" id="client-strip" open>
  <summary style="cursor:pointer;list-style:none;display:flex;align-items:center;justify-content:space-between;gap:8px">
    <span class="card-title" style="margin:0">👤 Client Birth Details</span>
    <span style="font-size:0.72rem;color:var(--muted)">click to expand/collapse</span>
  </summary>
  <div style="margin-top:14px">
  <div class="profile-bar">
    <div class="profile-grow">
      <label>Saved profile (nickname)</label>
      <select id="client-profile-select" onchange="onProfileSelect(this.value,'client')">
        <option value="">-- Select nickname --</option>
      </select>
    </div>
    <div class="profile-grow">
      <label>Nickname to save as</label>
      <input type="text" id="profile-nickname-input" placeholder="e.g. Sample, Partner"/>
    </div>
    <div style="display:flex;gap:6px;flex-wrap:wrap">
      <button type="button" class="btn btn-outline" onclick="saveBirthProfile()" style="font-size:0.78rem;padding:6px 12px">Save profile</button>
      <button type="button" class="btn btn-outline" onclick="deleteBirthProfile()" style="font-size:0.78rem;padding:6px 12px;color:var(--red)">Delete</button>
    </div>
  </div>
  <p class="hint" style="margin-top:-6px;margin-bottom:12px">Save name, DOB, time, gender, place and optional BTR events under a nickname. Pick from the dropdown to auto-fill.</p>
  <div class="field-row">
    <div>
      <label>Full Name <span style="color:#ef4444">*</span></label>
      <input type="text" id="client-name" placeholder="e.g. Sample User" required/>
    </div>
    <div>
      <label>Date of Birth <span style="color:#ef4444">*</span> <span style="color:#7a7a9a">(YYYY-MM-DD)</span></label>
      <input type="text" id="client-dob" placeholder="e.g. 1989-07-29" required/>
    </div>
    <div>
      <label>Gender</label>
      <select id="client-gender">
        <option value="Male">Male</option>
        <option value="Female">Female</option>
        <option value="Other">Other / Not specified</option>
      </select>
    </div>
  </div>
  <div class="field-row">
    <div>
      <label>Time of Birth <span style="color:#ef4444">*</span> <span style="color:#7a7a9a">(24-hr HH:MM)</span></label>
      <input type="text" id="client-tob" placeholder="e.g. 13:05" required/>
    </div>
    <div style="grid-column:span 2" class="place-wrap" id="place-wrap">
      <label>Place of Birth <span style="color:#ef4444">*</span> <span style="color:#7a7a9a">(city, country)</span></label>
      <input type="text" id="client-place" placeholder="Start typing — e.g. New Delhi" autocomplete="off" required/>
      <ul class="place-suggestions hidden" id="place-suggestions"></ul>
      <input type="hidden" id="place-lat"/>
      <input type="hidden" id="place-lon"/>
      <input type="hidden" id="place-tz"/>
    </div>
  </div>
  <p class="hint">Charts use PyJHora (Lahiri + KP ayanamsa). Pick your city from the dropdown for correct latitude, longitude, and timezone.</p>
  </div>
</details>

<!-- ═══ VEDIC ═══ -->
<div class="section-panel active" id="section-vedic">
  <div class="section-head">
    <h2>Vedic Reports</h2>
    <p>Generate full multi-lane Vedic chart analysis — BNN, KP, Jaimini, Vimshottari, Ashtakavarga, confluence, and more. Palmistry and numerology are separate sections.</p>
  </div>

  <div class="card" id="input-card">
    <div class="field">
      <label>Known Life Events for Calibration <span style="color:#7a7a9a">(optional — improves prediction accuracy)</span></label>
      <textarea id="life-events" rows="4"
        placeholder="List confirmed events with approximate dates, one per line.&#10;e.g. First job: 2009&#10;Marriage: 2016&#10;First child (son): 2018&#10;Job change + relocation: 2019"></textarea>
      <p class="hint">📌 At least 5 events dramatically improves confidence from MODERATE → HIGH</p>
    </div>
    <div class="btn-row">
      <button class="btn btn-gold" id="start-btn" disabled onclick="startGeneration()">
        <span>▶</span> Generate Reports
      </button>
      <button class="btn btn-outline" onclick="clearAll()"><span>✕</span> Clear</button>
      <span id="status-pill" class="status-pill pill-idle"><span class="dot"></span>Idle</span>
    </div>
    <div class="progress-wrap hidden" id="progress-wrap">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="progress-bar"></div></div>
    </div>
    <div class="queue-banner hidden" id="queue-banner">
      <div class="qb-spinner"></div>
      <div class="qb-text">
        <div class="qb-title" id="qb-title">Waiting in queue…</div>
        <div class="qb-sub" id="qb-sub">Your report will start automatically.</div>
      </div>
    </div>
  </div>

  <div class="card hidden" id="pipeline-card">
    <div class="card-title">⚙️ Pipeline Progress</div>
    <div class="pipeline-steps" id="pipeline-steps">
      <div class="step" id="step-extract">🔭 Build Chart</div>
      <div class="step" id="step-pillar">🏛️ Pillar of Life</div>
      <div class="step" id="step-bnn">📖 BNN Analysis</div>
      <div class="step" id="step-bhardwaj">📚 Bhardwaj</div>
      <div class="step" id="step-kp">🔭 KP System</div>
      <div class="step" id="step-jaimini">⚖️ Jaimini</div>
      <div class="step" id="step-vimshottari">⏳ Vimshottari</div>
      <div class="step" id="step-yogini">🌙 Yogini Dasha</div>
      <div class="step" id="step-ashta">📊 Ashtakavarga</div>
      <div class="step" id="step-rtvd">📅 RTVD</div>
      <div class="step" id="step-longevity">⚕️ Longevity</div>
      <div class="step" id="step-blind">🎯 Blind Chart</div>
      <div class="step" id="step-conf">✦ Confluence</div>
      <div class="step" id="step-user">📱 User Report</div>
    </div>
  </div>

  <div class="card">
    <div class="section-label">
      <div class="card-title" style="margin-bottom:0">📋 Live Progress Log</div>
      <button class="btn btn-outline" style="padding:4px 12px;font-size:.73rem" onclick="clearLog()">Clear</button>
    </div>
    <div class="log-box" id="log-box">
      <div class="log-entry">
        <span class="log-ts">--:--:--</span>
        <span class="log-msg" style="color:#333355">Ready. Enter birth details and press Generate Reports.</span>
      </div>
    </div>
  </div>

  <div class="card hidden" id="downloads-card">
    <div class="card-title">📥 Your Reports Are Ready — <span id="client-label" style="color:var(--gold)"></span></div>
    <div class="downloads-grid">
      <div class="dl-card">
        <div class="dl-title">✦ Technical Confluence</div>
        <div class="dl-sub">Full multi-system analysis · Confidence vote table · All 12+ systems · Remedies · For the analyst</div>
        <div id="dl-confluence"></div>
      </div>
      <div class="dl-card">
        <div class="dl-title">📱 Client User Report</div>
        <div class="dl-sub">Plain English · Date-first predictions · Traffic light summary · No jargon · For the client</div>
        <div id="dl-user"></div>
      </div>
    </div>
    <div class="card hidden" id="cursor-human-card" style="margin-top:16px;border-color:var(--gold)">
      <div class="card-title">✨ Cursor Human Report <span style="font-size:.75rem;color:var(--muted);font-weight:400">(optional — AI narrative)</span></div>
      <p class="hint" style="margin-bottom:12px">Python reports above are deterministic and book-backed. Use this to generate a warmer, human-style confluence + client report via <strong>Cursor CLI</strong> — grounded in the same lane HTML, birth data, and precomputed chart.</p>
      <button class="btn btn-gold" id="cursor-human-btn" onclick="runCursorHumanReport()" style="margin-bottom:12px">
        <span>🤖</span> Generate Cursor Human Report
      </button>
      <div id="cursor-human-status" class="hint" style="margin-bottom:10px"></div>
      <div class="downloads-grid" id="cursor-human-dls" style="display:none">
        <div class="dl-card">
          <div class="dl-title">✦ Cursor Confluence</div>
          <div class="dl-sub">Human narrative · multi-system synthesis</div>
          <div id="dl-cursor-confluence"></div>
        </div>
        <div class="dl-card">
          <div class="dl-title">📱 Cursor Client Report</div>
          <div class="dl-sub">Plain English · conversational tone</div>
          <div id="dl-cursor-user"></div>
        </div>
      </div>
      <div id="cursor-chat-section" class="hidden" style="margin-top:18px;padding-top:16px;border-top:1px solid var(--border)">
        <div class="card-title" style="font-size:1rem">💬 Follow-up with Cursor</div>
        <p class="hint">Ask a follow-up about this chart. Context includes prior chat turns.</p>
        <textarea id="cursor-chat-input" rows="3" placeholder="e.g. What does my chart say about career change in 2027?" style="width:100%;margin:8px 0;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-family:inherit;font-size:.9rem"></textarea>
        <button class="btn btn-outline" id="cursor-chat-btn" onclick="sendCursorChat()">Send follow-up</button>
        <div id="cursor-chat-log" style="margin-top:12px;max-height:280px;overflow-y:auto;font-size:.88rem;line-height:1.55"></div>
      </div>
    </div>
    <div style="margin-top:20px">
      <div class="card-title" style="margin-bottom:12px">📂 All Individual Lane Reports</div>
      <div class="individual-grid" id="individual-grid"></div>
    </div>
  </div>
</div>

<!-- ═══ PALMISTRY ═══ -->
<div class="section-panel" id="section-palmistry">
  <div class="section-head">
    <h2>Palmistry</h2>
    <p>Upload palm photos for a standalone book-backed palm reading (CV + multi-book confluence). Uses client name from above.</p>
  </div>
  <div class="card">
    <div class="field">
      <label>Palm Print Images <span style="color:#ef4444">*</span> <span style="color:#7a7a9a">(right + left hand)</span></label>
      <input type="file" id="img-input" accept=".jpg,.jpeg,.png" multiple/>
      <label for="img-input" class="drop-zone" id="img-drop">
        <span class="drop-icon">🖐️</span>
        <span class="drop-label">Drop palm photos here, or click to browse</span>
        <span class="drop-hint">JPG / PNG · Upload both palms · Right palm = dominant / lived life</span>
      </label>
      <div class="file-list" id="img-list"></div>
    </div>
    <div class="field" style="max-width:280px">
      <label>Dominant hand <span style="color:#7a7a9a">(active / lived life)</span></label>
      <select id="palm-active-hand">
        <option value="right">Right hand (default)</option>
        <option value="left">Left hand</option>
      </select>
    </div>
    <div class="btn-row">
      <button type="button" class="btn btn-gold" id="palmistry-btn" disabled onclick="runPalmistryReport()">
        <span>🖐️</span> Generate Palmistry Report
      </button>
      <span id="palmistry-pill" class="status-pill pill-idle"><span class="dot"></span>Idle</span>
    </div>
    <div class="progress-wrap hidden" id="palm-progress-wrap">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="palm-progress-bar" style="background:linear-gradient(90deg,#c8a020,#d4af37)"></div></div>
    </div>
    <div id="palmistry-result" style="margin-top:12px"></div>
  </div>
</div>

<!-- ═══ NUMEROLOGY ═══ -->
<div class="section-panel" id="section-numerology">
  <div class="section-head">
    <h2>Numerology</h2>
    <p>Standalone name + DOB numerology report — Mahā/Antar/Pratyantar dasha, Lo Shu grid, career, relationship, remedies (book-backed).</p>
  </div>
  <div class="card">
    <p class="hint" style="margin-bottom:14px">Uses <strong>full name</strong>, <strong>date of birth</strong>, and <strong>gender</strong> from client details above. Birth time and place are not required.</p>
    <div class="btn-row">
      <button type="button" class="btn btn-gold" id="numerology-btn" disabled onclick="runNumerologyReport()">
        <span>🔢</span> Generate Numerology Report
      </button>
      <span id="numerology-pill" class="status-pill pill-idle"><span class="dot"></span>Idle</span>
    </div>
    <div class="progress-wrap hidden" id="num-progress-wrap">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="num-progress-bar" style="background:linear-gradient(90deg,#58a6ff,#a371f7)"></div></div>
    </div>
    <div id="numerology-result" style="margin-top:12px"></div>
  </div>
</div>

<!-- ═══ BTR ═══ -->
<div class="section-panel" id="section-btr">
  <div class="section-head">
    <h2>Birth Time Rectification</h2>
    <p>Enter 3+ confirmed life-event dates. Scans ±90 min, then D60-grade ±4 min when a shift is likely.</p>
  </div>
  <div class="card">
    <div class="field-row">
      <div>
        <label>Higher education <span style="color:#7a7a9a">(optional)</span></label>
        <input type="text" id="btr-education" placeholder="e.g. 2011-06"/>
      </div>
      <div>
        <label>Foreign travel / major move <span style="color:#7a7a9a">(optional)</span></label>
        <input type="text" id="btr-foreign" placeholder="e.g. 2019-03-15"/>
      </div>
      <div>
        <label>Marriage <span style="color:#7a7a9a">(optional)</span></label>
        <input type="text" id="btr-marriage" placeholder="e.g. 2016-11"/>
      </div>
    </div>
    <div class="field-row">
      <div>
        <label>First child <span style="color:#7a7a9a">(optional)</span></label>
        <input type="text" id="btr-child" placeholder="e.g. 2018-07"/>
      </div>
      <div>
        <label>First job <span style="color:#7a7a9a">(optional)</span></label>
        <input type="text" id="btr-job" placeholder="e.g. 2010-08"/>
      </div>
      <div style="display:flex;align-items:flex-end">
        <button type="button" class="btn btn-outline" id="btr-btn" onclick="runBtrCheck()" style="width:100%;justify-content:center">Verify birth time</button>
      </div>
    </div>
    <div class="field">
      <label>Other life events <span style="color:#7a7a9a">(optional)</span></label>
      <textarea id="btr-custom" rows="4" placeholder="One per line, e.g.&#10;MBA completed: 2012-05&#10;Father passed: 2014-08 | death&#10;Bought flat: 2020-03 | property"></textarea>
    </div>
    <div id="btr-result" class="hidden"></div>
  </div>
</div>

<!-- ═══ EVENT PREDICTOR ═══ -->
<div class="section-panel" id="section-event">
  <div class="section-head">
    <h2>Event Predictor</h2>
    <p>Predicts the <strong>next</strong> window from today using Vimshottari + Chara overlap + multi-lagna check.</p>
  </div>
  <div class="card">
    <div class="field-row">
      <div>
        <label>Rectified birth time <span style="color:#7a7a9a">(optional)</span></label>
        <input type="time" id="future-birth-time" placeholder="Uses birth time if empty"/>
      </div>
      <div>
        <label>Event to predict</label>
        <select id="future-event-type">
          <option value="marriage">Marriage</option>
          <option value="child_birth">Child birth</option>
          <option value="job_change">Job change / new role</option>
          <option value="promotion">Promotion / recognition</option>
          <option value="house_purchase">House / property purchase</option>
          <option value="higher_education">Higher education milestone</option>
          <option value="foreign_relocation">Foreign relocation</option>
          <option value="business_start">Business start</option>
          <option value="recovery">Recovery from illness</option>
          <option value="wealth_rise">Business / wealth rise</option>
          <option value="status_uplift">Social status upliftment</option>
        </select>
      </div>
      <div style="display:flex;align-items:flex-end">
        <button type="button" class="btn btn-outline" id="future-btn" onclick="runFutureEventPredict()" style="width:100%;justify-content:center">Predict next window</button>
      </div>
    </div>
    <div id="future-result" class="hidden"></div>
  </div>
</div>

<!-- ═══ USER QUESTION ═══ -->
<div class="section-panel" id="section-question">
  <div class="section-head">
    <h2>User Question</h2>
    <p>One focused confluence report for a single life area — routes to relevant houses and all techniques.</p>
  </div>
  <div class="card">
    <div class="field">
      <label>Your Main Question <span style="color:#ef4444">*</span></label>
      <textarea id="client-question" rows="3"
        placeholder="Ask one clear question about a single area.&#10;e.g. Will I recover from this illness?&#10;e.g. When is marriage most likely?"></textarea>
      <p class="hint">Routes to houses (e.g. H2 speech, H6 health/legal, H7 spouse) — confluence answer, not one dasha guess</p>
      <div class="btn-row" style="margin-top:8px">
        <button type="button" class="btn btn-outline" id="main-question-btn" onclick="runMainQuestion()">Answer Main Question</button>
      </div>
      <div id="main-question-result" class="hidden" style="margin-top:10px"></div>
      <details style="margin-top:10px;font-size:0.88rem">
        <summary style="cursor:pointer;color:var(--muted)">Related person (optional — child/spouse for dual-chart timing)</summary>
        <div class="grid2" style="margin-top:8px;gap:8px">
          <input type="text" id="related-name" placeholder="Name e.g. Child"/>
          <select id="related-role"><option value="child">Child</option><option value="spouse">Spouse</option><option value="other">Other</option></select>
          <input type="text" id="related-dob" placeholder="DOB e.g. 01/01/2018"/>
          <input type="text" id="related-tob" placeholder="Time e.g. 12:30 PM"/>
          <input type="text" id="related-place" placeholder="Place e.g. Noida, UP" style="grid-column:1/-1"/>
        </div>
        <p class="hint">Dual-chart overlap sharpens &ldquo;when&rdquo; questions (speech, child development).</p>
      </details>
    </div>
  </div>
  <div class="card" style="margin-top:14px;border-color:var(--gold)">
    <div class="card-title" style="font-size:1rem">💬 Follow-up with Cursor (AI)</div>
    <p class="hint" style="margin-bottom:8px">Ask a free-form follow-up about this chart in plain language — context carries across turns. Requires the Vedic reports to be generated first (Vedic Reports → Generate) so Cursor has the chart context.</p>
    <textarea id="q-cursor-chat-input" rows="3" placeholder="e.g. Based on my chart, how should I prepare for the marriage window you mentioned?" style="width:100%;margin:4px 0 8px;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-family:inherit;font-size:.9rem"></textarea>
    <button type="button" class="btn btn-outline" id="q-cursor-chat-btn" onclick="sendCursorChat('q-cursor-chat-input','q-cursor-chat-btn','q-cursor-chat-log')">Send follow-up</button>
    <div id="q-cursor-chat-log" style="margin-top:12px;max-height:300px;overflow-y:auto;font-size:.88rem;line-height:1.55"></div>
  </div>
</div>

<!-- ═══ HORARY ═══ -->
<div class="section-panel" id="section-horary">
  <div class="section-head">
    <h2>Horary / Prashna</h2>
    <p>Ask a specific question — no birth chart needed. Vedic confluence + Western horary as separate reports.</p>
  </div>
  <div class="card" id="horary-card">
    <div class="field">
      <label>Your Question <span style="color:#ef4444">*</span></label>
      <textarea id="h-question" rows="3" placeholder="Ask one clear, specific question.&#10;e.g. Will I get the job I interviewed for this week?"></textarea>
    </div>
    <div class="field-row">
      <div>
        <label>Date of Question</label>
        <input type="text" id="h-date" placeholder="YYYY-MM-DD"/>
      </div>
      <div>
        <label>Time of Question (HH:MM, 24-hr)</label>
        <input type="text" id="h-time" placeholder="e.g. 14:35"/>
      </div>
      <div>
        <label>Location (city, country)</label>
        <input type="text" id="h-location" placeholder="e.g. New Delhi, India"/>
      </div>
    </div>
    <div class="field" style="max-width:220px">
      <label>KP Number <span style="color:#7a7a9a">(1–249 · leave blank to auto-derive)</span></label>
      <input type="text" id="h-kp" placeholder="e.g. 108"/>
    </div>
    <div class="btn-row" style="margin-top:4px">
      <button class="btn btn-gold" id="horary-btn" onclick="submitHorary()">
        <span>🔮</span> Get Horary Answer
      </button>
      <span id="horary-pill" class="status-pill pill-idle"><span class="dot"></span>Idle</span>
    </div>
    <div class="progress-wrap hidden" id="h-progress-wrap">
      <div class="progress-bar-bg"><div class="progress-bar-fill" id="h-progress-bar" style="background:linear-gradient(90deg,#a371f7,#58a6ff)"></div></div>
    </div>
  </div>
  <div class="card hidden" id="horary-result-card">
    <div class="card-title">🔮 Horary Results</div>
    <p class="hint" style="margin-bottom:14px">Two independent judgments. Open each report separately.</p>
    <div id="h-question-display" style="font-size:0.9rem;color:var(--text);font-style:italic;margin-bottom:16px"></div>
    <div class="horary-dual-grid">
      <div class="horary-lane">
        <div class="horary-lane-title" style="color:var(--gold)">☸ Vedic horary (confluence)</div>
        <div id="h-vedic-verdict-badge" style="font-size:1.15rem;font-weight:800;padding:8px 18px;border-radius:10px;border:2px solid;margin-bottom:8px;width:fit-content"></div>
        <div id="h-vedic-confidence" style="font-size:0.78rem;color:var(--muted);margin-bottom:10px"></div>
        <div id="h-vedic-dl"></div>
      </div>
      <div class="horary-lane">
        <div class="horary-lane-title" style="color:#58a6ff">◆ Western horary (Tropical)</div>
        <div id="h-western-verdict-badge" style="font-size:1.15rem;font-weight:800;padding:8px 18px;border-radius:10px;border:2px solid;margin-bottom:8px;width:fit-content"></div>
        <div id="h-western-confidence" style="font-size:0.78rem;color:var(--muted);margin-bottom:10px"></div>
        <div id="h-western-dl"></div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ MARRIAGE ═══ -->
<div class="section-panel" id="section-marriage">
  <div class="section-head">
    <h2>Marriage Compatibility</h2>
    <p>36 Guna Ashtakoota + Manglik/Nadi/Bhakoot + Goel Navamsha synastry + Navamsha (D9) compatibility.</p>
  </div>
  <div class="card">
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px">
      <button type="button" class="btn btn-outline" onclick="matchUseClientAsGroom()" style="font-size:0.78rem;padding:6px 12px">Use client above as groom</button>
      <label style="font-size:0.85rem;color:var(--muted)">Method
        <select id="match-method" style="margin-left:6px;padding:6px;border-radius:6px;background:var(--surface);color:var(--text);border:1px solid var(--border)">
          <option value="North">North — 36 Guna</option>
          <option value="South">South — 10 Porutham</option>
        </select>
      </label>
    </div>
    <p class="hint" style="margin-bottom:6px"><strong>Groom</strong></p>
    <div class="profile-inline">
      <label style="font-size:0.82rem;color:var(--muted)">Load groom profile</label>
      <select id="groom-profile-select" onchange="onProfileSelect(this.value,'groom')">
        <option value="">-- Nickname --</option>
      </select>
    </div>
    <div class="field-row">
      <div><label>Name</label><input type="text" id="groom-name" placeholder="Groom name"/></div>
      <div><label>DOB</label><input type="text" id="groom-dob" placeholder="YYYY-MM-DD"/></div>
      <div><label>Time</label><input type="text" id="groom-tob" placeholder="HH:MM"/></div>
    </div>
    <div class="place-wrap" id="groom-place-wrap" style="margin-bottom:12px">
      <label>Place of birth</label>
      <input type="text" id="groom-place" placeholder="City, country" autocomplete="off"/>
      <ul class="place-suggestions hidden" id="groom-place-suggestions"></ul>
      <input type="hidden" id="groom-place-lat"/><input type="hidden" id="groom-place-lon"/><input type="hidden" id="groom-place-tz"/>
    </div>
    <p class="hint" style="margin-bottom:6px"><strong>Bride</strong></p>
    <div class="profile-inline">
      <label style="font-size:0.82rem;color:var(--muted)">Load bride profile</label>
      <select id="bride-profile-select" onchange="onProfileSelect(this.value,'bride')">
        <option value="">-- Nickname --</option>
      </select>
    </div>
    <div class="field-row">
      <div><label>Name</label><input type="text" id="bride-name" placeholder="Bride name"/></div>
      <div><label>DOB</label><input type="text" id="bride-dob" placeholder="YYYY-MM-DD"/></div>
      <div><label>Time</label><input type="text" id="bride-tob" placeholder="HH:MM"/></div>
    </div>
    <div class="place-wrap" id="bride-place-wrap" style="margin-bottom:12px">
      <label>Place of birth</label>
      <input type="text" id="bride-place" placeholder="City, country" autocomplete="off"/>
      <ul class="place-suggestions hidden" id="bride-place-suggestions"></ul>
      <input type="hidden" id="bride-place-lat"/><input type="hidden" id="bride-place-lon"/><input type="hidden" id="bride-place-tz"/>
    </div>
    <button type="button" class="btn btn-outline" id="kundali-match-btn" onclick="runKundaliMatch()" style="width:100%;justify-content:center">Match kundali</button>
    <div id="kundali-match-result" style="margin-top:10px"></div>
  </div>
</div>

<!-- ═══ MUHURAT ═══ -->
<div class="section-panel" id="section-muhurat">
  <div class="section-head">
    <h2>Muhurat Checking</h2>
    <p>Panchang (tithi, nakshatra, choghadiya, Rahu Kaal) for any event day. Event location is separate from birth place.</p>
  </div>
  <div class="card">
    <div class="field" style="margin-bottom:12px">
      <label>Event location for panchang <span style="color:#7a7a9a">(city where the event happens)</span></label>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0 8px">
        <button type="button" class="btn btn-outline" onclick="muhuratUseBirthPlace()" style="font-size:0.78rem;padding:6px 12px">Use birth place</button>
        <button type="button" class="btn btn-outline" onclick="muhuratUseCurrentLocation()" style="font-size:0.78rem;padding:6px 12px">Use my current location</button>
      </div>
      <div class="place-wrap" id="muhurat-place-wrap">
        <input type="text" id="muhurat-place" placeholder="Start typing — e.g. Mumbai, India" autocomplete="off"/>
        <ul class="place-suggestions hidden" id="muhurat-place-suggestions"></ul>
        <input type="hidden" id="muhurat-place-lat"/>
        <input type="hidden" id="muhurat-place-lon"/>
        <input type="hidden" id="muhurat-place-tz"/>
      </div>
    </div>
    <div class="field-row">
      <div>
        <label>Event type</label>
        <select id="muhurat-event-type" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text)"></select>
      </div>
      <div>
        <label>Date to check <span style="color:#7a7a9a">(optional)</span></label>
        <input type="date" id="muhurat-check-date" style="width:100%;padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text)"/>
      </div>
      <div style="display:flex;align-items:flex-end">
        <button type="button" class="btn btn-outline" id="muhurat-check-btn" onclick="runMuhuratCheck()" style="width:100%;justify-content:center">Check muhurat</button>
      </div>
    </div>
    <div id="muhurat-check-result" style="margin-top:10px"></div>
  </div>
</div>

<!-- ═══ DAILY FORECAST ═══ -->
<div class="section-panel" id="section-daily">
  <div class="section-head">
    <h2>Daily Forecast</h2>
    <p>Chart-specific day guide: Vimshottari MD/AD/PD, Moon transit, gochar, Ashtakavarga, Tarabala, Moonology lane.</p>
  </div>
  <div class="card" id="daily-moon-card" style="border-color:#6b5b95">
    <p class="hint" style="margin-bottom:12px">Generate Vedic reports first (or restore a session) so the chart is available. Then pick a date.</p>
    <div class="grid2" style="gap:10px;margin-bottom:12px">
      <input type="date" id="daily-moon-date" style="padding:10px;border-radius:8px;border:1px solid var(--border);background:var(--surface);color:var(--text)"/>
      <button class="btn btn-outline" id="daily-moon-btn" onclick="fetchDailyMoon()">Get today's guide</button>
    </div>
    <div id="daily-moon-result" class="hint"></div>
    <div id="daily-moon-dl" style="margin-top:8px"></div>
  </div>
</div>

</main>
</div>

<script>
function showSection(id){
  document.querySelectorAll('.section-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  const panel=document.getElementById('section-'+id);
  const nav=document.querySelector('.nav-item[data-section="'+id+'"]');
  if(panel) panel.classList.add('active');
  if(nav) nav.classList.add('active');
  try{history.replaceState(null,'','#'+id);}catch(_){}
  window.scrollTo({top:0,behavior:'smooth'});
}
(function(){
  const hash=(location.hash||'').replace(/^#/,'');
  const valid=['vedic','palmistry','numerology','btr','event','question','horary','marriage','muhurat','daily'];
  if(hash&&valid.includes(hash)) showSection(hash);
})();

function uuid4() {
  try{return crypto.randomUUID()}catch(_){}
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{
    const r=Math.random()*16|0;return(c==='x'?r:(r&0x3|0x8)).toString(16);});
}

// ── Session persistence (survive page refresh) ──────────────────────
const LS_ID  = 'astro_session_id';
const LS_LOG = 'astro_session_log';
const LS_DONE= 'astro_session_done';
const LS_PROFILES = 'astro_saved_profiles';

function loadProfiles() {
  try { return JSON.parse(localStorage.getItem(LS_PROFILES) || '{}'); }
  catch(_) { return {}; }
}
function storeProfiles(profiles) {
  localStorage.setItem(LS_PROFILES, JSON.stringify(profiles));
}
function profileNicknames() {
  return Object.keys(loadProfiles()).sort((a, b) => a.localeCompare(b, undefined, {sensitivity: 'base'}));
}
function refreshProfileDropdowns(selected) {
  const nicks = profileNicknames();
  ['client-profile-select', 'groom-profile-select', 'bride-profile-select'].forEach((id, i) => {
    const sel = document.getElementById(id);
    if (!sel) return;
    const cur = selected && selected[id] !== undefined ? selected[id] : sel.value;
    sel.innerHTML = '<option value="">' + (id === 'client-profile-select' ? '-- Select nickname --' : '-- Nickname --') + '</option>';
    nicks.forEach(n => {
      const opt = document.createElement('option');
      opt.value = n;
      opt.textContent = n;
      sel.appendChild(opt);
    });
    if (cur && nicks.includes(cur)) sel.value = cur;
  });
}
function readClientFormAsProfile() {
  const btrCustom = document.getElementById('btr-custom');
  return {
    name: document.getElementById('client-name').value.trim(),
    dob: document.getElementById('client-dob').value.trim(),
    tob: document.getElementById('client-tob').value.trim(),
    gender: document.getElementById('client-gender').value,
    place: document.getElementById('client-place').value.trim(),
    lat: document.getElementById('place-lat').value,
    lon: document.getElementById('place-lon').value,
    tz: document.getElementById('place-tz').value,
    btr_education: (document.getElementById('btr-education') || {}).value?.trim() || '',
    btr_foreign: (document.getElementById('btr-foreign') || {}).value?.trim() || '',
    btr_marriage: (document.getElementById('btr-marriage') || {}).value?.trim() || '',
    btr_child: (document.getElementById('btr-child') || {}).value?.trim() || '',
    btr_job: (document.getElementById('btr-job') || {}).value?.trim() || '',
    btr_custom: btrCustom ? btrCustom.value.trim() : '',
  };
}
function applyPlaceFromProfile(p, cfg) {
  if (p.place && p.lat && p.lon && p.tz) {
    selectPlace({
      label: p.place,
      latitude: parseFloat(p.lat),
      longitude: parseFloat(p.lon),
      timezone: parseFloat(p.tz),
    }, cfg);
  } else {
    document.getElementById(cfg.inputId).value = p.place || '';
    clearPlaceSelection(cfg);
  }
}
function applyProfileToTarget(p, target) {
  if (!p) return;
  if (target === 'client' || target === 'groom' || target === 'bride') {
    const maps = {
      client: {name: 'client-name', dob: 'client-dob', tob: 'client-tob', gender: 'client-gender', placeCfg: BIRTH_PLACE_CFG},
      groom: {name: 'groom-name', dob: 'groom-dob', tob: 'groom-tob', placeCfg: GROOM_PLACE_CFG},
      bride: {name: 'bride-name', dob: 'bride-dob', tob: 'bride-tob', placeCfg: BRIDE_PLACE_CFG},
    };
    const m = maps[target];
    if (p.name) document.getElementById(m.name).value = p.name;
    if (p.dob) document.getElementById(m.dob).value = p.dob;
    if (p.tob) document.getElementById(m.tob).value = p.tob;
    if (target === 'client' && p.gender) document.getElementById('client-gender').value = p.gender;
    applyPlaceFromProfile(p, m.placeCfg);
    if (target === 'client') {
      const btrMap = [
        ['btr_education', 'btr-education'], ['btr_foreign', 'btr-foreign'],
        ['btr_marriage', 'btr-marriage'], ['btr_child', 'btr-child'],
        ['btr_job', 'btr-job'], ['btr_custom', 'btr-custom'],
      ];
      btrMap.forEach(([k, id]) => {
        const el = document.getElementById(id);
        if (el && p[k] !== undefined) el.value = p[k] || '';
      });
      updateStartBtn();
    }
    return;
  }
}
function onProfileSelect(nickname, target) {
  if (!nickname) return;
  const p = loadProfiles()[nickname];
  if (!p) {
    appendLog('Profile "' + nickname + '" not found.', 'warn');
    refreshProfileDropdowns();
    return;
  }
  applyProfileToTarget(p, target);
  const selIds = {
    client: 'client-profile-select',
    groom: 'groom-profile-select',
    bride: 'bride-profile-select',
  };
  document.getElementById('profile-nickname-input').value = nickname;
  refreshProfileDropdowns({[selIds[target]]: nickname});
  appendLog('Loaded profile "' + nickname + '" into ' + target + ' form.', 'success');
}
function saveBirthProfile() {
  const nick = document.getElementById('profile-nickname-input').value.trim();
  if (!nick) {
    appendLog('Enter a nickname before saving.', 'warn');
    return;
  }
  const p = readClientFormAsProfile();
  if (!p.name || !p.dob || !p.tob) {
    appendLog('Name, DOB and birth time are required to save a profile.', 'warn');
    return;
  }
  if (!p.place || !p.lat || !p.lon || !p.tz) {
    appendLog('Select birth place from the dropdown before saving (coords required).', 'warn');
    return;
  }
  const profiles = loadProfiles();
  const exists = !!profiles[nick];
  profiles[nick] = {...p, saved_at: new Date().toISOString()};
  storeProfiles(profiles);
  refreshProfileDropdowns({'client-profile-select': nick});
  appendLog((exists ? 'Updated' : 'Saved') + ' profile "' + nick + '".', 'success');
}
function deleteBirthProfile() {
  const nick = document.getElementById('profile-nickname-input').value.trim()
    || document.getElementById('client-profile-select').value;
  if (!nick) {
    appendLog('Select or enter a nickname to delete.', 'warn');
    return;
  }
  const profiles = loadProfiles();
  if (!profiles[nick]) {
    appendLog('No profile named "' + nick + '".', 'warn');
    return;
  }
  if (!confirm('Delete saved profile "' + nick + '"?')) return;
  delete profiles[nick];
  storeProfiles(profiles);
  document.getElementById('profile-nickname-input').value = '';
  refreshProfileDropdowns();
  appendLog('Deleted profile "' + nick + '".', 'warn');
}

function loadOrCreateSession() {
  let sid = localStorage.getItem(LS_ID);
  if (!sid) { sid = uuid4(); localStorage.setItem(LS_ID, sid); }
  return sid;
}
const SESSION_ID = loadOrCreateSession();

function saveLog(msg, kind) {
  try {
    const logs = JSON.parse(localStorage.getItem(LS_LOG)||'[]');
    const now = new Date().toTimeString().slice(0,8);
    logs.push({ts:now, msg, kind});
    if(logs.length > 300) logs.splice(0, logs.length-300); // keep last 300
    localStorage.setItem(LS_LOG, JSON.stringify(logs));
  } catch(_) {}
}
function restoreLogs() {
  try {
    const logs = JSON.parse(localStorage.getItem(LS_LOG)||'[]');
    if(!logs.length) return;
    const box = document.getElementById('log-box');
    logs.forEach(({ts,msg,kind})=>{
      const cls=kind==='success'?'success':kind==='error'?'error':kind==='warn'?'warn':'';
      const div=document.createElement('div');div.className='log-entry';
      div.innerHTML=`<span class="log-ts">${ts}</span><span class="log-msg ${cls}">${escHtml(msg)}</span>`;
      box.appendChild(div);
    });
    box.scrollTop=box.scrollHeight;
    appendLog('↺ Session restored from previous activity.','warn');
  } catch(_) {}
}
function restoreDoneState() {
  try {
    const d = JSON.parse(localStorage.getItem(LS_DONE)||'null');
    if(!d) return;
    onDone(d, true); // true = restore mode (don't re-save)
  } catch(_) {}
}
function clearSession() {
  localStorage.removeItem(LS_ID);
  localStorage.removeItem(LS_LOG);
  localStorage.removeItem(LS_DONE);
  location.reload();
}

let imgFiles = [];
let running = false;
let ws = null;

// ── file handling (palm images only) ───────────────────────────────
setupDropZone('img-drop','img-input','img-list',false);

function setupDropZone(zoneId, inputId, listId, single) {
  const zone = document.getElementById(zoneId);
  const inp  = document.getElementById(inputId);

  zone.addEventListener('dragenter', e=>{e.preventDefault();zone.classList.add('dragover');});
  zone.addEventListener('dragover',  e=>{e.preventDefault();zone.classList.add('dragover');});
  zone.addEventListener('dragleave', e=>{if(!zone.contains(e.relatedTarget))zone.classList.remove('dragover');});
  zone.addEventListener('drop', e=>{
    e.preventDefault();zone.classList.remove('dragover');
    addFiles([...e.dataTransfer.files], single, listId);
  });
  inp.addEventListener('change', ()=>{
    if(inp.files&&inp.files.length) addFiles([...inp.files], single, listId);
    inp.value='';
  });
}

function addFiles(newFiles, single, listId) {
  const imgs = newFiles.filter(f=>/\.(jpg|jpeg|png)$/i.test(f.name));
  if(!imgs.length){appendLog('Only JPG/PNG files accepted for palm images.','warn');return;}
  imgs.forEach(f=>{if(!imgFiles.find(x=>x.name===f.name))imgFiles.push(f);});
  renderList('img-list',imgFiles,false);
  updatePalmistryBtn();
}

function renderList(listId, files) {
  const el=document.getElementById(listId);
  el.innerHTML='';
  files.forEach(f=>{
    const div=document.createElement('div');div.className='file-item';
    div.innerHTML=`<span style="font-size:1em">🖼️</span>
      <span class="file-name" title="${f.name}">${f.name}</span>
      <button class="remove-btn" onclick="removeFile('${listId}','${f.name.replace(/'/g,"\\'")}')">✕</button>`;
    el.appendChild(div);
  });
}

function removeFile(listId, name) {
  imgFiles=imgFiles.filter(x=>x.name!==name);
  renderList('img-list',imgFiles);
  updatePalmistryBtn();
}

let placeSearchTimer=null;
let placeActiveIdx=-1;
const placeWidgetState={};

const BIRTH_PLACE_CFG={
  wrapId:'place-wrap',inputId:'client-place',suggestionsId:'place-suggestions',
  latId:'place-lat',lonId:'place-lon',tzId:'place-tz',hintId:'place-selected-hint',
};
const MUHURAT_PLACE_CFG={
  wrapId:'muhurat-place-wrap',inputId:'muhurat-place',suggestionsId:'muhurat-place-suggestions',
  latId:'muhurat-place-lat',lonId:'muhurat-place-lon',tzId:'muhurat-place-tz',hintId:'muhurat-place-selected-hint',
};
const GROOM_PLACE_CFG={
  wrapId:'groom-place-wrap',inputId:'groom-place',suggestionsId:'groom-place-suggestions',
  latId:'groom-place-lat',lonId:'groom-place-lon',tzId:'groom-place-tz',hintId:'groom-place-selected-hint',
};
const BRIDE_PLACE_CFG={
  wrapId:'bride-place-wrap',inputId:'bride-place',suggestionsId:'bride-place-suggestions',
  latId:'bride-place-lat',lonId:'bride-place-lon',tzId:'bride-place-tz',hintId:'bride-place-selected-hint',
};

function clearPlaceSelection(cfg=BIRTH_PLACE_CFG){
  document.getElementById(cfg.latId).value='';
  document.getElementById(cfg.lonId).value='';
  document.getElementById(cfg.tzId).value='';
  const hint=document.getElementById(cfg.hintId);
  if(hint) hint.remove();
}

function selectPlace(item,cfg=BIRTH_PLACE_CFG){
  document.getElementById(cfg.inputId).value=item.label;
  document.getElementById(cfg.latId).value=String(item.latitude);
  document.getElementById(cfg.lonId).value=String(item.longitude);
  document.getElementById(cfg.tzId).value=String(item.timezone);
  hidePlaceSuggestions(cfg);
  const wrap=document.getElementById(cfg.wrapId);
  let hint=document.getElementById(cfg.hintId);
  if(!hint){
    hint=document.createElement('div');
    hint.id=cfg.hintId;
    hint.className='place-selected';
    wrap.appendChild(hint);
  }
  hint.textContent=`✓ ${item.label} — ${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)}, TZ ${item.timezone>=0?'+':''}${item.timezone}`;
  if(cfg===BIRTH_PLACE_CFG) updateStartBtn();
}

function hidePlaceSuggestions(cfg=BIRTH_PLACE_CFG){
  const ul=document.getElementById(cfg.suggestionsId);
  ul.classList.add('hidden');
  ul.innerHTML='';
  placeWidgetState[cfg.suggestionsId]=-1;
}

function renderPlaceSuggestions(results,cfg=BIRTH_PLACE_CFG){
  const ul=document.getElementById(cfg.suggestionsId);
  ul.innerHTML='';
  placeWidgetState[cfg.suggestionsId]=-1;
  if(!results.length){hidePlaceSuggestions(cfg);return;}
  results.forEach((item,idx)=>{
    const li=document.createElement('li');
    li.dataset.idx=String(idx);
    li.innerHTML=`<span class="ps-label">${escHtml(item.label)}</span>
      <span class="ps-meta">${escHtml(item.country)} · ${item.latitude.toFixed(4)}, ${item.longitude.toFixed(4)} · TZ ${item.timezone>=0?'+':''}${item.timezone}</span>`;
    li.addEventListener('mousedown',e=>{e.preventDefault();selectPlace(item,cfg);});
    ul.appendChild(li);
  });
  ul.classList.remove('hidden');
}

async function searchPlacesFor(q,cfg=BIRTH_PLACE_CFG){
  if(q.length<2){hidePlaceSuggestions(cfg);return;}
  try{
    const resp=await fetch('/api/places?q='+encodeURIComponent(q));
    if(!resp.ok)return;
    const data=await resp.json();
    renderPlaceSuggestions(data.results||[],cfg);
  }catch(_){}
}

function initPlaceAutocomplete(cfg){
  const input=document.getElementById(cfg.inputId);
  if(!input) return;
  placeWidgetState[cfg.suggestionsId]=-1;
  input.addEventListener('input',()=>{
    clearPlaceSelection(cfg);
    const q=input.value.trim();
    clearTimeout(placeSearchTimer);
    placeSearchTimer=setTimeout(()=>searchPlacesFor(q,cfg),220);
    if(cfg===BIRTH_PLACE_CFG) updateStartBtn();
  });
  input.addEventListener('keydown',e=>{
    const ul=document.getElementById(cfg.suggestionsId);
    const items=[...ul.querySelectorAll('li')];
    const sid=cfg.suggestionsId;
    if(!items.length||ul.classList.contains('hidden'))return;
    let idx=placeWidgetState[sid]??-1;
    if(e.key==='ArrowDown'){e.preventDefault();idx=Math.min(idx+1,items.length-1);}
    else if(e.key==='ArrowUp'){e.preventDefault();idx=Math.max(idx-1,0);}
    else if(e.key==='Enter'&&idx>=0){e.preventDefault();items[idx].dispatchEvent(new Event('mousedown'));return;}
    else if(e.key==='Escape'){hidePlaceSuggestions(cfg);return;}
    else return;
    placeWidgetState[sid]=idx;
    items.forEach((li,i)=>li.classList.toggle('active',i===idx));
  });
  document.addEventListener('click',e=>{
    if(!document.getElementById(cfg.wrapId).contains(e.target))hidePlaceSuggestions(cfg);
  });
}

function muhuratPlaceCoords(){
  return {
    place:document.getElementById('muhurat-place').value.trim(),
    lat:document.getElementById('muhurat-place-lat').value,
    lon:document.getElementById('muhurat-place-lon').value,
    tz:document.getElementById('muhurat-place-tz').value,
  };
}

function muhuratUseBirthPlace(){
  const bp=document.getElementById('client-place').value.trim();
  const lat=document.getElementById('place-lat').value;
  const lon=document.getElementById('place-lon').value;
  const tz=document.getElementById('place-tz').value;
  if(!bp||!lat||!lon||!tz){
    const box=document.getElementById('muhurat-check-result');
    if(box) box.innerHTML='<p class="hint" style="color:var(--red)">Select birth place from the dropdown above first.</p>';
    return;
  }
  selectPlace({label:bp,latitude:parseFloat(lat),longitude:parseFloat(lon),timezone:parseFloat(tz)},MUHURAT_PLACE_CFG);
}

async function muhuratUseCurrentLocation(){
  const box=document.getElementById('muhurat-check-result');
  if(!navigator.geolocation){
    if(box) box.innerHTML='<p class="hint" style="color:var(--red)">Geolocation is not available in this browser.</p>';
    return;
  }
  if(box) box.innerHTML='<p class="hint">Detecting your location…</p>';
  navigator.geolocation.getCurrentPosition(async pos=>{
    try{
      const resp=await fetch(`/api/places/nearest?lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`);
      const data=await resp.json();
      const item=(data.results||[])[0];
      if(!item){
        if(box) box.innerHTML='<p class="hint" style="color:var(--red)">Could not match GPS to a city in our database. Type your city manually.</p>';
        return;
      }
      selectPlace(item,MUHURAT_PLACE_CFG);
      if(box) box.innerHTML=`<p class="hint" style="color:var(--green)">Event location set to nearest city: ${escHtml(item.label)}</p>`;
    }catch(e){
      if(box) box.innerHTML='<p class="hint" style="color:var(--red)">Could not resolve GPS location. Type your city manually.</p>';
    }
  },err=>{
    const msg=err.code===1?'Location permission denied. Type your city or use birth place.':'Could not read GPS. Type your city manually.';
    if(box) box.innerHTML=`<p class="hint" style="color:var(--red)">${escHtml(msg)}</p>`;
  },{enableHighAccuracy:false,timeout:12000,maximumAge:300000});
}

initPlaceAutocomplete(BIRTH_PLACE_CFG);
initPlaceAutocomplete(MUHURAT_PLACE_CFG);
initPlaceAutocomplete(GROOM_PLACE_CFG);
initPlaceAutocomplete(BRIDE_PLACE_CFG);

function btrFieldValues(){
  return {
    higher_education: document.getElementById('btr-education').value.trim(),
    foreign_travel: document.getElementById('btr-foreign').value.trim(),
    marriage: document.getElementById('btr-marriage').value.trim(),
    child: document.getElementById('btr-child').value.trim(),
    first_job: document.getElementById('btr-job').value.trim(),
    custom_events: (document.getElementById('btr-custom')||{}).value?.trim()||'',
  };
}

function appendBtrFields(fd){
  const b=btrFieldValues();
  Object.entries(b).forEach(([k,v])=>fd.append('btr_'+k,v));
}

function btrFunnelHtml(funnel,title){
  if(!funnel||!funnel.length)return '';
  const win=w=>(w==null)?'':(w<1?`~${Math.round(w*60)}s`:`~${w}m`);
  const cells=funnel.map(f=>{
    const c=`${f.varga} ${escHtml(f.lagna||'?')} (${win(f.window_min)})`;
    return f.ultra_fine?`<span style="color:#9a7ad9" title="ultra-fine tie-break">${c}</span>`:c;
  }).join(' · ');
  return `<div style="margin-top:6px;font-size:0.74rem;color:var(--muted)"><strong>${escHtml(title)}:</strong> ${cells}</div>`;
}

function applySuggestedBtrTime(timeHms){
  if(!timeHms)return;
  const disp=timeHms.slice(0,5);
  document.getElementById('client-tob').value=disp;
  appendLog('BTR: birth time set to '+disp+' (manual)','success');
}

function showBtrResult(data){
  const box=document.getElementById('btr-result');
  if(!box)return;
  if(!data||data.skipped){box.classList.add('hidden');box.innerHTML='';return;}
  const cls=data.apply?'ok':(data.trial_verdict==='approve_trial'?'ok':(data.confidence==='low'?'warn':'info'));
  let rows='';
  (data.event_results||[]).forEach(r=>{
    const clue=(r.clues&&r.clues.length)?` title="${escHtml(r.clues.join('; '))}"`:'';
    const vg=r.varga?` <span style="color:#7a7a9a">(${escHtml(r.varga)})</span>`:'';
    rows+=`<tr${clue}><td>${escHtml(r.label)}${vg}</td><td>${escHtml(r.date)}</td><td>${escHtml(r.md_lord||'-')} / ${escHtml(r.ad_lord||'-')}</td><td>${r.score}</td><td>${escHtml(r.strength)}</td></tr>`;
  });
  const off=data.offset_minutes||0;
  const offTxt=off?` (${off>0?'+':''}${off} min)`:'';
  const fine=data.fine_scan_used?' · D60 fine scan':'';
  const suggestBtn=(data.suggested_time&&data.suggested_time!==data.trial_time&&!data.apply)
    ?`<button type="button" class="btn btn-outline" style="margin-top:8px;font-size:0.78rem" onclick="applySuggestedBtrTime('${escHtml(data.suggested_time)}')">Use suggested time ${escHtml(data.suggested_time.slice(0,8))}</button>`:'';
  box.className='btr-result '+cls;
  box.classList.remove('hidden');
  box.innerHTML=`<strong>${escHtml(data.message||'')}</strong>
    <div style="margin-top:6px;font-size:0.78rem;color:var(--muted)">Trial ${escHtml(data.trial_time||'')} (score ${data.trial_score}) · Best ${escHtml(data.suggested_time||data.corrected_time||'')}${offTxt} (score ${data.suggested_score||data.best_score}) · ${escHtml(data.confidence||'')}${fine}</div>
    ${btrFunnelHtml(data.funnel_trial,'Trial funnel lagnas')}
    ${data.trial_verdict==='shift_suggested'?btrFunnelHtml(data.funnel_best,'Best-match funnel lagnas'):''}
    ${rows?`<table class="btr-table"><tr><th>Event</th><th>Date</th><th>MD/AD</th><th>Score</th><th>Fit</th></tr>${rows}</table>`:''}
    ${suggestBtn}`;
  if(data.apply&&data.corrected_time){
    const disp=data.corrected_time.slice(0,5);
    document.getElementById('client-tob').value=disp;
    const ft=document.getElementById('future-birth-time');
    if(ft)ft.value=disp;
    appendLog('BTR: birth time updated to '+disp,'success');
  }
}

function showFutureEventResult(data){
  const box=document.getElementById('future-result');
  if(!box)return;
  if(!data||!data.ok){box.classList.add('hidden');return;}
  const cls=data.promised&&data.timing_available?'ok':(data.promised?'info':'warn');
  let alt='';
  (data.alternates||[]).forEach(a=>{
    const pct=a.confluence_pct!=null?` · ${Math.round(a.confluence_pct*100)}%`:'';
    alt+=`<li>${escHtml(a.range_label)} — ${escHtml(a.md_lord)}/${escHtml(a.ad_lord)} (${a.score}, ${escHtml(a.strength||a.confluence_verdict||'')}${pct})</li>`;
  });
  const prom=data.promise||{};
  const reasons=(prom.reasons||[]).map(r=>`<li>${escHtml(r)}</li>`).join('');
  const denial=(prom.denial||[]).map(r=>`<li>${escHtml(r)}</li>`).join('');
  const win=data.next_window;
  let techTable='';
  if(win&&win.confluence&&win.confluence.techniques){
    const rows=win.confluence.techniques.map(t=>{
      const mark=t.yes?'✓':'✗';
      const note=t.note?` <span style="color:var(--muted)">${escHtml(t.note)}</span>`:'';
      return `<tr><td>${mark}</td><td>${escHtml(t.label)}</td><td>${note}</td></tr>`;
    }).join('');
    const pct=win.confluence.confluence_pct_display||Math.round((win.confluence.confluence_pct||0)*100);
    techTable=`<div style="margin-top:8px;font-size:0.74rem"><strong>Technique confluence:</strong> ${win.confluence.yes_count}/${win.confluence.total_techniques} (${pct}%)
      <table style="width:100%;margin-top:4px;border-collapse:collapse;font-size:0.72rem">
      <tr style="text-align:left"><th></th><th>Technique</th><th>Note</th></tr>${rows}</table></div>`;
  }
  let gateTable='';
  if(win&&win.confluence&&win.confluence.release_gate&&win.confluence.release_gate.checks){
    const rows=win.confluence.release_gate.checks.map(c=>{
      const mark=c.passed?'✓':'✗';
      const det=c.detail?` <span style="color:var(--muted)">${escHtml(c.detail)}</span>`:'';
      return `<tr><td>${mark}</td><td>${escHtml(c.label)}</td><td>${det}</td></tr>`;
    }).join('');
    gateTable=`<div style="margin-top:6px;font-size:0.72rem"><strong>Release gate (all required):</strong>
      <table style="width:100%;margin-top:4px;border-collapse:collapse">${rows}</table></div>`;
  }
  const partial=data.best_partial_window;
  const partialGate=partial&&partial.confluence&&partial.confluence.release_gate;
  const partialGateHtml=partialGate&&!win?`<div style="margin-top:6px;font-size:0.72rem"><strong>Why date withheld:</strong><ul style="margin:4px 0 0 16px">${
    (partial.confluence.release_gate.failed_checks||[]).map(c=>`<li>${escHtml(c.label)}${c.detail?': '+escHtml(c.detail):''}</li>`).join('')
  }</ul></div>`:'';
  const winHtml=win?`<div style="margin-top:8px"><strong>Confirmed window:</strong> ${escHtml(win.range_label)}<br/>
    <span style="font-size:0.78rem;color:var(--muted)">${escHtml(win.md_lord)} MD / ${escHtml(win.ad_lord)} AD · Vim ${win.score} · Boney ${escHtml(win.composite_tier||'')} · Kapoor ${escHtml(win.kapoor_tier||data.kapoor_confidence||'')}</span>
    ${win.chara_hits&&win.chara_hits.length?`<div style="font-size:0.74rem;margin-top:4px">Chara: ${escHtml(win.chara_hits.join('; '))}</div>`:''}
    ${win.lagna_hits&&win.lagna_hits.length?`<div style="font-size:0.74rem">Lagnas: ${escHtml(win.lagna_hits.join('; '))}</div>`:''}
    ${win.kapoor&&win.kapoor.age_activation_hits&&win.kapoor.age_activation_hits.length?`<div style="font-size:0.74rem">Age activation: ${escHtml(win.kapoor.age_activation_hits.join('; '))}</div>`:''}
    ${win.kapoor&&win.kapoor.paribhraman_hits&&win.kapoor.paribhraman_hits.length?`<div style="font-size:0.74rem">Paribhraman: ${escHtml(win.kapoor.paribhraman_hits.join('; '))}</div>`:''}
    ${win.kp&&win.kp.available&&win.kp.csl_promise?`<div style="font-size:0.74rem">KP (rules21): ${escHtml(win.kp.csl_promise.note||'')}</div>`:''}
    ${win.goel&&win.goel.yogini&&win.goel.yogini.available?`<div style="font-size:0.74rem">Yogini PL (rules8): ${escHtml(win.goel.yogini.note||'')}</div>`:''}
    ${win.goel&&win.goel.chara&&win.goel.chara.available?`<div style="font-size:0.74rem">Chara Goel (rules8): ${escHtml(win.goel.chara.note||'')}</div>`:''}
    ${win.transit_support?`<div style="font-size:0.74rem">Transit: Jupiter/Saturn support</div>`:''}
    ${techTable}
    ${gateTable}</div>`:'';
  const partialHtml=partial&&!win?`<div style="margin-top:6px;font-size:0.76rem"><strong>Best partial (gate not passed):</strong> ${escHtml(partial.range_label)} — ${partial.confluence?partial.confluence.yes_count+'/'+partial.confluence.total_techniques+' ('+partial.confluence.confluence_pct_display+'%)':''}</div>`:'';
  let remedyHtml='';
  if(data.remedies&&data.remedies.length){
    const blocks=data.remedies.map(b=>{
      const items=(b.items||[]).map(it=>`<li>${escHtml(it)}</li>`).join('');
      return `<div style="margin-top:6px"><strong>${escHtml(b.title)}</strong><ul style="margin:3px 0 0 16px">${items}</ul></div>`;
    }).join('');
    remedyHtml=`<div style="margin-top:8px;padding-top:6px;border-top:1px solid var(--border);font-size:0.76rem">
      <strong style="color:var(--gold)">🪔 Remedies (no date given — strengthen the promise first):</strong>${blocks}</div>`;
  }
  box.className='btr-result '+cls;
  box.classList.remove('hidden');
  box.innerHTML=`<strong>${escHtml(data.message||'')}</strong>
    ${winHtml}
    ${partialHtml}
    ${partialGateHtml}
    ${reasons?`<div style="margin-top:6px;font-size:0.76rem"><strong>Chart promise:</strong><ul style="margin:4px 0 0 16px">${reasons}</ul></div>`:''}
    ${denial?`<div style="margin-top:4px;font-size:0.76rem;color:var(--amber)"><strong>Denial markers:</strong><ul style="margin:4px 0 0 16px">${denial}</ul></div>`:''}
    ${alt?`<div style="margin-top:6px;font-size:0.76rem"><strong>Later confirmed windows:</strong><ul style="margin:4px 0 0 16px">${alt}</ul></div>`:''}
    ${remedyHtml}`;
}

async function runMainQuestion(){
  const q=document.getElementById('client-question').value.trim();
  if(!q){appendLog('Type your main question first.','warn');return;}
  if(!birthFormValid()){appendLog('Fill name, DOB, time, and pick place first.','warn');return;}
  const btn=document.getElementById('main-question-btn');
  const box=document.getElementById('main-question-result');
  if(btn)btn.disabled=true;
  const fd=new FormData();
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('client_dob',document.getElementById('client-dob').value.trim());
  fd.append('birth_time',document.getElementById('client-tob').value.trim());
  const rect=document.getElementById('future-birth-time');
  if(rect&&rect.value.trim())fd.append('rectified_time',rect.value.trim());
  fd.append('birth_place',document.getElementById('client-place').value.trim());
  fd.append('birth_latitude',document.getElementById('place-lat').value);
  fd.append('birth_longitude',document.getElementById('place-lon').value);
  fd.append('birth_timezone',document.getElementById('place-tz').value);
  fd.append('client_gender',document.getElementById('client-gender').value);
  fd.append('question',q);
  const rn=document.getElementById('related-name');
  const rd=document.getElementById('related-dob');
  const rt=document.getElementById('related-tob');
  const rp=document.getElementById('related-place');
  const rr=document.getElementById('related-role');
  if(rd&&rd.value.trim()&&rt&&rt.value.trim()&&rp&&rp.value.trim()){
    fd.append('related_name',rn?rn.value.trim():'Related');
    fd.append('related_dob',rd.value.trim());
    fd.append('related_birth_time',rt.value.trim());
    fd.append('related_place',rp.value.trim());
    fd.append('related_role',rr?rr.value:'child');
  }
  fd.append('save_report','1');
  try{
    const resp=await fetch('/api/main-question',{method:'POST',body:fd});
    const data=await resp.json();
    if(!resp.ok)throw new Error(data.detail||data.error||'Question analysis failed');
    if(box){
      box.classList.remove('hidden');
      box.innerHTML=data.html_inline||data.html||'';
    }
    if(data.verdict){
      const vc=data.verdict.practical_confidence||'';
      appendLog('Main question: '+data.verdict.headline+' ('+vc+')','success');
      if(data.report_path)appendLog('Saved: '+data.report_path,'info');
    }else if(data.synthesis&&data.synthesis.confirmed){
      appendLog('Main question: confirmed confluence answer.','success');
    }else{
      appendLog('Main question: partial/mixed — see technique table.','info');
    }
  }catch(e){
    appendLog('Main question error: '+e,'error');
    if(box){box.classList.add('hidden');}
  }finally{
    if(btn)btn.disabled=false;
  }
}

async function runFutureEventPredict(){
  if(!birthFormValid()){appendLog('Fill name, DOB, time, and pick place first.','warn');return;}
  const btn=document.getElementById('future-btn');
  if(btn)btn.disabled=true;
  const fd=new FormData();
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('client_dob',document.getElementById('client-dob').value.trim());
  const rect=document.getElementById('future-birth-time').value.trim();
  fd.append('birth_time',document.getElementById('client-tob').value.trim());
  fd.append('rectified_time',rect);
  fd.append('birth_place',document.getElementById('client-place').value.trim());
  fd.append('birth_latitude',document.getElementById('place-lat').value);
  fd.append('birth_longitude',document.getElementById('place-lon').value);
  fd.append('birth_timezone',document.getElementById('place-tz').value);
  fd.append('client_gender',document.getElementById('client-gender').value);
  fd.append('event_type',document.getElementById('future-event-type').value);
  try{
    const resp=await fetch('/api/future-event',{method:'POST',body:fd});
    const data=await resp.json();
    if(!resp.ok)throw new Error(data.detail||data.error||'Prediction failed');
    showFutureEventResult(data);
  }catch(e){
    appendLog('Future event error: '+e,'error');
  }finally{
    if(btn)btn.disabled=false;
  }
}

async function runBtrCheck(){
  if(!birthFormValid()){appendLog('Fill name, DOB, time, and pick place before BTR.','warn');return;}
  const btn=document.getElementById('btr-btn');
  if(btn)btn.disabled=true;
  const fd=new FormData();
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('client_dob',document.getElementById('client-dob').value.trim());
  fd.append('birth_time',document.getElementById('client-tob').value.trim());
  fd.append('birth_place',document.getElementById('client-place').value.trim());
  fd.append('birth_latitude',document.getElementById('place-lat').value);
  fd.append('birth_longitude',document.getElementById('place-lon').value);
  fd.append('birth_timezone',document.getElementById('place-tz').value);
  fd.append('client_gender',document.getElementById('client-gender').value);
  appendBtrFields(fd);
  try{
    const resp=await fetch('/api/btr',{method:'POST',body:fd});
    const data=await resp.json();
    if(!resp.ok)throw new Error(data.detail||'BTR failed');
    showBtrResult(data);
  }catch(e){
    appendLog('BTR error: '+e,'error');
  }finally{
    if(btn)btn.disabled=false;
  }
}

function birthFormValid(){
  const name=document.getElementById('client-name').value.trim();
  const dob=document.getElementById('client-dob').value.trim();
  const tob=document.getElementById('client-tob').value.trim();
  const place=document.getElementById('client-place').value.trim();
  const hasCoords=document.getElementById('place-lat').value&&document.getElementById('place-lon').value;
  return !!(name && dob && tob && place && hasCoords);
}

function updateStartBtn(){
  document.getElementById('start-btn').disabled=!birthFormValid()||running;
  updateAuxLaneBtns();
}

function numerologyFormValid(){
  const name=document.getElementById('client-name').value.trim();
  const dob=document.getElementById('client-dob').value.trim();
  return !!(name && dob);
}

function palmistryFormValid(){
  const name=document.getElementById('client-name').value.trim();
  return !!(name && imgFiles.length);
}

let palmistryRunning=false;
let numerologyRunning=false;

function setPalmistryStatus(state){
  const pill=document.getElementById('palmistry-pill');
  if(!pill) return;
  pill.className='status-pill pill-'+state;
  const labels={idle:'Idle',running:'Running…',done:'Done',error:'Error'};
  pill.innerHTML='<span class="dot'+(state==='running'?' pulse':'')+'"></span>'+(labels[state]||state);
}
function setNumerologyStatus(state){
  const pill=document.getElementById('numerology-pill');
  if(!pill) return;
  pill.className='status-pill pill-'+state;
  const labels={idle:'Idle',running:'Running…',done:'Done',error:'Error'};
  pill.innerHTML='<span class="dot'+(state==='running'?' pulse':'')+'"></span>'+(labels[state]||state);
}
function showPalmProgress(show){const w=document.getElementById('palm-progress-wrap');if(w)w.classList.toggle('hidden',!show);}
function showNumProgress(show){const w=document.getElementById('num-progress-wrap');if(w)w.classList.toggle('hidden',!show);}
function updatePalmProgress(pct){const b=document.getElementById('palm-progress-bar');if(b)b.style.width=Math.min(100,pct)+'%';}
function updateNumProgress(pct){const b=document.getElementById('num-progress-bar');if(b)b.style.width=Math.min(100,pct)+'%';}

function updatePalmistryBtn(){
  const btn=document.getElementById('palmistry-btn');
  if(btn) btn.disabled=!palmistryFormValid()||palmistryRunning;
}
function updateNumerologyBtn(){
  const btn=document.getElementById('numerology-btn');
  if(btn) btn.disabled=!numerologyFormValid()||numerologyRunning;
}
function updateAuxLaneBtns(){
  updatePalmistryBtn();
  updateNumerologyBtn();
}

function clearAll(){
  imgFiles=[];running=false;
  hideQueueBanner();
  document.getElementById('img-list').innerHTML='';
  document.getElementById('client-name').value='';
  document.getElementById('client-dob').value='';
  document.getElementById('client-tob').value='';
  document.getElementById('client-place').value='';
  clearPlaceSelection();
  hidePlaceSuggestions();
  document.getElementById('life-events').value='';
  document.getElementById('client-question').value='';
  ['btr-education','btr-foreign','btr-marriage','btr-child','btr-job'].forEach(id=>{
    document.getElementById(id).value='';
  });
  const btrCustom=document.getElementById('btr-custom');
  if(btrCustom)btrCustom.value='';
  const ft=document.getElementById('future-birth-time');
  if(ft)ft.value='';
  const fr=document.getElementById('future-result');
  if(fr){fr.classList.add('hidden');fr.innerHTML='';}
  const btrBox=document.getElementById('btr-result');
  if(btrBox){btrBox.classList.add('hidden');btrBox.innerHTML='';}
  document.getElementById('downloads-card').classList.add('hidden');
  document.getElementById('pipeline-card').classList.add('hidden');
  clearLog();
  localStorage.removeItem(LS_DONE);
  setStatus('idle');updateStartBtn();
  const pr=document.getElementById('palmistry-result');if(pr)pr.innerHTML='';
  const nr=document.getElementById('numerology-result');if(nr)nr.innerHTML='';
}

['client-name','client-dob','client-tob','client-place'].forEach(id=>{
  document.getElementById(id).addEventListener('input', updateStartBtn);
});
document.getElementById('client-gender').addEventListener('change', updateAuxLaneBtns);

// ── WebSocket ────────────────────────────────────────────────────────
function connectWS() {
  const proto=location.protocol==='https:'?'wss':'ws';
  ws=new WebSocket(`${proto}://${location.host}/ws/${SESSION_ID}`);
  ws.onmessage=e=>{
    try{
      const d=JSON.parse(e.data);
      if(d.kind==='queued'){showQueueBanner(d);return;}
      hideQueueBanner();
      if(d.msg)appendLog(d.msg,d.kind||'info');
      if(d.kind==='progress')updateProgress(d.value);
      if(d.kind==='step')markStep(d.step,d.state);
      if(d.kind==='done')onDone(d);
      if(d.kind==='cursor_human_done')onCursorHumanDone(d);
      if(d.kind==='horary_done')onHoraryDone(d);
      if(d.kind==='horary_progress')updateHProgress(d.value);
    }catch(_){appendLog(e.data,'info');}
  };
  ws.onerror=()=>appendLog('WebSocket error.','error');
  ws.onclose=()=>{ws=null;};
}
connectWS();

// ── Queue banner (shown while waiting for a free generation slot) ─────
function showQueueBanner(d){
  const b=document.getElementById('queue-banner');if(!b)return;
  const t=document.getElementById('qb-title'),s=document.getElementById('qb-sub');
  const pos=d.position||1;
  if(t)t.textContent='Waiting in queue — position #'+pos;
  if(s)s.textContent=d.msg||'Your report will start automatically.';
  b.classList.remove('hidden');
  try{setStatus('running');}catch(_){}
}
function hideQueueBanner(){
  const b=document.getElementById('queue-banner');if(b)b.classList.add('hidden');
}

// ── Restore previous session on page load ────────────────────────────
(function(){
  // Show session ID in badge
  const badge = document.getElementById('session-badge');
  if(badge) badge.textContent = 'Session: ' + SESSION_ID.slice(0,8) + '…';

  const logs = JSON.parse(localStorage.getItem(LS_LOG)||'[]');
  const hasPrior = logs.length > 0;
  if(hasPrior){
    document.getElementById('pipeline-card').classList.remove('hidden');
    restoreLogs();
  }
  restoreDoneState();
  restoreCursorChatHistory();
  const dmDate=document.getElementById('daily-moon-date');
  if(dmDate){
    const t=new Date();
    dmDate.value=`${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`;
  }
  const mhDate=document.getElementById('muhurat-check-date');
  if(mhDate){
    const t=new Date();
    mhDate.value=`${t.getFullYear()}-${String(t.getMonth()+1).padStart(2,'0')}-${String(t.getDate()).padStart(2,'0')}`;
  }
  loadMuhuratEventTypes();
  refreshProfileDropdowns();
  updateStartBtn();
  updateAuxLaneBtns();
})();

// ── log ──────────────────────────────────────────────────────────────
function appendLog(msg,kind){
  const box=document.getElementById('log-box');
  const now=new Date().toTimeString().slice(0,8);
  const cls=kind==='success'?'success':kind==='error'?'error':kind==='warn'?'warn':'';
  const div=document.createElement('div');div.className='log-entry';
  div.innerHTML=`<span class="log-ts">${now}</span><span class="log-msg ${cls}">${escHtml(msg)}</span>`;
  box.appendChild(div);box.scrollTop=box.scrollHeight;
  saveLog(msg,kind);
}
function clearLog(){
  document.getElementById('log-box').innerHTML='';
  localStorage.removeItem(LS_LOG);
}
function escHtml(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function chatPlainText(answer){
  let t=String(answer||'').trim();
  t=t.replace(/^Question:\s*.+?\n\n/i,'').replace(/^Short answer:\s*/i,'');
  return t;
}
function formatChatAnswer(text){
  let t=chatPlainText(text);
  const paras=t.split(/\n\s*\n/).map(p=>p.trim()).filter(Boolean);
  if(!paras.length) return `<div style="white-space:pre-wrap">${escHtml(t)}</div>`;
  return paras.map(p=>`<p style="margin:0 0 10px">${escHtml(p)}</p>`).join('');
}
function copyChatAnswer(btn){
  const block=btn.closest('[data-chat-block]');
  if(!block) return;
  const ta=block.querySelector('.chat-plain-copy');
  const text=ta?ta.value:'';
  const done=()=>{const o=btn.textContent;btn.textContent='Copied!';setTimeout(()=>{btn.textContent=o||'Copy answer';},1500);};
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(()=>{
      if(ta){ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);done();}
    });
  }else if(ta){
    ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();document.execCommand('copy');document.body.removeChild(ta);done();
  }
}
function appendChatBlock(q, answer, logId){
  const log=document.getElementById(logId||'cursor-chat-log');
  if(!log)return;
  const block=document.createElement('div');
  block.setAttribute('data-chat-block','1');
  block.style.cssText='margin-bottom:14px;padding:10px 12px;background:var(--surface);border-radius:8px;border:1px solid var(--border)';
  const header=document.createElement('div');
  header.style.cssText='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;gap:8px';
  header.innerHTML='<div style="color:var(--gold);font-weight:600">You asked:</div>';
  const copyBtn=document.createElement('button');
  copyBtn.type='button';
  copyBtn.className='btn btn-outline';
  copyBtn.style.cssText='font-size:.72rem;padding:4px 10px;flex-shrink:0';
  copyBtn.textContent='Copy answer';
  copyBtn.onclick=function(){copyChatAnswer(copyBtn);};
  header.appendChild(copyBtn);
  block.appendChild(header);
  const qDiv=document.createElement('div');
  qDiv.style.marginBottom='10px';
  qDiv.textContent=q;
  block.appendChild(qDiv);
  const lbl=document.createElement('div');
  lbl.style.cssText='color:var(--muted);font-weight:600;margin-bottom:6px';
  lbl.textContent='Cursor:';
  block.appendChild(lbl);
  const aDiv=document.createElement('div');
  aDiv.innerHTML=formatChatAnswer(answer);
  block.appendChild(aDiv);
  const plainTa=document.createElement('textarea');
  plainTa.className='chat-plain-copy';
  plainTa.style.display='none';
  plainTa.value=chatPlainText(answer);
  block.appendChild(plainTa);
  log.appendChild(block);
  log.scrollTop=log.scrollHeight;
}
async function restoreCursorChatHistory(){
  try{
    const resp=await fetch(`/api/cursor-chat-history?session_id=${encodeURIComponent(SESSION_ID)}`);
    if(!resp.ok) return;
    const data=await resp.json();
    const turns=data.turns||[];
    if(!turns.length) return;
    const card=document.getElementById('cursor-human-card');
    if(card)card.classList.remove('hidden');
    const sec=document.getElementById('cursor-chat-section');
    if(sec)sec.classList.remove('hidden');
    const log=document.getElementById('cursor-chat-log');
    const qlog=document.getElementById('q-cursor-chat-log');
    if(log)log.innerHTML='';
    if(qlog)qlog.innerHTML='';
    turns.forEach(t=>{
      if(t.human&&t.ai){
        appendChatBlock(t.human, t.ai, 'cursor-chat-log');
        appendChatBlock(t.human, t.ai, 'q-cursor-chat-log');
      }
    });
  }catch(_){}
}

// ── pipeline steps ───────────────────────────────────────────────────
const STEP_MAP={
  extract:'step-extract',pillar:'step-pillar',bnn:'step-bnn',kp:'step-kp',
  jaimini:'step-jaimini',vimshottari:'step-vimshottari',yogini:'step-yogini',
  ashtakavarga:'step-ashta',rtvd:'step-rtvd',longevity:'step-longevity',
  blindchart:'step-blind',confluence:'step-conf',user:'step-user'
};
function markStep(step,state){
  const el=document.getElementById(STEP_MAP[step]);
  if(!el)return;
  el.classList.remove('done','active');
  if(state==='active')el.classList.add('active');
  if(state==='done')el.classList.add('done');
}

// ── start ────────────────────────────────────────────────────────────
async function startGeneration(){
  if(!birthFormValid()||running)return;
  running=true;updateStartBtn();
  setStatus('running');showProgress(true);updateProgress(3);
  document.getElementById('pipeline-card').classList.remove('hidden');
  document.getElementById('downloads-card').classList.add('hidden');
  document.getElementById('cursor-human-card').classList.add('hidden');
  document.getElementById('cursor-human-dls').style.display='none';
  document.getElementById('cursor-chat-section').classList.add('hidden');

  const fd=new FormData();
  fd.append('session_id',SESSION_ID);
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('client_dob',document.getElementById('client-dob').value.trim());
  fd.append('birth_time',document.getElementById('client-tob').value.trim());
  fd.append('birth_place',document.getElementById('client-place').value.trim());
  fd.append('birth_latitude',document.getElementById('place-lat').value);
  fd.append('birth_longitude',document.getElementById('place-lon').value);
  fd.append('birth_timezone',document.getElementById('place-tz').value);
  fd.append('client_gender',document.getElementById('client-gender').value);
  appendBtrFields(fd);
  fd.append('life_events',document.getElementById('life-events').value.trim());
  fd.append('client_question',document.getElementById('client-question').value.trim());

  try{
    const resp=await fetch('/generate',{method:'POST',body:fd});
    if(!resp.ok){
      const err=await resp.text();
      appendLog('❌ Upload failed: '+err,'error');
      onDone(null,null,false);
    }
  }catch(e){
    appendLog('❌ Network error: '+e,'error');
    onDone(null,null,false);
  }
}

function onDone(d, restoreMode){
  running=false;updateStartBtn();
  if(!restoreMode){updateProgress(100);setTimeout(()=>showProgress(false),1200);}
  setStatus(d.success?'done':'error');
  // Persist done state so refresh can restore it
  if(d.success && !restoreMode) {
    try{localStorage.setItem(LS_DONE, JSON.stringify(d));}catch(_){}
  }
  if(d.success&&d.confluence&&d.user){
    // Client label
    if(d.client) document.getElementById('client-label').textContent=d.client;

    // Primary downloads
    document.getElementById('dl-confluence').innerHTML=
      `<a href="${d.confluence}" target="_blank"><button class="btn btn-success" style="width:100%;justify-content:center;margin-top:4px">⬇ View / Download</button></a>`;
    document.getElementById('dl-user').innerHTML=
      `<a href="${d.user}" target="_blank"><button class="btn btn-success" style="width:100%;justify-content:center;margin-top:4px">⬇ View / Download</button></a>`;

    // Individual reports grid
    const grid=document.getElementById('individual-grid');
    grid.innerHTML='';
    const icons={
      'Pillar':'🏛️','BNN':'📖','Bhardwaj':'📚','KP':'🔭','Jaimini':'⚖️','Vimshottari':'⏳',
      'Yogini':'🌙','Ashtakavarga':'📊','RTVD':'📅','Longevity':'⚕️',
      'BlindChart':'🎯','Palmistry':'🖐️','Numerology':'🔢',
      'Confluence':'✦','user':'📱'
    };
    (d.individual||[]).forEach(item=>{
      const name=item.name||'Report';
      // Friendly label: strip slug+date suffix  e.g. "Vedic_BNN_Ritz_20260408" → "BNN"
      let label=name.replace(/^Vedic_/,'').replace(/_[A-Z][a-z]+_\d{8}$/,'').replace(/_\d{8}$/,'').replace(/_/g,' ');
      const icon=Object.entries(icons).find(([k])=>name.includes(k));
      const card=document.createElement('div');card.className='ind-card';
      card.innerHTML=`
        <div class="ind-type">${icon?icon[0]:''} ${label}</div>
        <a href="${item.url}" target="_blank" rel="noopener">
          <button class="btn btn-outline" style="width:100%;justify-content:center;font-size:.78rem;padding:6px 10px">⬇ View</button>
        </a>`;
      grid.appendChild(card);
    });

    document.getElementById('downloads-card').classList.remove('hidden');
    if(!restoreMode && typeof showSection==='function') showSection('vedic');

    // Show optional Cursor human report section when CLI is available
    if(d.cursor_available){
      document.getElementById('cursor-human-card').classList.remove('hidden');
      const cbtn=document.getElementById('cursor-human-btn');
      if(cbtn) cbtn.disabled=false;
      if(d.cursor_confluence&&d.cursor_user){
        showCursorHumanDownloads(d);
      }
      restoreCursorChatHistory();
    }else{
      document.getElementById('cursor-human-card').classList.add('hidden');
    }
  }
}

let cursorHumanRunning=false;

function showCursorHumanDownloads(d){
  document.getElementById('cursor-human-dls').style.display='grid';
  document.getElementById('cursor-chat-section').classList.remove('hidden');
  document.getElementById('dl-cursor-confluence').innerHTML=
    `<a href="${d.cursor_confluence}" target="_blank"><button class="btn btn-success" style="width:100%;justify-content:center;margin-top:4px">⬇ View / Download</button></a>`;
  document.getElementById('dl-cursor-user').innerHTML=
    `<a href="${d.cursor_user}" target="_blank"><button class="btn btn-success" style="width:100%;justify-content:center;margin-top:4px">⬇ View / Download</button></a>`;
  document.getElementById('cursor-human-status').textContent='Cursor human reports ready.';
}

async function runCursorHumanReport(){
  if(cursorHumanRunning){appendLog('Cursor human report already running.','warn');return;}
  cursorHumanRunning=true;
  const btn=document.getElementById('cursor-human-btn');
  btn.disabled=true;
  document.getElementById('cursor-human-status').textContent='Starting Cursor CLI… (may take 10–20 minutes)';
  appendLog('✨ Queuing Cursor human confluence + client report…','info');
  try{
    const fd=new FormData();
    fd.append('session_id',SESSION_ID);
    const resp=await fetch('/api/cursor-human-report',{method:'POST',body:fd});
    if(!resp.ok){
      const err=await resp.text();
      appendLog('❌ Cursor human report failed: '+err,'error');
      document.getElementById('cursor-human-status').textContent='Failed — see log.';
      cursorHumanRunning=false;
      btn.disabled=false;
    }else{
      appendLog('✓ Cursor human report queued — waiting for Cursor CLI…','info');
    }
  }catch(e){
    appendLog('❌ Network error: '+e,'error');
    document.getElementById('cursor-human-status').textContent='Network error.';
    cursorHumanRunning=false;
    btn.disabled=false;
  }
}

function onCursorHumanDone(d){
  cursorHumanRunning=false;
  document.getElementById('cursor-human-btn').disabled=false;
  if(d.success){
    showCursorHumanDownloads(d);
    document.getElementById('cursor-chat-section').classList.remove('hidden');
    restoreCursorChatHistory();
    appendLog('✅ Cursor human reports ready.','success');
    try{
      const prev=JSON.parse(localStorage.getItem(LS_DONE)||'{}');
      localStorage.setItem(LS_DONE, JSON.stringify({...prev, ...d}));
    }catch(_){}
  }else{
    document.getElementById('cursor-human-status').textContent=d.error||'Cursor human report failed.';
    appendLog('❌ Cursor human report failed.','error');
  }
}

let MUHURAT_EVENTS=[];

async function loadMuhuratEventTypes(){
  const sel=document.getElementById('muhurat-event-type');
  if(!sel) return;
  try{
    const resp=await fetch('/api/muhurat-events');
    const data=await resp.json();
    MUHURAT_EVENTS=data.events||[];
    sel.innerHTML='';
    MUHURAT_EVENTS.forEach(ev=>{
      const opt=document.createElement('option');
      opt.value=ev.id;
      const suffix=ev.requires_natal_chart?' *':(ev.requires_dob?' (DOB)':'');
      opt.textContent=ev.label+suffix;
      sel.appendChild(opt);
    });
  }catch(e){
    sel.innerHTML='<option value="travel">Travel</option>';
  }
}

function muhuratEventReq(evId){
  return MUHURAT_EVENTS.find(e=>e.id===evId)||{requires_dob:false,requires_natal_chart:false,panchang_only:true};
}

function muhuratVerdictStyle(v){
  if(v==='good') return 'color:#4ade80;font-weight:700';
  if(v==='avoid') return 'color:#f87171;font-weight:700';
  return 'color:#fbbf24;font-weight:700';
}

function matchUseClientAsGroom(){
  const bp=document.getElementById('client-place').value.trim();
  const lat=document.getElementById('place-lat').value;
  const lon=document.getElementById('place-lon').value;
  const tz=document.getElementById('place-tz').value;
  document.getElementById('groom-name').value=document.getElementById('client-name').value.trim();
  document.getElementById('groom-dob').value=document.getElementById('client-dob').value.trim();
  document.getElementById('groom-tob').value=document.getElementById('client-tob').value.trim();
  if(bp&&lat&&lon&&tz){
    selectPlace({label:bp,latitude:parseFloat(lat),longitude:parseFloat(lon),timezone:parseFloat(tz)},GROOM_PLACE_CFG);
  }else{
    document.getElementById('groom-place').value=bp;
  }
  const clientNick=document.getElementById('client-profile-select').value;
  if(clientNick){
    document.getElementById('groom-profile-select').value=clientNick;
  }
}

function matchVerdictStyle(v){
  if(v==='yes') return 'color:#4ade80;font-weight:700';
  if(v==='no') return 'color:#f87171;font-weight:700';
  return 'color:#fbbf24;font-weight:700';
}

async function runPalmistryReport(){
  if(!palmistryFormValid()||palmistryRunning) return;
  palmistryRunning=true;
  updatePalmistryBtn();
  setPalmistryStatus('running');
  showPalmProgress(true);
  updatePalmProgress(15);
  const box=document.getElementById('palmistry-result');
  box.innerHTML='<p class="hint">Analysing palm images (CV + book corpus)…</p>';
  const fd=new FormData();
  fd.append('session_id',SESSION_ID);
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('active_hand',document.getElementById('palm-active-hand').value||'right');
  // Optional birth details: when present, the palmistry report adds a real
  // ephemeris birth-chart lane (PyJHora + Swiss Ephemeris) on top of the palm read.
  const _gv=id=>{const el=document.getElementById(id);return el?el.value.trim():'';};
  fd.append('client_dob',_gv('client-dob'));
  fd.append('birth_time',_gv('client-tob'));
  fd.append('birth_place',_gv('client-place'));
  fd.append('birth_latitude',_gv('place-lat'));
  fd.append('birth_longitude',_gv('place-lon'));
  fd.append('birth_timezone',_gv('place-tz'));
  imgFiles.forEach(f=>fd.append('images',f));
  try{
    updatePalmProgress(40);
    const resp=await fetch('/api/palmistry',{method:'POST',body:fd});
    const data=await resp.json();
    updatePalmProgress(100);
    if(!resp.ok||!data.success){
      setPalmistryStatus('error');
      box.innerHTML='<p class="hint" style="color:var(--red)">'+(data.error||'Palmistry generation failed.')+'</p>';
      return;
    }
    setPalmistryStatus('done');
    if(typeof showSection==='function') showSection('palmistry');
    box.innerHTML=`<div class="dl-card" style="text-align:left">
      <div class="dl-title">🖐️ Palmistry Report Ready</div>
      <div class="dl-sub">${escHtml(data.message||'')}</div>
      <a href="${data.report}" target="_blank" rel="noopener">
        <button class="btn btn-success" style="width:100%;justify-content:center;margin-top:8px">⬇ View / Download</button>
      </a></div>`;
    appendLog('🖐️ Palmistry report ready: '+data.report,'success');
  }catch(e){
    setPalmistryStatus('error');
    box.innerHTML='<p class="hint" style="color:var(--red)">Network error: '+escHtml(String(e))+'</p>';
  }finally{
    palmistryRunning=false;
    updatePalmistryBtn();
    setTimeout(()=>showPalmProgress(false),800);
  }
}

async function runNumerologyReport(){
  if(!numerologyFormValid()||numerologyRunning) return;
  numerologyRunning=true;
  updateNumerologyBtn();
  setNumerologyStatus('running');
  showNumProgress(true);
  updateNumProgress(20);
  const box=document.getElementById('numerology-result');
  box.innerHTML='<p class="hint">Computing name + DOB numerology (Mahā/Antar/Pratyantar, Lo Shu)…</p>';
  const fd=new FormData();
  fd.append('client_name',document.getElementById('client-name').value.trim());
  fd.append('client_dob',document.getElementById('client-dob').value.trim());
  fd.append('client_gender',document.getElementById('client-gender').value);
  try{
    updateNumProgress(50);
    const resp=await fetch('/api/numerology',{method:'POST',body:fd});
    const data=await resp.json();
    updateNumProgress(100);
    if(!resp.ok||!data.success){
      setNumerologyStatus('error');
      box.innerHTML='<p class="hint" style="color:var(--red)">'+(data.error||'Numerology generation failed.')+'</p>';
      return;
    }
    setNumerologyStatus('done');
    if(typeof showSection==='function') showSection('numerology');
    box.innerHTML=`<div class="dl-card" style="text-align:left">
      <div class="dl-title">🔢 Numerology Report Ready</div>
      <div class="dl-sub">${escHtml(data.message||'')}</div>
      <a href="${data.report}" target="_blank" rel="noopener">
        <button class="btn btn-success" style="width:100%;justify-content:center;margin-top:8px">⬇ View / Download</button>
      </a></div>`;
    appendLog('🔢 Numerology report ready: '+data.report,'success');
  }catch(e){
    setNumerologyStatus('error');
    box.innerHTML='<p class="hint" style="color:var(--red)">Network error: '+escHtml(String(e))+'</p>';
  }finally{
    numerologyRunning=false;
    updateNumerologyBtn();
    setTimeout(()=>showNumProgress(false),800);
  }
}

async function runKundaliMatch(){
  const btn=document.getElementById('kundali-match-btn');
  const box=document.getElementById('kundali-match-result');
  const groom={name:document.getElementById('groom-name').value.trim(),dob:document.getElementById('groom-dob').value.trim(),tob:document.getElementById('groom-tob').value.trim(),place:document.getElementById('groom-place').value.trim(),lat:document.getElementById('groom-place-lat').value,lon:document.getElementById('groom-place-lon').value,tz:document.getElementById('groom-place-tz').value};
  const bride={name:document.getElementById('bride-name').value.trim(),dob:document.getElementById('bride-dob').value.trim(),tob:document.getElementById('bride-tob').value.trim(),place:document.getElementById('bride-place').value.trim(),lat:document.getElementById('bride-place-lat').value,lon:document.getElementById('bride-place-lon').value,tz:document.getElementById('bride-place-tz').value};
  if(!groom.name||!groom.dob||!groom.tob||!groom.lat||!bride.name||!bride.dob||!bride.tob||!bride.lat){
    box.innerHTML='<p class="hint" style="color:var(--red)">Fill groom and bride name, DOB, time, and select both places from dropdown.</p>';
    return;
  }
  btn.disabled=true;
  box.innerHTML='<p class="hint">Computing Ashtakoota, doshas, and Navamsha synastry…</p>';
  try{
    const fd=new FormData();
    fd.append('match_method',document.getElementById('match-method').value);
    ['groom','bride'].forEach(role=>{
      const p=role==='groom'?groom:bride;
      fd.append(role+'_name',p.name);
      fd.append(role+'_dob',p.dob);
      fd.append(role+'_birth_time',p.tob);
      fd.append(role+'_place',p.place);
      fd.append(role+'_latitude',p.lat);
      fd.append(role+'_longitude',p.lon);
      fd.append(role+'_timezone',p.tz);
    });
    const resp=await fetch('/api/kundali-match',{method:'POST',body:fd});
    const data=await resp.json();
    if(!data.success){
      box.innerHTML=`<p class="hint" style="color:var(--red)">${escHtml(data.error||'Match failed')}</p>`;
      return;
    }
    const r=data.result;
    const v=r.verdict||{};
    const ak=r.ashtakoota||{};
    let html=`<p style="${matchVerdictStyle(v.verdict)}">${escHtml((v.verdict||'').toUpperCase())} — ${escHtml(v.headline||'')}</p>`;
    html+=`<p class="body"><strong>${escHtml(String(ak.total_guna))}</strong> / ${escHtml(String(ak.max_guna||36))} guns · ${escHtml(ak.band_plain||'')}</p>`;
    html+=`<p class="fine">Moon: groom ${escHtml(ak.groom_nakshatra)} p${escHtml(String(ak.groom_pada))} (${escHtml(ak.groom_moon_display||ak.groom_moon_sign||'')}) · bride ${escHtml(ak.bride_nakshatra)} p${escHtml(String(ak.bride_pada))} (${escHtml(ak.bride_moon_display||ak.bride_moon_sign||'')})</p>`;
    if(ak.koots&&ak.koots.length){
      html+='<table class="body" style="width:100%;margin-top:8px"><tr><th>Koot</th><th>Score</th></tr>';
      ak.koots.forEach(k=>{ html+=`<tr><td>${escHtml(k.label)}</td><td>${escHtml(String(k.score))}/${escHtml(String(k.max))}</td></tr>`; });
      html+='</table>';
    }
    const doshas=(r.doshas&&r.doshas.items)||[];
    if(doshas.length){
      html+='<p class="body" style="margin-top:10px"><strong>Doshas:</strong></p><ul class="fine">';
      doshas.forEach(d=>{ html+=`<li>${escHtml(d.name)}: ${d.waived?'waived':(d.active?'active':'clear')} — ${escHtml(d.detail)}</li>`; });
      html+='</ul>';
    }
    const goel=r.goel_synastry||{};
    html+=`<p class="fine" style="margin-top:8px">Goel D9 synastry: ${escHtml(String(goel.passed))}/${escHtml(String(goel.total))} passed</p>`;
    const d9c=r.d9_compatibility||{};
    if(d9c.available){
      const d9Cls=d9c.verdict==='strong'?'color:#4ade80':(d9c.verdict==='weak'?'color:#f87171':'color:#fbbf24');
      html+=`<p class="body" style="margin-top:10px"><strong>Navamsha (D9) compatibility:</strong> <span style="${d9Cls}">${escHtml((d9c.verdict||'').toUpperCase())}</span> — ${escHtml(d9c.headline||'')}</p>`;
      html+=`<p class="fine">D9 lagna: groom ${escHtml(d9c.groom_d9_lagna||'')} (${escHtml(d9c.groom_d9_lagna_lord||'')}) · bride ${escHtml(d9c.bride_d9_lagna||'')} (${escHtml(d9c.bride_d9_lagna_lord||'')}) · ${escHtml(String(d9c.passed))}/${escHtml(String(d9c.total))} checks (${escHtml(String(d9c.score_pct))}%)</p>`;
      if(d9c.checks&&d9c.checks.length){
        html+='<ul class="fine">';
        d9c.checks.forEach(c=>{ html+=`<li>${c.ok?'OK':'MISS'} — ${escHtml(c.name)}: ${escHtml(c.detail)}</li>`; });
        html+='</ul>';
      }
    }
    const num=r.numerology||{};
    if(num.available){
      const lp=num.life_path_compat||{};
      const su=num.soul_urge_compat||{};
      const rel=num.relationship_number||{};
      const nv=num.verdict||{};
      html+=`<p class="body" style="margin-top:10px"><strong>Numerology:</strong> ${escHtml(nv.headline||'')}</p>`;
      html+=`<p class="fine">Life Path ${escHtml(String(lp.groom_lp))} x ${escHtml(String(lp.bride_lp))}: <strong>${escHtml(lp.label||'')}</strong> · Soul Urge ${escHtml(String(su.groom_su))} x ${escHtml(String(su.bride_su))}: <strong>${escHtml(su.label||'')}</strong></p>`;
      html+=`<p class="fine">Relationship number <strong>${escHtml(String(rel.number))}</strong> — ${escHtml(rel.text||'')}</p>`;
      const tips=(num.partner_tips&&num.partner_tips.tips)||[];
      if(tips.length){
        html+='<ul class="fine">';
        tips.forEach(t=>{ html+=`<li>${escHtml(t)}</li>`; });
        html+='</ul>';
      }
    }
    const adv=(num.advanced)||{};
    if(adv.available){
      const dec=adv.decision||{};
      const enm=adv.psychic_enmity||{};
      const g=adv.groom||{}, b=adv.bride||{};
      const advCls=dec.verdict==='recommend'?'color:#4ade80':(dec.verdict==='reject'?'color:#f87171':'color:#fbbf24');
      html+=`<p class="body" style="margin-top:10px"><strong>Advanced numerology:</strong> <span style="${advCls}">${escHtml((dec.verdict||'').toUpperCase())}</span> - ${escHtml(dec.headline||'')}</p>`;
      html+=`<p class="fine">Psychic ${escHtml(String(g.psychic))} x ${escHtml(String(b.psychic))} - enmity: ${enm.anemical?'yes':'no'} | Destiny ${escHtml(String(g.destiny))} (${escHtml(g.destiny_band)}) x ${escHtml(String(b.destiny))} (${escHtml(b.destiny_band)})</p>`;
      const rem=adv.remedies||[];
      if(rem.length){
        html+='<p class="fine"><strong>Num. remedies:</strong></p><ul class="fine">';
        rem.slice(0,4).forEach(r=>{
          html+=`<li>${escHtml(r.for)}: ${escHtml((r.steps||[])[0]||'')}</li>`;
        });
        html+='</ul>';
      }
    }
    if(r.remissions&&r.remissions.length){
      html+='<p class="body" style="margin-top:10px"><strong>Remissions (Bhardwaj):</strong></p><ul class="fine">';
      r.remissions.forEach(x=>{ html+=`<li>${escHtml(x.dosha)}: ${x.remission_applies?'yes':'no'} - ${escHtml(x.detail)}</li>`; });
      html+='</ul>';
    }
    if(r.remedies&&r.remedies.length){
      html+='<p class="body" style="margin-top:10px"><strong>Remedies:</strong></p><ul class="fine">';
      r.remedies.forEach(b=>{
        html+=`<li><strong>${escHtml(b.for)}</strong><ul>`;
        (b.steps||[]).forEach(s=>{ html+=`<li>${escHtml(s)}</li>`; });
        html+='</ul></li>';
      });
      html+='</ul>';
    }
    if(data.report_url){
      html+=`<p style="margin-top:10px"><a href="${escHtml(data.report_url)}" target="_blank" style="color:var(--gold)">Open full HTML report</a></p>`;
    }
    box.innerHTML=html;
    appendLog('Kundali match: '+v.verdict+' ('+ak.total_guna+' guns)',v.verdict==='yes'?'success':'warn');
  }catch(e){
    box.innerHTML='<p class="hint" style="color:var(--red)">Network error.</p>';
  }finally{
    btn.disabled=false;
  }
}

async function runMuhuratCheck(){
  const btn=document.getElementById('muhurat-check-btn');
  const box=document.getElementById('muhurat-check-result');
  const evId=document.getElementById('muhurat-event-type').value;
  const req=muhuratEventReq(evId);
  const dob=document.getElementById('client-dob').value.trim();
  const tob=document.getElementById('client-tob').value.trim();
  const mp=muhuratPlaceCoords();
  const hasEventCoords=mp.lat&&mp.lon&&mp.tz;
  if(!hasEventCoords){
    box.innerHTML='<p class="hint" style="color:var(--red)">Select <strong>event location</strong> for panchang (type city or use a button above).</p>';
    return;
  }
  const birthCoords=document.getElementById('place-lat').value&&document.getElementById('place-lon').value&&document.getElementById('place-tz').value;
  if(req.requires_natal_chart&&!birthCoords){
    box.innerHTML='<p class="hint" style="color:var(--red)">This event needs your birth place + DOB + birth time for the natal chart (marked *).</p>';
    return;
  }
  if(req.requires_natal_chart&&(!dob||!tob)){
    box.innerHTML='<p class="hint" style="color:var(--red)">This event needs your date of birth and birth time (marked * in the list).</p>';
    return;
  }
  if(req.requires_dob&&!dob){
    box.innerHTML='<p class="hint" style="color:var(--red)">This event needs date of birth (marked DOB in the list).</p>';
    return;
  }
  btn.disabled=true;
  box.innerHTML='<p class="hint">Checking panchang'+(dob?' and your chart':'')+'…</p>';
  try{
    const fd=new FormData();
    fd.append('session_id',SESSION_ID);
    fd.append('event_type',document.getElementById('muhurat-event-type').value);
    fd.append('target_date',document.getElementById('muhurat-check-date').value||'');
    fd.append('client_name',document.getElementById('client-name').value.trim());
    fd.append('client_dob',dob);
    fd.append('birth_time',document.getElementById('client-tob').value.trim());
    fd.append('birth_place',document.getElementById('client-place').value.trim());
    fd.append('birth_latitude',document.getElementById('place-lat').value);
    fd.append('birth_longitude',document.getElementById('place-lon').value);
    fd.append('birth_timezone',document.getElementById('place-tz').value);
    fd.append('panchang_place',mp.place);
    fd.append('panchang_latitude',mp.lat);
    fd.append('panchang_longitude',mp.lon);
    fd.append('panchang_timezone',mp.tz);
    fd.append('client_gender',document.getElementById('client-gender').value);
    const resp=await fetch('/api/muhurat-check',{method:'POST',body:fd});
    const data=await resp.json();
    if(!data.success){
      box.innerHTML=`<p class="hint" style="color:var(--red)">${escHtml(data.error||'Check failed')}</p>`;
      return;
    }
    const r=data.result;
    let html=`<p style="${muhuratVerdictStyle(r.verdict)}">${escHtml(r.verdict.toUpperCase())} — ${escHtml(r.headline)}</p>`;
    html+=`<p class="body">${escHtml(r.summary)}</p>`;
    html+=`<p class="fine">${escHtml(r.event_label)} on <strong>${escHtml(r.target_date)}</strong> at <strong>${escHtml(r.panchang_location||'')}</strong> · ${escHtml(r.panchang.weekday)} · tithi ${escHtml(String(r.panchang.tithi_day))} ${escHtml(r.panchang.paksha)} · ${escHtml(r.panchang.nakshatra)}</p>`;
    if(r.day_windows&&r.day_windows.day_summary){
      html+=`<p class="fine"><strong>Best hours that day:</strong> ${escHtml(r.day_windows.day_summary)}</p>`;
    }
    const tri=(r.day_windows&&r.day_windows.tri_kaal)||[];
    if(tri.length){
      html+='<p class="fine" style="margin-top:8px"><strong>Avoid (tri-kaal):</strong></p><ul class="fine">';
      tri.forEach(s=>{ html+=`<li><strong>${escHtml(s.label)}</strong> ${escHtml(s.start)}-${escHtml(s.end)}</li>`; });
      html+='</ul>';
    }
    const avoidCh=(r.day_windows&&r.day_windows.avoid_choghadiya)||[];
    if(avoidCh.length){
      html+='<p class="fine"><strong>Avoid choghadiya:</strong></p><ul class="fine">';
      avoidCh.forEach(s=>{ html+=`<li>${escHtml(s.label)} ${escHtml(s.start)}-${escHtml(s.end)}</li>`; });
      html+='</ul>';
    }
    if(r.checks&&r.checks.length){
      html+='<ul class="body" style="margin-top:8px">';
      r.checks.forEach(c=>{
        const mark=c.ok?'✓':'✗';
        const col=c.ok?'#4ade80':'#f87171';
        html+=`<li><span style="color:${col}">${mark}</span> <strong>${escHtml(c.name)}:</strong> ${escHtml(c.detail)}</li>`;
      });
      html+='</ul>';
    }
    if(r.chart_notes&&r.chart_notes.length){
      html+='<p class="fine" style="margin-top:8px"><strong>Chart-specific (your birth data):</strong></p><ul class="fine">';
      r.chart_notes.forEach(n=>{ html+=`<li>${escHtml(n)}</li>`; });
      html+='</ul>';
    }
    if(r.alternatives&&r.alternatives.length){
      html+='<p class="body" style="margin-top:12px"><strong>Suggested next dates:</strong></p><table class="body" style="width:100%;border-collapse:collapse;margin-top:6px">';
      html+='<tr><th style="text-align:left;padding:4px 8px;border-bottom:1px solid #444">Date</th><th style="text-align:left;padding:4px 8px;border-bottom:1px solid #444">Day</th><th style="text-align:left;padding:4px 8px;border-bottom:1px solid #444">Verdict</th><th style="text-align:left;padding:4px 8px;border-bottom:1px solid #444">Nakshatra</th></tr>';
      r.alternatives.forEach(a=>{
        html+=`<tr><td style="padding:4px 8px;border-bottom:1px solid #333">${escHtml(a.date)}</td><td style="padding:4px 8px;border-bottom:1px solid #333">${escHtml(a.weekday)}</td><td style="padding:4px 8px;border-bottom:1px solid #333">${escHtml(a.verdict)}</td><td style="padding:4px 8px;border-bottom:1px solid #333">${escHtml(a.nakshatra)}</td></tr>`;
      });
      html+='</table>';
    }
    box.innerHTML=html;
    appendLog('Muhurat '+r.event_label+': '+r.verdict+' on '+r.target_date, r.verdict==='good'?'success':'warn');
  }catch(e){
    box.innerHTML='<p class="hint" style="color:var(--red)">Network error.</p>';
    appendLog('Muhurat check error: '+e,'error');
  }finally{
    btn.disabled=false;
  }
}

async function fetchDailyMoon(){
  const dateEl=document.getElementById('daily-moon-date');
  const btn=document.getElementById('daily-moon-btn');
  const res=document.getElementById('daily-moon-result');
  const dl=document.getElementById('daily-moon-dl');
  btn.disabled=true;
  res.textContent='Computing personalised Moon guide…';
  dl.innerHTML='';
  try{
    const fd=new FormData();
    fd.append('session_id',SESSION_ID);
    fd.append('target_date',dateEl.value||'');
    fd.append('birth_latitude',document.getElementById('place-lat').value);
    fd.append('birth_longitude',document.getElementById('place-lon').value);
    fd.append('birth_timezone',document.getElementById('place-tz').value);
    const resp=await fetch('/api/daily-moon',{method:'POST',body:fd});
    const data=await resp.json();
    if(data.success){
      res.innerHTML=`<span style="color:var(--gold);font-weight:600">${escHtml(data.tone||'').replace(/-/g,' ')}</span> — ${escHtml((data.opening||'').slice(0,220))}…`;
      dl.innerHTML=`<a href="${data.url}" target="_blank"><button class="btn btn-success" style="margin-top:6px">⬇ Open full Daily Prediction HTML</button></a>`;
      appendLog('📅 Daily Prediction ready.','success');
    }else{
      res.textContent=data.error||'Daily guide failed.';
      appendLog('❌ Daily Moon: '+(data.error||'failed'),'error');
    }
  }catch(e){
    res.textContent='Network error.';
    appendLog('❌ Daily Moon error: '+e,'error');
  }finally{
    btn.disabled=false;
  }
}

function chatNote(logId, msg, kind){
  const log=document.getElementById(logId);
  if(!log)return;
  const c=kind==='error'?'var(--red)':(kind==='warn'?'var(--amber)':'var(--muted)');
  const div=document.createElement('div');
  div.style.cssText='margin:6px 0;font-size:.82rem;color:'+c;
  div.textContent=msg;
  log.appendChild(div);
  log.scrollTop=log.scrollHeight;
}
async function sendCursorChat(inputId, btnId, logId){
  inputId=inputId||'cursor-chat-input'; btnId=btnId||'cursor-chat-btn'; logId=logId||'cursor-chat-log';
  const inEl=document.getElementById(inputId);
  const q=inEl?inEl.value.trim():'';
  if(!q){chatNote(logId,'Enter a follow-up question first.','warn');appendLog('Enter a follow-up question first.','warn');return;}
  const btn=document.getElementById(btnId);
  if(btn)btn.disabled=true;
  appendLog('💬 Sending follow-up to Cursor…','info');
  chatNote(logId,'Sending follow-up to Cursor… (this can take a minute)','info');
  try{
    const fd=new FormData();
    fd.append('session_id',SESSION_ID);
    fd.append('question',q);
    const resp=await fetch('/api/cursor-chat',{method:'POST',body:fd});
    let data={};
    try{ data=await resp.json(); }catch(_){ data={}; }
    if(resp.ok&&data.success&&data.answer){
      const sec=document.getElementById('cursor-chat-section');
      if(sec)sec.classList.remove('hidden');
      // Mirror the turn into both chat logs so the conversation stays in sync.
      ['cursor-chat-log','q-cursor-chat-log'].forEach(id=>{ if(document.getElementById(id)) appendChatBlock(q, data.answer, id); });
      if(inEl)inEl.value='';
      appendLog('✓ Follow-up answer received.','success');
    }else{
      let msg=data.error||data.detail||'No answer from Cursor';
      if(resp.status===404)msg='Generate the Vedic reports first (Vedic Reports → Generate) — the follow-up chat needs that chart context.';
      else if(resp.status===503)msg='Cursor CLI (cursor-agent) is not available on this machine.';
      chatNote(logId,'⚠ '+msg,'error');
      appendLog('❌ '+msg,'error');
    }
  }catch(e){
    chatNote(logId,'⚠ Chat error: '+e,'error');
    appendLog('❌ Chat error: '+e,'error');
  }finally{
    if(btn)btn.disabled=false;
  }
}

// ── Horary section ───────────────────────────────────────────────────
(function(){
  // Default date/time to now
  const now=new Date();
  const pad=n=>String(n).padStart(2,'0');
  document.getElementById('h-date').value=
    `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}`;
  document.getElementById('h-time').value=`${pad(now.getHours())}:${pad(now.getMinutes())}`;
  document.getElementById('h-location').value='New Delhi, India';
})();

let horaryRunning=false;

function submitHorary(){
  const q=document.getElementById('h-question').value.trim();
  const d=document.getElementById('h-date').value.trim();
  const t=document.getElementById('h-time').value.trim();
  if(!q){appendLog('[Horary] Please enter a question.','warn');return;}
  if(!d||!t){appendLog('[Horary] Please enter date and time.','warn');return;}
  if(horaryRunning)return;
  horaryRunning=true;
  document.getElementById('horary-btn').disabled=true;
  document.getElementById('horary-result-card').classList.add('hidden');
  setHoraryStatus('running');
  showHProgress(true);updateHProgress(5);

  const fd=new FormData();
  fd.append('session_id',SESSION_ID);
  fd.append('question',q);
  fd.append('q_date',d);
  fd.append('q_time',t);
  fd.append('location',document.getElementById('h-location').value.trim()||'New Delhi, India');
  fd.append('kp_number',document.getElementById('h-kp').value.trim());

  fetch('/horary',{method:'POST',body:fd})
    .then(r=>{if(!r.ok)r.text().then(e=>appendLog('[Horary] Error: '+e,'error'));})
    .catch(e=>appendLog('[Horary] Network error: '+e,'error'));
}

function applyHoraryVerdictBadge(el,verdict){
  const raw=(verdict||'').trim();
  const v=raw.toUpperCase();
  el.textContent=raw||'—';
  const vmap={YES:'verdict-yes',LIKELY:'verdict-likely',UNCERTAIN:'verdict-uncertain',
              UNLIKELY:'verdict-unlikely',NO:'verdict-no'};
  el.className='';
  const fs=v.length>14?'0.82rem':'1.15rem';
  Object.assign(el.style,{fontSize:fs,fontWeight:'800',padding:'8px 18px',
    borderRadius:'10px',border:'2px solid',marginBottom:'8px',maxWidth:'100%',width:'fit-content',
    background:'rgba(212,175,55,.08)',color:'var(--gold)',borderColor:'var(--gold)'});
  if(vmap[v]) el.classList.add(vmap[v]);
  else if(v.includes('MIXED')||v.includes('VERIFY')) el.classList.add('verdict-uncertain');
}

function onHoraryDone(d){
  horaryRunning=false;
  document.getElementById('horary-btn').disabled=false;
  updateHProgress(100);setTimeout(()=>showHProgress(false),1200);

  const vedicOk=!!(d.report&&(d.vedic_success!==false));
  const westernOk=!!(d.western_report&&(d.western_success!==false));
  const anyOk=d.success||vedicOk||westernOk;
  setHoraryStatus(anyOk?'done':'error');

  if(!anyOk)return;

  const card=document.getElementById('horary-result-card');
  card.classList.remove('hidden');
  if(typeof showSection==='function') showSection('horary');
  document.getElementById('h-question-display').textContent=d.question?('"'+d.question+'"'):'';

  if(vedicOk){
    applyHoraryVerdictBadge(document.getElementById('h-vedic-verdict-badge'),d.verdict);
    document.getElementById('h-vedic-confidence').textContent=
      d.confidence?'Confidence: '+d.confidence:'';
    document.getElementById('h-vedic-dl').innerHTML=
      `<a href="${d.report}" target="_blank" rel="noopener">
         <button class="btn btn-success" style="margin-top:4px">⬇ Vedic horary report</button>
       </a>`;
  }else{
    document.getElementById('h-vedic-verdict-badge').textContent='—';
    document.getElementById('h-vedic-verdict-badge').className='horary-na';
    document.getElementById('h-vedic-confidence').textContent='';
    document.getElementById('h-vedic-dl').innerHTML='<span class="horary-na">Not available for this run.</span>';
  }

  if(westernOk){
    applyHoraryVerdictBadge(document.getElementById('h-western-verdict-badge'),d.western_verdict);
    document.getElementById('h-western-confidence').textContent=
      d.western_confidence?'Confidence: '+d.western_confidence:'';
    document.getElementById('h-western-dl').innerHTML=
      `<a href="${d.western_report}" target="_blank" rel="noopener">
         <button class="btn btn-outline" style="margin-top:4px;border-color:#58a6ff;color:#58a6ff">⬇ Western horary report</button>
       </a>`;
  }else{
    document.getElementById('h-western-verdict-badge').textContent='—';
    document.getElementById('h-western-verdict-badge').className='horary-na';
    document.getElementById('h-western-confidence').textContent='';
    document.getElementById('h-western-dl').innerHTML='<span class="horary-na">Not available for this run.</span>';
  }
}

function setHoraryStatus(s){
  const pill=document.getElementById('horary-pill');
  const map={idle:['pill-idle','Idle'],running:['pill-running','Analyzing…'],
    done:['pill-done','Done ✓'],error:['pill-error','Error']};
  const [cls,label]=map[s]||map.idle;
  pill.className=`status-pill ${cls}`;
  const pulse=s==='running'?' pulse':'';
  pill.innerHTML=`<span class="dot${pulse}"></span>${label}`;
}
function showHProgress(show){document.getElementById('h-progress-wrap').classList.toggle('hidden',!show);}
function updateHProgress(pct){document.getElementById('h-progress-bar').style.width=Math.min(100,pct)+'%';}

// ── UI helpers ────────────────────────────────────────────────────────
function setStatus(s){
  const pill=document.getElementById('status-pill');
  const map={idle:['pill-idle','Idle'],running:['pill-running','Generating…'],
    done:['pill-done','Done ✓'],error:['pill-error','Error']};
  const [cls,label]=map[s]||map.idle;
  pill.className=`status-pill ${cls}`;
  const pulse=s==='running'?' pulse':'';
  pill.innerHTML=`<span class="dot${pulse}"></span>${label}`;
}
function showProgress(show){document.getElementById('progress-wrap').classList.toggle('hidden',!show);}
function updateProgress(pct){document.getElementById('progress-bar').style.width=Math.min(100,pct)+'%';}
</script>
</body>
</html>
"""

# ──────────────────────────── login page ─────────────────────────────
LOGIN_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Sign in · Vedic Astrology</title>
<style>
  :root{--bg:#0a0a1a;--surface:#12122a;--border:#2a2a5a;--gold:#d4af37;--gold2:#e8c96a;
        --text:#e8e0d0;--muted:#7a7a9a;--red:#ef4444;--radius:14px}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:radial-gradient(1200px 600px at 50% -10%,#1a1a3a,var(--bg));color:var(--text);
       font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;align-items:center;
       justify-content:center;padding:20px}
  .card{width:100%;max-width:380px;background:var(--surface);border:1px solid var(--border);
        border-radius:var(--radius);padding:34px 28px;box-shadow:0 20px 60px rgba(0,0,0,.5)}
  .brand{text-align:center;margin-bottom:22px}
  .brand .mark{font-size:2.2rem;color:var(--gold)}
  .brand h1{font-size:1.25rem;font-weight:600;margin-top:6px;
            background:linear-gradient(90deg,var(--gold),var(--gold2));-webkit-background-clip:text;
            background-clip:text;-webkit-text-fill-color:transparent}
  .brand p{color:var(--muted);font-size:.85rem;margin-top:4px}
  label{display:block;font-size:.8rem;color:var(--muted);margin:14px 0 6px}
  input{width:100%;padding:12px 14px;border-radius:10px;border:1px solid var(--border);
        background:#0d0d22;color:var(--text);font-size:1rem;outline:none}
  input:focus{border-color:var(--gold)}
  button{width:100%;margin-top:22px;padding:13px;border:none;border-radius:10px;cursor:pointer;
         font-size:1rem;font-weight:600;color:#0a0a1a;
         background:linear-gradient(90deg,var(--gold),var(--gold2))}
  button:disabled{opacity:.6;cursor:default}
  .err{display:none;margin-top:14px;color:var(--red);font-size:.85rem;text-align:center}
  .hint{margin-top:18px;text-align:center;color:var(--muted);font-size:.75rem}
</style>
</head>
<body>
  <form class="card" id="login-form" autocomplete="on">
    <div class="brand">
      <div class="mark">✦</div>
      <h1>Vedic Astrology Reports</h1>
      <p>Please sign in to continue</p>
    </div>
    <label for="u">Username</label>
    <input id="u" name="username" type="text" autocomplete="username" required autofocus/>
    <label for="p">Password</label>
    <input id="p" name="password" type="password" autocomplete="current-password" required/>
    <button type="submit" id="btn">Sign in</button>
    <div class="err" id="err">Invalid username or password</div>
    <div class="hint">Secure local access</div>
  </form>
<script>
  var f=document.getElementById('login-form'),btn=document.getElementById('btn'),err=document.getElementById('err');
  f.addEventListener('submit',function(e){
    e.preventDefault();err.style.display='none';btn.disabled=true;btn.textContent='Signing in…';
    fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},
      credentials:'same-origin',
      body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})})
    .then(function(r){return r.json().then(function(j){return {ok:r.ok,j:j};});})
    .then(function(res){
      if(res.ok&&res.j.status==='ok'){window.location.href='/';}
      else{err.style.display='block';btn.disabled=false;btn.textContent='Sign in';}
    })
    .catch(function(){err.style.display='block';btn.disabled=false;btn.textContent='Sign in';});
  });
</script>
</body>
</html>"""

_LOGOUT_SNIPPET = r"""
<style>
#astro-logout{position:fixed;bottom:16px;right:16px;z-index:100000;background:rgba(18,18,42,.92);
  color:#d4af37;border:1px solid #2a2a5a;border-radius:10px;padding:8px 14px;cursor:pointer;
  font:600 .82rem 'Segoe UI',system-ui,sans-serif;box-shadow:0 4px 16px rgba(0,0,0,.4)}
#astro-logout:hover{border-color:#d4af37}
@media print{#astro-logout{display:none}}
</style>
<button id="astro-logout" onclick="(function(){fetch('/api/logout',{method:'POST',credentials:'same-origin'}).then(function(){window.location.href='/';});})()">Sign out</button>
</body>"""


# ──────────────────────────── routes ──────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    if not _request_authed(request):
        return HTMLResponse(LOGIN_PAGE)
    return HTMLResponse(HTML_PAGE.replace("</body>", _LOGOUT_SNIPPET, 1))


@app.get("/health")
async def health():
    urls = get_server_urls(int(os.getenv("ASTRO_PORT", "8091")))
    return JSONResponse({
        "status": "ok",
        "service": "vedic-astro",
        "auth_required": True,
        "public_url": urls.get("public"),
        "recommended_url": urls["recommended"],
        "urls": {
            "local": urls["local"],
            "lan": urls["lan"],
            "public": urls.get("public"),
        },
        "universal": urls["universal"],
    })


@app.post("/api/login")
async def api_login(request: Request):
    username = password = ""
    ctype = request.headers.get("content-type", "")
    try:
        if "application/json" in ctype:
            data = await request.json()
            username = str(data.get("username", "")).strip()
            password = str(data.get("password", ""))
        else:
            form = await request.form()
            username = str(form.get("username", "")).strip()
            password = str(form.get("password", ""))
    except Exception:
        return JSONResponse({"status": "error", "detail": "Bad request"}, status_code=400)

    user_ok = _hmac.compare_digest(username, AUTH_USER)
    pass_ok = _hmac.compare_digest(password, AUTH_PASS)
    if user_ok and pass_ok:
        resp = JSONResponse({"status": "ok", "token": _VALID_TOKEN})
        resp.set_cookie(
            AUTH_COOKIE, _VALID_TOKEN, httponly=True, samesite="lax",
            max_age=60 * 60 * 24 * 30, path="/",
        )
        return resp
    return JSONResponse({"status": "error", "detail": "Invalid username or password"}, status_code=401)


@app.post("/api/logout")
async def api_logout():
    resp = JSONResponse({"status": "ok"})
    resp.delete_cookie(AUTH_COOKIE, path="/")
    return resp


@app.websocket("/ws/{session_id}")
async def ws_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = get_session(session_id)
    session.ws_connections.append(websocket)
    for entry in session.events:
        try:
            await websocket.send_text(entry)
        except Exception:
            break
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        try:
            session.ws_connections.remove(websocket)
        except Exception:
            pass


@app.get("/api/places")
async def api_places(q: str = ""):
    from birth_place_resolve import search_places
    return JSONResponse({"results": search_places(q, limit=12)})


@app.get("/api/places/nearest")
async def api_places_nearest(lat: float = 0.0, lon: float = 0.0):
    from birth_place_resolve import nearest_places
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise HTTPException(400, "Invalid latitude/longitude.")
    return JSONResponse({"results": nearest_places(lat, lon, limit=5)})


@app.post("/api/btr")
async def api_btr(
    client_name: str = Form(""),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    client_gender: str = Form("Male"),
    btr_higher_education: str = Form(""),
    btr_foreign_travel: str = Form(""),
    btr_marriage: str = Form(""),
    btr_child: str = Form(""),
    btr_first_job: str = Form(""),
    btr_custom_events: str = Form(""),
):
    from birth_place_resolve import normalize_birth_time, normalize_dob
    from btr_rectify import rectify_birth_time

    if not client_dob.strip() or not birth_time.strip():
        raise HTTPException(400, "DOB and birth time required for BTR.")
    if not birth_latitude.strip() or not birth_longitude.strip() or not birth_timezone.strip():
        raise HTTPException(400, "Select a place from the dropdown first.")

    try:
        dob = normalize_dob(client_dob)
        birth_time_norm = normalize_birth_time(birth_time)
    except ValueError as ve:
        raise HTTPException(400, str(ve))

    gender_int = 1 if client_gender.lower().startswith("f") else 0
    loop = asyncio.get_running_loop()

    def do_btr():
        return rectify_birth_time(
            client_name=client_name.strip() or "Client",
            dob=dob,
            birth_time=birth_time_norm,
            latitude=float(birth_latitude),
            longitude=float(birth_longitude),
            timezone=float(birth_timezone),
            place_name=birth_place.strip(),
            gender=gender_int,
            event_fields={
                "higher_education": btr_higher_education,
                "foreign_travel": btr_foreign_travel,
                "marriage": btr_marriage,
                "child": btr_child,
                "first_job": btr_first_job,
            },
            custom_events=btr_custom_events,
        )

    return JSONResponse(await loop.run_in_executor(None, do_btr))


@app.post("/api/main-question")
async def api_main_question(
    client_name: str = Form(""),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    rectified_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    client_gender: str = Form("Male"),
    question: str = Form(""),
    related_name: str = Form(""),
    related_dob: str = Form(""),
    related_birth_time: str = Form(""),
    related_place: str = Form(""),
    related_latitude: str = Form(""),
    related_longitude: str = Form(""),
    related_timezone: str = Form(""),
    related_role: str = Form("child"),
    save_report: str = Form(""),
):
    from birth_place_resolve import normalize_birth_time, normalize_dob, resolve_birth_place
    from main_question_report import SubjectInput, build_main_question_report, save_main_question_report

    if not question.strip():
        raise HTTPException(400, "Enter your main question.")
    if not client_dob.strip() or not birth_time.strip():
        raise HTTPException(400, "DOB and birth time required.")
    if not birth_latitude.strip() or not birth_longitude.strip() or not birth_timezone.strip():
        raise HTTPException(400, "Select a place from the dropdown first.")

    try:
        dob = normalize_dob(client_dob)
        birth_time_norm = normalize_birth_time(birth_time)
        rect_norm = normalize_birth_time(rectified_time) if rectified_time.strip() else ""
    except ValueError as ve:
        raise HTTPException(400, str(ve))

    use_time = rect_norm or birth_time_norm
    gender_int = 1 if client_gender.lower().startswith("f") else 0
    loop = asyncio.get_running_loop()

    def do_answer():
        subject = SubjectInput(
            name=client_name.strip() or "Client",
            dob=dob,
            birth_time=use_time,
            latitude=float(birth_latitude),
            longitude=float(birth_longitude),
            timezone=float(birth_timezone),
            place_name=birth_place.strip(),
            gender=gender_int,
            role="client",
        )
        related = None
        if related_dob.strip() and related_birth_time.strip() and related_place.strip():
            try:
                rdob = normalize_dob(related_dob)
                rtob = normalize_birth_time(related_birth_time)
                if related_latitude.strip() and related_longitude.strip() and related_timezone.strip():
                    rplace = resolve_birth_place(
                        related_place.strip(),
                        latitude=float(related_latitude),
                        longitude=float(related_longitude),
                        timezone=float(related_timezone),
                    )
                else:
                    rplace = resolve_birth_place(related_place.strip())
                related = SubjectInput(
                    name=related_name.strip() or "Related",
                    dob=rdob,
                    birth_time=rtob,
                    latitude=rplace["latitude"],
                    longitude=rplace["longitude"],
                    timezone=rplace["timezone"],
                    place_name=rplace["place"],
                    gender=0,
                    role=(related_role.strip() or "child"),
                )
            except ValueError as ve:
                return {"ok": False, "error": f"Related person: {ve}"}

        result = build_main_question_report(question.strip(), subject, related=related)
        if result.get("ok"):
            result["html"] = result.get("html_inline") or result.get("html", "")
            slug = (client_name.strip() or "Client").replace(" ", "_")
            if save_report.lower() in ("1", "true", "yes"):
                from pathlib import Path
                reports_dir = BASE_DIR / "reports" / slug
                save_main_question_report(result, reports_dir, slug)
            result["remedy_saved"] = result.get("remedy_path")
            result["remedy_related_saved"] = result.get("remedy_related_path")
        return result

    # jsonable_encoder converts nested date/datetime objects (timing windows) to ISO strings.
    return JSONResponse(jsonable_encoder(await loop.run_in_executor(None, do_answer)))


@app.post("/api/future-event")
async def api_future_event(
    client_name: str = Form(""),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    rectified_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    client_gender: str = Form("Male"),
    event_type: str = Form("marriage"),
    consultation_date: str = Form(""),
):
    from birth_place_resolve import normalize_birth_time, normalize_dob
    from future_event_timing import predict_next_event

    if not client_dob.strip() or not birth_time.strip():
        raise HTTPException(400, "DOB and birth time required.")
    if not birth_latitude.strip() or not birth_longitude.strip() or not birth_timezone.strip():
        raise HTTPException(400, "Select a place from the dropdown first.")
    if not event_type.strip():
        raise HTTPException(400, "Select an event type.")

    try:
        dob = normalize_dob(client_dob)
        birth_time_norm = normalize_birth_time(birth_time)
        rect_norm = normalize_birth_time(rectified_time) if rectified_time.strip() else ""
    except ValueError as ve:
        raise HTTPException(400, str(ve))

    gender_int = 1 if client_gender.lower().startswith("f") else 0
    loop = asyncio.get_running_loop()

    def do_predict():
        return predict_next_event(
            client_name=client_name.strip() or "Client",
            dob=dob,
            birth_time=birth_time_norm,
            rectified_time=rect_norm,
            latitude=float(birth_latitude),
            longitude=float(birth_longitude),
            timezone=float(birth_timezone),
            place_name=birth_place.strip(),
            gender=gender_int,
            event_type=event_type.strip(),
            consultation_date=consultation_date.strip(),
        )

    return JSONResponse(jsonable_encoder(await loop.run_in_executor(None, do_predict)))


def _rel_to_url(rel: str) -> str:
    if not rel:
        return ""
    if rel.startswith("/"):
        return rel
    return "/" + rel.replace("\\", "/")


async def _run_cursor_human_background(session_id: str) -> None:
    session = get_session(session_id)
    session_dir = session.dir
    try:
        manifest = load_session_manifest(session_dir)
        loop = asyncio.get_running_loop()

        def do_run():
            return run_cursor_human_report(manifest, session_dir)

        await session.emit("Starting Cursor CLI for human-style confluence + client report…", "info")
        ok, result = await loop.run_in_executor(None, do_run)
        if ok:
            conf_rel = result.get("cursor_confluence") or manifest.get("cursor_confluence_out", "")
            user_rel = result.get("cursor_user") or manifest.get("cursor_user_out", "")
            await session.emit("✅ Cursor human reports ready.", "success")
            await session.emit_raw({
                "kind": "cursor_human_done",
                "success": True,
                "cursor_confluence": _rel_to_url(conf_rel),
                "cursor_user": _rel_to_url(user_rel),
                "client": manifest.get("slug", ""),
                "msg": result.get("msg", "Cursor human reports ready."),
            })
        else:
            err = result.get("error", "Cursor human report failed")
            await session.emit(f"❌ Cursor human report failed: {err}", "error")
            await session.emit_raw({
                "kind": "cursor_human_done",
                "success": False,
                "error": err,
            })
    except Exception as exc:
        await session.emit(f"❌ Cursor human report error: {exc}", "error")
        await session.emit_raw({
            "kind": "cursor_human_done",
            "success": False,
            "error": str(exc),
        })
    finally:
        _cursor_human_running[session_id] = False


@app.post("/api/cursor-human-report")
async def api_cursor_human_report(session_id: str = Form(...)):
    if not find_cursor_cmd():
        raise HTTPException(503, "cursor-agent not found in PATH. Install Cursor CLI first.")
    session_dir = SESSIONS_DIR / session_id
    if not (session_dir / "session_manifest.json").is_file():
        raise HTTPException(404, "Session manifest not found. Generate Python reports first.")
    if _cursor_human_running.get(session_id):
        raise HTTPException(409, "Cursor human report already running for this session.")
    _cursor_human_running[session_id] = True
    asyncio.create_task(_run_cursor_human_background(session_id))
    return JSONResponse({"queued": True, "msg": "Cursor human report started. Watch log for progress."})


@app.get("/api/muhurat-events")
async def api_muhurat_events():
    return JSONResponse({"events": event_catalog()})


@app.post("/api/muhurat-check")
async def api_muhurat_check(
    session_id: str = Form(""),
    event_type: str = Form(...),
    target_date: str = Form(""),
    client_name: str = Form(""),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    panchang_place: str = Form(""),
    panchang_latitude: str = Form(""),
    panchang_longitude: str = Form(""),
    panchang_timezone: str = Form(""),
    client_gender: str = Form("Male"),
):
    from birth_place_resolve import normalize_birth_time, normalize_dob
    from datetime import date as date_cls

    if not event_type.strip():
        raise HTTPException(400, "Select an event type.")

    rule = get_event_rule(event_type.strip())
    if not rule:
        raise HTTPException(400, f"Unknown event type: {event_type.strip()}")
    req = event_requirements(rule)

    dob_norm = ""
    if client_dob.strip():
        try:
            dob_norm = normalize_dob(client_dob)
        except ValueError as ve:
            raise HTTPException(400, str(ve))
    elif req["requires_dob"] or req["requires_natal_chart"]:
        raise HTTPException(400, "Date of birth is required for this event.")

    try:
        td = date_cls.fromisoformat(target_date.strip()) if target_date.strip() else date_cls.today()
    except ValueError:
        raise HTTPException(400, "Invalid date — use YYYY-MM-DD.")

    if not (
        panchang_latitude.strip()
        and panchang_longitude.strip()
        and panchang_timezone.strip()
    ):
        raise HTTPException(
            400,
            "Select event location for panchang (city where the event happens).",
        )
    p_lat = float(panchang_latitude)
    p_lon = float(panchang_longitude)
    p_tz = float(panchang_timezone)
    p_place = panchang_place.strip() or "EventLocation"

    b_lat = b_lon = b_tz = None
    if birth_latitude.strip() and birth_longitude.strip() and birth_timezone.strip():
        b_lat = float(birth_latitude)
        b_lon = float(birth_longitude)
        b_tz = float(birth_timezone)
    elif req["requires_natal_chart"]:
        raise HTTPException(
            400,
            "Select birth place above — natal chart is required for this event.",
        )

    chart_lat = b_lat if b_lat is not None else p_lat
    chart_lon = b_lon if b_lon is not None else p_lon
    chart_tz = b_tz if b_tz is not None else p_tz
    chart_place = birth_place.strip() or p_place

    birth_time_norm = ""
    if birth_time.strip():
        try:
            birth_time_norm = normalize_birth_time(birth_time)
        except ValueError as ve:
            raise HTTPException(400, str(ve))
    elif req["requires_natal_chart"]:
        raise HTTPException(400, "Birth time is required for this event (natal chart needed).")

    gender_int = 1 if client_gender.lower().startswith("f") else 0
    session_dir = SESSIONS_DIR / session_id if session_id.strip() else None
    loop = asyncio.get_running_loop()
    event_id = event_type.strip()

    def do_check():
        try:
            pc = resolve_pc_for_muhurat(
                session_dir=session_dir,
                event_id=event_id,
                client_name=client_name.strip() or "Client",
                client_dob=dob_norm,
                birth_time=birth_time_norm,
                latitude=chart_lat,
                longitude=chart_lon,
                timezone=chart_tz,
                place_name=chart_place,
                gender=gender_int,
                load_pc_for_session=load_pc_for_session,
            )
        except ValueError as ve:
            return {"ok": False, "error": str(ve)}
        except FileNotFoundError:
            try:
                pc = resolve_pc_for_muhurat(
                    session_dir=None,
                    event_id=event_id,
                    client_name=client_name.strip() or "Client",
                    client_dob=dob_norm,
                    birth_time=birth_time_norm,
                    latitude=chart_lat,
                    longitude=chart_lon,
                    timezone=chart_tz,
                    place_name=chart_place,
                    gender=gender_int,
                )
            except ValueError as ve:
                return {"ok": False, "error": str(ve)}
        result = check_muhurat(
            event_id=event_type.strip(),
            target=td,
            pc=pc,
            latitude=p_lat,
            longitude=p_lon,
            timezone=p_tz,
            place_name=p_place,
        )
        if not result.get("available"):
            return {"ok": False, "error": result.get("error", "Muhurat check failed")}
        return {"ok": True, "result": result}

    out = await loop.run_in_executor(None, do_check)
    if not out.get("ok"):
        return JSONResponse({"success": False, "error": out.get("error", "Failed")}, status_code=400)
    return JSONResponse({"success": True, "result": out["result"]})


@app.post("/api/kundali-match")
async def api_kundali_match(
    groom_name: str = Form(""),
    groom_dob: str = Form(""),
    groom_birth_time: str = Form(""),
    groom_place: str = Form(""),
    groom_latitude: str = Form(""),
    groom_longitude: str = Form(""),
    groom_timezone: str = Form(""),
    bride_name: str = Form(""),
    bride_dob: str = Form(""),
    bride_birth_time: str = Form(""),
    bride_place: str = Form(""),
    bride_latitude: str = Form(""),
    bride_longitude: str = Form(""),
    bride_timezone: str = Form(""),
    match_method: str = Form("North"),
):
    from birth_place_resolve import normalize_birth_time, normalize_dob
    from datetime import date as date_cls

    def _person_form(role: str, name, dob, tob, place, lat, lon, tz, gender: int):
        if not name.strip() or not dob.strip() or not tob.strip():
            raise HTTPException(400, f"{role.capitalize()}: name, DOB and birth time are required.")
        if not lat.strip() or not lon.strip() or not tz.strip():
            raise HTTPException(400, f"{role.capitalize()}: select place from dropdown.")
        try:
            dob_n = normalize_dob(dob)
            tob_n = normalize_birth_time(tob)
        except ValueError as ve:
            raise HTTPException(400, f"{role.capitalize()}: {ve}")
        return {
            "name": name.strip(),
            "dob": dob_n,
            "birth_time": tob_n,
            "place": place.strip(),
            "latitude": float(lat),
            "longitude": float(lon),
            "timezone": float(tz),
            "gender": gender,
        }

    try:
        groom_in = _person_form(
            "groom", groom_name, groom_dob, groom_birth_time,
            groom_place, groom_latitude, groom_longitude, groom_timezone, 0,
        )
        bride_in = _person_form(
            "bride", bride_name, bride_dob, bride_birth_time,
            bride_place, bride_latitude, bride_longitude, bride_timezone, 1,
        )
    except HTTPException:
        raise

    method = "South" if match_method.strip().lower().startswith("south") else "North"
    loop = asyncio.get_running_loop()

    def do_match():
        groom_pc = build_person_chart(
            name=groom_in["name"],
            dob=groom_in["dob"],
            birth_time=groom_in["birth_time"],
            latitude=groom_in["latitude"],
            longitude=groom_in["longitude"],
            timezone=groom_in["timezone"],
            place_name=groom_in["place"],
            gender=groom_in["gender"],
        )
        bride_pc = build_person_chart(
            name=bride_in["name"],
            dob=bride_in["dob"],
            birth_time=bride_in["birth_time"],
            latitude=bride_in["latitude"],
            longitude=bride_in["longitude"],
            timezone=bride_in["timezone"],
            place_name=bride_in["place"],
            gender=bride_in["gender"],
        )
        result = match_kundali(
            groom=groom_pc,
            bride=bride_pc,
            method=method,
            groom_name=groom_in["name"],
            bride_name=bride_in["name"],
            groom_dob=groom_in["dob"],
            bride_dob=bride_in["dob"],
        )
        slug_g = match_slug(groom_in["name"])
        slug_b = match_slug(bride_in["name"])
        today = date_cls.today().strftime("%Y%m%d")
        out_file = REPORTS_DIR / f"Kundali_Match_{slug_g}_{slug_b}_{today}.html"
        write_kundali_match_report(
            result=result,
            groom_meta={
                "name": groom_in["name"],
                "dob": groom_in["dob"],
                "tob": groom_in["birth_time"],
                "place": groom_in["place"],
            },
            bride_meta={
                "name": bride_in["name"],
                "dob": bride_in["dob"],
                "tob": bride_in["birth_time"],
                "place": bride_in["place"],
            },
            out_path=out_file,
        )
        rel = out_file.relative_to(BASE_DIR).as_posix()
        return {"result": result, "report_rel": rel}

    try:
        out = await loop.run_in_executor(None, do_match)
    except ValueError as ve:
        return JSONResponse({"success": False, "error": str(ve)}, status_code=400)
    except Exception as exc:
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

    report_url = "/" + out["report_rel"]
    return JSONResponse({
        "success": True,
        "result": out["result"],
        "report_url": report_url,
        "report_path": out["report_rel"],
    })


@app.post("/api/daily-moon")
async def api_daily_moon(
    session_id: str = Form(...),
    target_date: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
):
    from datetime import date as date_cls

    session_dir = SESSIONS_DIR / session_id
    try:
        pc = load_pc_for_session(session_dir)
    except FileNotFoundError:
        raise HTTPException(404, "Generate Python reports first — precomputed chart missing.")

    try:
        td = date_cls.fromisoformat(target_date.strip()) if target_date.strip() else date_cls.today()
    except ValueError:
        raise HTTPException(400, "Invalid date — use YYYY-MM-DD.")

    lat, lon, tz = 28.6, 77.2, 5.5
    manifest = {}
    if (session_dir / "session_manifest.json").is_file():
        manifest = load_session_manifest(session_dir)
        lat = float(manifest.get("birth_latitude", lat))
        lon = float(manifest.get("birth_longitude", lon))
        tz = float(manifest.get("birth_timezone", tz))
    if birth_latitude.strip() and birth_longitude.strip() and birth_timezone.strip():
        lat = float(birth_latitude)
        lon = float(birth_longitude)
        tz = float(birth_timezone)

    loop = asyncio.get_running_loop()

    def do_daily():
        data = compute_daily_moon_guide(pc, td, latitude=lat, longitude=lon, timezone=tz)
        slug = manifest.get("slug") or pc.get("meta", {}).get("client", "Client").replace(" ", "_")
        reports_dir = BASE_DIR / manifest.get("reports_dir", f"reports/{slug}")
        out = write_daily_moon_report(data, reports_dir, slug)
        rel = str(out.relative_to(BASE_DIR)).replace("\\", "/")
        return data, rel

    try:
        data, rel = await loop.run_in_executor(None, do_daily)
    except RuntimeError as e:
        raise HTTPException(503, str(e))

    return JSONResponse({
        "success": True,
        "url": "/" + rel,
        "tone": data.get("tone"),
        "opening": data.get("opening"),
        "date": data.get("date"),
        "lucky_numbers": data.get("lucky_numbers"),
        "lucky_colors": data.get("lucky_colors"),
        "dos": data.get("dos"),
        "donts": data.get("donts"),
    })


@app.get("/api/cursor-chat-history")
async def api_cursor_chat_history(session_id: str = Query(...)):
    session_dir = SESSIONS_DIR / session_id
    memory = CursorChatMemory(session_dir / "cursor_chat_history.json")
    return JSONResponse({"turns": memory.get_turns()})


@app.post("/api/cursor-chat")
async def api_cursor_chat(session_id: str = Form(...), question: str = Form(...)):
    if not question.strip():
        raise HTTPException(400, "Question is required.")
    if not find_cursor_cmd():
        raise HTTPException(503, "cursor-agent not found in PATH.")
    session_dir = SESSIONS_DIR / session_id
    if not (session_dir / "session_manifest.json").is_file():
        raise HTTPException(404, "Session manifest not found. Generate Python reports first.")
    manifest = load_session_manifest(session_dir)
    memory = CursorChatMemory(session_dir / "cursor_chat_history.json")
    loop = asyncio.get_running_loop()

    def do_chat():
        return run_cursor_chat(manifest, session_dir, question.strip(), memory)

    ok, answer_or_err = await loop.run_in_executor(None, do_chat)
    if ok:
        return JSONResponse({"success": True, "answer": answer_or_err})
    return JSONResponse({"success": False, "error": answer_or_err}, status_code=500)


@app.post("/api/numerology")
async def api_numerology(
    client_name: str = Form(""),
    client_dob: str = Form(""),
    client_gender: str = Form("Male"),
):
    from birth_place_resolve import normalize_dob
    from datetime import date as date_cls

    if not client_name.strip():
        raise HTTPException(400, "Client name is required.")
    if not client_dob.strip():
        raise HTTPException(400, "Date of birth is required (YYYY-MM-DD).")
    try:
        dob = normalize_dob(client_dob.strip())
    except ValueError as ve:
        raise HTTPException(400, str(ve))

    slug = make_slug(client_name.strip())
    client_reports_dir = REPORTS_DIR / slug
    client_reports_dir.mkdir(parents=True, exist_ok=True)
    loop = asyncio.get_running_loop()

    def do_numerology():
        _reload_deterministic_modules()
        d = date_cls.fromisoformat(dob)
        html, _slug = generate_numerology_html(
            client_name.strip(), d, client_gender.strip() or "—", date_cls.today())
        out_path = client_reports_dir / f"Numerology_{slug}_{dob.replace('-', '')}.html"
        out_path.write_text(finalize_report_html(html, client_name or ""), encoding="utf-8")
        return out_path

    try:
        out_path = await loop.run_in_executor(None, do_numerology)
    except Exception as exc:
        logger.exception("Numerology generation failed")
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

    rel = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")
    return JSONResponse({
        "success": True,
        "report": "/" + rel,
        "message": f"Numerology report for {client_name.strip()} (DOB {dob})",
    })


@app.post("/api/palmistry")
async def api_palmistry(
    session_id: str = Form(""),
    client_name: str = Form(""),
    active_hand: str = Form("right"),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    images: List[UploadFile] = File(default=[]),
):
    if not client_name.strip():
        raise HTTPException(400, "Client name is required.")
    img_list: List[Tuple[str, bytes]] = []
    for img in images:
        if img.filename:
            img_list.append((img.filename, await img.read()))
    if not img_list:
        raise HTTPException(400, "Upload at least one palm image (JPG/PNG).")

    session = get_session(session_id) if session_id.strip() else None
    input_dir = (session.dir / "input") if session else (SESSIONS_DIR / "_palm_only" / uuid.uuid4().hex)
    input_dir.mkdir(parents=True, exist_ok=True)

    palm_paths: List[str] = []
    for img_name, img_data in img_list:
        safe_img = re.sub(r"[^0-9A-Za-z_.\-]+", "_", img_name)
        img_path = input_dir / safe_img
        img_path.write_bytes(img_data)
        palm_paths.append(str(img_path))

    slug = make_slug(client_name.strip())
    client_reports_dir = REPORTS_DIR / slug
    client_reports_dir.mkdir(parents=True, exist_ok=True)
    hand = "left" if active_hand.strip().lower().startswith("left") else "right"
    loop = asyncio.get_running_loop()

    # Build optional birth details — when present, the combined report adds a real
    # ephemeris birth-chart lane (PyJHora + Swiss Ephemeris) on top of the palm read.
    birth: Optional[dict] = None
    if client_dob.strip() and birth_time.strip():
        birth = {
            "client_name": client_name.strip() or "Client",
            "dob": client_dob.strip(),
            "birth_time": birth_time.strip(),
            "place": birth_place.strip(),
        }
        try:
            if birth_latitude.strip() and birth_longitude.strip() and birth_timezone.strip():
                birth["latitude"] = float(birth_latitude)
                birth["longitude"] = float(birth_longitude)
                birth["timezone"] = float(birth_timezone)
        except ValueError:
            pass

    def do_palmistry():
        _reload_deterministic_modules()
        out_path = client_reports_dir / f"Palmistry_{slug}_{TODAY}.html"
        generate_combined_report(
            palm_paths,
            out_path,
            client_name=client_name.strip() or "Client",
            active_hand=hand,
            embed_overlays=True,
            birth=birth,
        )
        return out_path

    try:
        out_path = await loop.run_in_executor(None, do_palmistry)
    except Exception as exc:
        logger.exception("Palmistry generation failed")
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)

    rel = str(out_path.relative_to(BASE_DIR)).replace("\\", "/")
    chart_note = " + birth-chart lane" if birth else ""
    return JSONResponse({
        "success": True,
        "report": "/" + rel,
        "message": f"Palmistry report for {client_name.strip()} ({len(img_list)} image(s), dominant {hand} hand{chart_note})",
    })


@app.post("/generate")
async def generate(
    session_id: str = Form(...),
    client_name: str = Form(""),
    client_dob: str = Form(""),
    birth_time: str = Form(""),
    birth_place: str = Form(""),
    birth_latitude: str = Form(""),
    birth_longitude: str = Form(""),
    birth_timezone: str = Form(""),
    client_gender: str = Form("Male"),
    btr_higher_education: str = Form(""),
    btr_foreign_travel: str = Form(""),
    btr_marriage: str = Form(""),
    btr_child: str = Form(""),
    btr_first_job: str = Form(""),
    btr_custom_events: str = Form(""),
    life_events: str = Form(""),
    client_question: str = Form(""),
    images: List[UploadFile] = File(default=[]),
):
    if not client_name.strip():
        raise HTTPException(400, "Client name is required.")
    if not client_dob.strip():
        raise HTTPException(400, "Date of birth is required (YYYY-MM-DD).")
    if not birth_time.strip():
        raise HTTPException(400, "Time of birth is required (HH:MM).")
    if not birth_place.strip():
        raise HTTPException(400, "Place of birth is required.")
    if not birth_latitude.strip() or not birth_longitude.strip() or not birth_timezone.strip():
        raise HTTPException(400, "Select a place from the dropdown list.")

    lat = float(birth_latitude)
    lon = float(birth_longitude)
    tz = float(birth_timezone)

    img_list: List[Tuple[str, bytes]] = []
    for img in images:
        if img.filename:
            img_list.append((img.filename, await img.read()))

    session = get_session(session_id)
    asyncio.create_task(_run_pipeline(
        session,
        img_list,
        client_name.strip(),
        client_dob.strip(),
        birth_time.strip(),
        birth_place.strip(),
        lat,
        lon,
        tz,
        client_gender.strip(),
        life_events.strip(),
        client_question.strip(),
        {
            "higher_education": btr_higher_education.strip(),
            "foreign_travel": btr_foreign_travel.strip(),
            "marriage": btr_marriage.strip(),
            "child": btr_child.strip(),
            "first_job": btr_first_job.strip(),
            "custom_events": btr_custom_events.strip(),
        },
    ))
    return JSONResponse({"status": "queued"})


async def _run_pipeline(*args, **kwargs):
    """Queue gate around the heavy pipeline: serialise to MAX_CONCURRENT and
    stream queue position + ETA to waiting clients."""
    session: Session = args[0]
    await _gen_queue.acquire(session)
    _t0 = time.time()
    try:
        await _run_pipeline_inner(*args, **kwargs)
    finally:
        await _gen_queue.release(time.time() - _t0)


async def _run_pipeline_inner(
    session: Session,
    img_list: List[Tuple[str, bytes]],
    client_name: str,
    dob: str,
    birth_time: str,
    birth_place: str,
    birth_latitude: float,
    birth_longitude: float,
    birth_timezone: float,
    gender: str,
    life_events: str,
    client_question: str = "",
    btr_events: dict | None = None,
):
    loop = asyncio.get_running_loop()

    async def log(msg: str, kind: str = "info"):
        await session.emit(msg, kind)

    async def step(name: str, state: str):
        await session.emit_raw({"kind": "step", "step": name, "state": state, "msg": ""})

    try:
        from birth_place_resolve import normalize_birth_time, normalize_dob, resolve_birth_place

        # ── 1. Validate birth input + geocode place ───────────────────
        await log("📥 Validating birth data…")
        input_dir = session.dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)

        try:
            dob = normalize_dob(dob)
            birth_time_norm = normalize_birth_time(birth_time)
        except ValueError as ve:
            await log(f"❌ {ve}", "error")
            await session.emit_raw({"kind": "done", "success": False, "confluence": None, "user": None, "msg": ""})
            return

        await step("extract", "active")
        await log(f"🌍 Place: {birth_place}…")

        def do_geocode():
            return resolve_birth_place(
                birth_place,
                latitude=birth_latitude,
                longitude=birth_longitude,
                timezone=birth_timezone,
            )

        try:
            geo = await loop.run_in_executor(None, do_geocode)
        except Exception as geo_err:
            await log(f"❌ Place lookup failed: {geo_err}", "error")
            await session.emit_raw({"kind": "done", "success": False, "confluence": None, "user": None, "msg": ""})
            return

        place_label = geo["place"]
        latitude = geo["latitude"]
        longitude = geo["longitude"]
        timezone = geo["timezone"]
        gender_int = 1 if gender.lower().startswith("f") else 0
        await log(
            f"   ✓ {place_label} → lat {latitude:.4f}, lon {longitude:.4f}, TZ {timezone:+.1f}"
        )
        await log(f"   ✓ Birth clock {birth_time_norm} on {dob}")

        # ── 1b. Birth time rectification (optional) ───────────────────
        btr_events = btr_events or {}
        if any((btr_events.get(k) or "").strip() for k in (
            "higher_education", "foreign_travel", "marriage", "child", "first_job", "custom_events"
        )):
            await log("🕐 Running Python BTR (Precision Sandwich: D4-D7-D9-D10-D24-D60)…")

            def do_btr_pipeline():
                from btr_rectify import rectify_birth_time
                return rectify_birth_time(
                    client_name=client_name or "Client",
                    dob=dob,
                    birth_time=birth_time_norm,
                    latitude=latitude,
                    longitude=longitude,
                    timezone=timezone,
                    place_name=place_label,
                    gender=gender_int,
                    event_fields=btr_events,
                    custom_events=btr_events.get("custom_events", ""),
                )

            try:
                btr = await loop.run_in_executor(None, do_btr_pipeline)
                if btr.get("skipped"):
                    await log(f"   ℹ BTR skipped: {btr.get('reason', '')}")
                else:
                    kind = "success" if btr.get("apply") else "info"
                    await log(f"   {btr.get('message', 'BTR complete')}", kind)
                    for ev in btr.get("event_results") or []:
                        await log(
                            f"      · {ev.get('label')}: {ev.get('md_lord')}/{ev.get('ad_lord')} "
                            f"score {ev.get('score')} ({ev.get('strength')})"
                        )
                    if btr.get("apply") and btr.get("corrected_time"):
                        birth_time_norm = btr["corrected_time"]
                        await log(f"   ✓ Using rectified birth time {birth_time_norm}", "success")
            except Exception as btr_err:
                await log(f"   ⚠ BTR failed (using entered time): {btr_err}", "warn")

        await step("extract", "done")
        await session.emit_raw({"kind": "progress", "value": 12, "msg": ""})

        chart_kw = {
            "birth_time": birth_time_norm,
            "latitude": latitude,
            "longitude": longitude,
            "timezone": timezone,
            "place_name": place_label,
            "gender": gender_int,
        }
        tob_display = birth_time_norm[:5]
        place_display = place_label

        # ── 2. Client slug + output folder (palmistry / numerology are separate APIs) ─
        slug = make_slug(client_name)
        slug_lower = client_name.split()[0].lower() if client_name else "client"
        await log(f"   ℹ Client: {client_name} | DOB: {dob} | Slug: {slug}")

        client_reports_dir = REPORTS_DIR / slug
        client_reports_dir.mkdir(parents=True, exist_ok=True)
        await log(f"   ✓ Output folder: reports/{slug}/")

        palm_paths: List[str] = []
        numerology_rel: Optional[str] = None
        palmistry_rel: Optional[str] = None
        palm_analysis: Optional[dict] = None

        # Pick up latest Python lane fixes without requiring a manual server restart.
        await loop.run_in_executor(None, _reload_deterministic_modules)

        extracted_txt_path = None

        # ── 3. Pre-compute all astrology math (PyJHora) ─────────────────
        precomputed_json_path = None
        if dob:
            await log("🔭 Pre-computing chart via PyJHora (D1, divisional, AV, dasha, KP)…")
            json_out = input_dir / f"{slug}_precomputed.json"

            def do_precompute():
                from astro_precompute import resolve_precompute
                pc = resolve_precompute(
                    client_name, dob,
                    birth_time=chart_kw["birth_time"],
                    latitude=chart_kw["latitude"],
                    longitude=chart_kw["longitude"],
                    timezone=chart_kw["timezone"],
                    place_name=chart_kw["place_name"],
                    gender=chart_kw["gender"],
                )
                json_out.write_text(json.dumps(pc, indent=2, default=str), encoding="utf-8")
                src = pc.get("meta", {}).get("source", "unknown")
                return 0, f"source={src} lagna={pc.get('lagna',{}).get('sign','?')}"

            try:
                import json
                pc_rc, pc_out = await loop.run_in_executor(None, do_precompute)
                if pc_rc == 0 and json_out.exists():
                    precomputed_json_path = str(json_out.relative_to(BASE_DIR))
                    await log(f"   ✓ Pre-computed data saved: {precomputed_json_path} ({json_out.stat().st_size:,} bytes)")
                    await log(f"   ✓ {pc_out.strip()[:200]}")
                else:
                    await log(f"   ⚠ Pre-compute warning (code {pc_rc}): {pc_out[:200]}", "warn")
            except Exception as pc_err:
                await log(f"   ⚠ Pre-compute skipped: {pc_err}", "warn")
        else:
            await log("   ℹ Skipping pre-compute — DOB not available")

        # Numerology + Palmistry: use sidebar sections (/api/numerology, /api/palmistry)
        await log("   ℹ Numerology + Palmistry skipped — generate from their sidebar sections")

        _precomputed_abs = (
            str(BASE_DIR / precomputed_json_path) if precomputed_json_path else None
        )
        lane_kw = {
            "precomputed_path": _precomputed_abs,
            "birth_time": chart_kw["birth_time"],
            "latitude": chart_kw["latitude"],
            "longitude": chart_kw["longitude"],
            "timezone": chart_kw["timezone"],
            "gender": chart_kw["gender"],
        }
        av_kw = {
            "precomputed_path": _precomputed_abs,
            "birth_time": chart_kw["birth_time"],
            "latitude": chart_kw["latitude"],
            "longitude": chart_kw["longitude"],
            "timezone": chart_kw["timezone"],
            "place_name": chart_kw["place_name"],
            "gender": chart_kw["gender"],
        }

        # ── 3b. Summary tables (ON the UI) + granular detail files (folder) ─
        #  The 4 summary reports (12 houses, 9 planets, 20 divisional charts,
        #  108 rules) are written to reports/{slug}/ and surfaced on the UI grid.
        #  The 37 granular per-item building blocks (one per house / planet /
        #  varga) go into reports/{slug}/details/ — a subfolder the UI globs
        #  never scan, so they stay off the grid but remain on disk.
        summary_links: list[dict] = []
        if dob and _precomputed_abs:
            await log("🧮 Generating summary tables + granular detail files…")

            def do_summaries():
                import json as _json
                from chart_summary_report import (
                    build_houses_html, build_planets_html, build_divisional_html,
                    write_granular,
                )
                from prediction108_transit import attach_contexts

                pc = _json.loads(Path(_precomputed_abs).read_text(encoding="utf-8"))
                name = client_name or "Client"
                links, notes = [], []

                # 1) the 4 UI-facing summary reports (top-level folder)
                summ = [
                    ("The 12 Houses", f"Summary_Houses_{slug}.html", lambda: build_houses_html(pc, name)),
                    ("The 9 Planets", f"Summary_Planets_{slug}.html", lambda: build_planets_html(pc, name)),
                    ("The 20 Divisional Charts", f"Summary_Divisional_{slug}.html", lambda: build_divisional_html(pc, name)),
                ]
                for label, fname, fn in summ:
                    try:
                        fp = client_reports_dir / fname
                        fp.write_text(fn(), encoding="utf-8")
                        links.append({"name": label, "url": "/" + str(fp.relative_to(BASE_DIR)).replace("\\", "/")})
                    except Exception as e:  # noqa: BLE001
                        notes.append(f"{fname} FAILED: {e}")

                try:
                    attach_contexts(pc, latitude=chart_kw["latitude"],
                                    longitude=chart_kw["longitude"], timezone=chart_kw["timezone"])
                    from prediction108_report import write_report as write_108
                    fp = write_108(pc, client_reports_dir, name)
                    links.append({"name": "108 Predictive Rules", "url": "/" + str(fp.relative_to(BASE_DIR)).replace("\\", "/")})
                except Exception as e:  # noqa: BLE001
                    notes.append(f"Predictive_108_Rules FAILED: {e}")

                # 2) Dasha + transit confluence timeline (UI) + per-window detail pages
                dasha_rows = None
                try:
                    from dasha_confluence_report import write_report as write_dasha
                    fp, dasha_rows = write_dasha(
                        pc, client_reports_dir, name,
                        lat=chart_kw["latitude"], lon=chart_kw["longitude"], tz=chart_kw["timezone"])
                    links.append({"name": "Dasha & Transit Confluence Timeline",
                                  "url": "/" + str(fp.relative_to(BASE_DIR)).replace("\\", "/")})
                except Exception as e:  # noqa: BLE001
                    notes.append(f"Dasha_Confluence FAILED: {e}")

                # 3) Final plain-English consultation report (the capstone, on UI)
                try:
                    from final_user_report import write_report as write_personal
                    fp = write_personal(pc, client_reports_dir, name,
                                        lat=chart_kw["latitude"], lon=chart_kw["longitude"], tz=chart_kw["timezone"])
                    links.insert(0, {"name": "Personal Reading (plain English)",
                                     "url": "/" + str(fp.relative_to(BASE_DIR)).replace("\\", "/")})
                except Exception as e:  # noqa: BLE001
                    notes.append(f"Personal_Reading FAILED: {e}")

                # 4) granular building blocks (background subfolder)
                try:
                    details = write_granular(pc, client_reports_dir / "details", name)
                    notes.append(f"details: {len(details)} item files")
                except Exception as e:  # noqa: BLE001
                    notes.append(f"details FAILED: {e}")
                if dasha_rows is not None:
                    try:
                        from dasha_confluence_report import write_details as write_dasha_details
                        dd = write_dasha_details(pc, dasha_rows, client_reports_dir / "details", name)
                        notes.append(f"dasha details: {len(dd)} files")
                    except Exception as e:  # noqa: BLE001
                        notes.append(f"dasha details FAILED: {e}")

                return links, notes

            try:
                summary_links, _notes = await loop.run_in_executor(None, do_summaries)
                for item in summary_links:
                    await log(f"   ✓ {item.get('name', 'report')} ready: {item.get('url', '')}", "success")
                await log(f"   ✓ {len(summary_links)} summary/reading reports on UI · "
                          f"granular + dasha files in reports/{slug}/details/", "success")
                for n in _notes:
                    if "FAILED" in n:
                        await log(f"   ⚠ {n}", "warn")
            except Exception as sum_err:
                await log(f"   ⚠ Summary tables skipped: {sum_err}", "warn")

        # ── 4d. Bhrigu Nandi Nadi (BNN) — deterministic Python (no LLM) ─
        bnn_rel: Optional[str] = None
        if dob:
            await log("📖 Generating BNN report (deterministic, rule-based — no LLM)…")

            def do_bnn():
                html_doc, _summary = generate_bnn_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_BNN_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                bnn_path = await loop.run_in_executor(None, do_bnn)
                bnn_rel = str(bnn_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ BNN ready: {bnn_rel}", "success")
                await step("bnn", "done")
            except Exception as bnn_err:
                await log(f"   ⚠ BNN generation failed: {bnn_err}", "warn")
        else:
            await log("   ℹ BNN skipped — DOB not available")

        # ── 4d2. Bhardwaj — deterministic Python + semantic corpus (no LLM) ─
        bhardwaj_rel: Optional[str] = None
        if dob:
            await log("📚 Generating Bhardwaj report (semantic MiniLM + book corpus — no LLM)…")

            def do_bhardwaj():
                html_doc, _summary = generate_bhardwaj_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Bhardwaj_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                bw_path = await loop.run_in_executor(None, do_bhardwaj)
                bhardwaj_rel = str(bw_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Bhardwaj ready: {bhardwaj_rel}", "success")
                await step("bhardwaj", "done")
            except Exception as bw_err:
                await log(f"   ⚠ Bhardwaj generation failed (Cursor will fall back): {bw_err}", "warn")
        else:
            await log("   ℹ Bhardwaj skipped — DOB not available")

        # ── 4e. Jaimini — deterministic Python (no LLM) ────────────────
        jaimini_rel: Optional[str] = None
        if dob:
            await log("⚖️ Generating Jaimini report (deterministic, rule-based — no LLM)…")

            def do_jaimini():
                html_doc, _s = generate_jaimini_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Jaimini_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                jm_path = await loop.run_in_executor(None, do_jaimini)
                jaimini_rel = str(jm_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Jaimini ready: {jaimini_rel}", "success")
                await step("jaimini", "done")
            except Exception as jm_err:
                await log(f"   ⚠ Jaimini generation failed (Cursor will fall back): {jm_err}", "warn")
        else:
            await log("   ℹ Jaimini skipped — DOB not available")

        # ── 4f. Ashtakavarga — deterministic Python (no LLM) ───────────
        ashtaka_rel: Optional[str] = None
        if dob:
            await log("🔢 Generating Ashtakavarga report (deterministic, rule-based — no LLM)…")

            def do_ashtaka():
                html_doc, _s = generate_ashtakavarga_html(
                    client_name or "Client", dob,
                    **av_kw,
                )
                out_path = client_reports_dir / f"Vedic_Ashtakavarga_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                av_path = await loop.run_in_executor(None, do_ashtaka)
                ashtaka_rel = str(av_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Ashtakavarga ready: {ashtaka_rel}", "success")
                await step("ashtakavarga", "done")
            except Exception as av_err:
                await log(f"   ⚠ Ashtakavarga generation failed (Cursor will fall back): {av_err}", "warn")
        else:
            await log("   ℹ Ashtakavarga skipped — DOB not available")

        # ── 4g. KP — deterministic Python (no LLM) ─────────────────────
        kp_rel: Optional[str] = None
        if dob:
            await log("🔭 Generating KP report (deterministic, rule-based — no LLM)…")

            def do_kp():
                html_doc, _s = generate_kp_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_KP_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                kp_path = await loop.run_in_executor(None, do_kp)
                kp_rel = str(kp_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ KP ready: {kp_rel}", "success")
                await step("kp", "done")
            except Exception as kp_err:
                await log(f"   ⚠ KP generation failed (Cursor will fall back): {kp_err}", "warn")
        else:
            await log("   ℹ KP skipped — DOB not available")

        # ── 4h. RTVD — deterministic Python (no LLM) ───────────────────
        rtvd_rel: Optional[str] = None
        if dob:
            await log("📅 Generating RTVD report (deterministic, rule-based — no LLM)…")

            def do_rtvd():
                html_doc, _s = generate_rtvd_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_RTVD_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                rtvd_path = await loop.run_in_executor(None, do_rtvd)
                rtvd_rel = str(rtvd_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ RTVD ready: {rtvd_rel}", "success")
                await step("rtvd", "done")
            except Exception as rtvd_err:
                await log(f"   ⚠ RTVD generation failed: {rtvd_err}", "warn")
        else:
            await log("   ℹ RTVD skipped — DOB not available")

        # ── 4i. Longevity — deterministic Python (no LLM) ──────────────
        longevity_rel: Optional[str] = None
        if dob:
            await log("⚕️ Generating Longevity report (deterministic, rule-based — no LLM)…")

            def do_longevity():
                html_doc, _s = generate_longevity_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Longevity_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                long_path = await loop.run_in_executor(None, do_longevity)
                longevity_rel = str(long_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Longevity ready: {longevity_rel}", "success")
                await step("longevity", "done")
            except Exception as long_err:
                await log(f"   ⚠ Longevity generation failed: {long_err}", "warn")
        else:
            await log("   ℹ Longevity skipped — DOB not available")

        # ── 4j. BlindChart — deterministic Python (no LLM) ─────────────
        blindchart_rel: Optional[str] = None
        if dob:
            await log("🎯 Generating Blind Chart report (deterministic, rule-based — no LLM)…")

            def do_blindchart():
                html_doc, _s = generate_blindchart_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_BlindChart_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                blind_path = await loop.run_in_executor(None, do_blindchart)
                blindchart_rel = str(blind_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Blind Chart ready: {blindchart_rel}", "success")
                await step("blindchart", "done")
            except Exception as blind_err:
                await log(f"   ⚠ Blind Chart generation failed: {blind_err}", "warn")
        else:
            await log("   ℹ Blind Chart skipped — DOB not available")

        # ── 4k. Pillar — deterministic Python (no LLM) ─────────────────
        pillar_rel: Optional[str] = None
        if dob:
            await log("🏛️ Generating Pillar of Life report (deterministic, rule-based — no LLM)…")

            def do_pillar():
                html_doc, _s = generate_pillar_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Pillar_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                pillar_path = await loop.run_in_executor(None, do_pillar)
                pillar_rel = str(pillar_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Pillar ready: {pillar_rel}", "success")
                await step("pillar", "done")
            except Exception as pillar_err:
                await log(f"   ⚠ Pillar generation failed: {pillar_err}", "warn")
        else:
            await log("   ℹ Pillar skipped — DOB not available")

        # ── 4l. Vimshottari — deterministic Python (no LLM) ────────────
        vimshottari_rel: Optional[str] = None
        if dob:
            await log("⏳ Generating Vimshottari Dasha report (deterministic, rule-based — no LLM)…")

            def do_vimshottari():
                html_doc, _s = generate_vimshottari_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Vimshottari_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                vim_path = await loop.run_in_executor(None, do_vimshottari)
                vimshottari_rel = str(vim_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Vimshottari ready: {vimshottari_rel}", "success")
                await step("vimshottari", "done")
            except Exception as vim_err:
                await log(f"   ⚠ Vimshottari generation failed: {vim_err}", "warn")
        else:
            await log("   ℹ Vimshottari skipped — DOB not available")

        # ── 4m. Yogini — deterministic Python (no LLM) ─────────────────
        yogini_rel: Optional[str] = None
        if dob:
            await log("🌙 Generating Yogini Dasha report (deterministic, rule-based — no LLM)…")

            def do_yogini():
                html_doc, _s = generate_yogini_html(
                    client_name or "Client", dob,
                    tob=tob_display, place=place_display,
                    **lane_kw,
                )
                out_path = client_reports_dir / f"Vedic_Yogini_{slug}_{TODAY}.html"
                out_path.write_text(finalize_report_html(html_doc, client_name or ""), encoding="utf-8")
                return out_path

            try:
                yog_path = await loop.run_in_executor(None, do_yogini)
                yogini_rel = str(yog_path.relative_to(BASE_DIR)).replace("\\", "/")
                await log(f"   ✓ Yogini ready: {yogini_rel}", "success")
                await step("yogini", "done")
            except Exception as yog_err:
                await log(f"   ⚠ Yogini generation failed: {yog_err}", "warn")
        else:
            await log("   ℹ Yogini skipped — DOB not available")

        # ── 4n. Confluence + User Report — semantic Python (no LLM) ───
        confluence_rel: Optional[str] = None
        user_rel: Optional[str] = None
        focus_rel: Optional[str] = None
        if dob:
            q_note = f' (focus: "{client_question[:60]}…")' if client_question else ""
            await log(f"🔗 Generating Confluence + User Report (semantic MiniLM — no LLM){q_note}…")

            def do_confluence():
                from chart_identity import ChartIdentityError
                try:
                    conf_html, user_html, focus_html, summary = generate_confluence_reports(
                        "", str(client_reports_dir),
                        client_name or "Client", dob, slug,
                        client_question=client_question,
                        palm_analysis=palm_analysis,
                        **av_kw,
                    )
                except ChartIdentityError as cie:
                    raise RuntimeError(
                        f"Chart identity check failed — wrong precompute for {slug}: {cie}"
                    ) from cie
                conf_path = client_reports_dir / f"Vedic_Confluence_{slug}_{TODAY}.html"
                user_path = client_reports_dir / f"user_report_{slug_lower}.html"
                conf_path.write_text(finalize_report_html(conf_html, client_name or ""), encoding="utf-8")
                user_path.write_text(finalize_report_html(user_html, client_name or ""), encoding="utf-8")
                focus_path = None
                if focus_html and summary.get("focus_domain"):
                    dom = summary["focus_domain"].title()
                    focus_path = client_reports_dir / f"Vedic_Focus_{dom}_{slug}_{TODAY}.html"
                    focus_path.write_text(finalize_report_html(focus_html, client_name or ""), encoding="utf-8")
                return conf_path, user_path, focus_path, summary

            try:
                conf_path, user_path, focus_path, summary = await loop.run_in_executor(None, do_confluence)
                confluence_rel = str(conf_path.relative_to(BASE_DIR)).replace("\\", "/")
                user_rel = str(user_path.relative_to(BASE_DIR)).replace("\\", "/")
                if focus_path and focus_path.exists():
                    focus_rel = str(focus_path.relative_to(BASE_DIR)).replace("\\", "/")
                    await log(f"   ✓ Focus report ({summary.get('focus_domain','')}): {focus_rel}", "success")
                if summary.get("remedy_path"):
                    await log(f"   ✓ Remedy/Gemstone: {summary['remedy_path']}", "success")
                await log(f"   ✓ Confluence ready: {confluence_rel}", "success")
                await log(f"   ✓ User report ready: {user_rel}", "success")
                await step("confluence", "done")
                await step("user", "done")
            except Exception as conf_err:
                await log(f"   ⚠ Confluence generation failed (Cursor will fall back): {conf_err}", "warn")
        else:
            await log("   ℹ Confluence skipped — DOB not available")

        extracted_txt_path = None
        rel_extracted = (
            f"(PyJHora birth-data — no AstroSage extract; see {precomputed_json_path})"
            if precomputed_json_path
            else "(PyJHora birth-data pipeline — no AstroSage extract)"
        )

        # ── 5. Finalize Python reports + session manifest ───────────────
        def to_url(rel: str) -> str:
            return "/" + rel.replace("\\", "/")

        def collect_python_individual_urls() -> list[dict]:
            individual_urls: list[dict] = []
            seen_urls: set[str] = set()
            for rel in (
                numerology_rel, bnn_rel, bhardwaj_rel, jaimini_rel, ashtaka_rel, kp_rel,
                rtvd_rel, longevity_rel, blindchart_rel, pillar_rel, vimshottari_rel,
                yogini_rel, palmistry_rel, focus_rel,
            ):
                if not rel:
                    continue
                p = BASE_DIR / rel
                if p.is_file():
                    u = to_url(rel)
                    if u not in seen_urls:
                        individual_urls.append({"name": p.stem, "url": u})
                        seen_urls.add(u)
            for f in sorted(client_reports_dir.glob(f"Vedic_*_{slug}_*.html")):
                u = to_url(str(f.relative_to(BASE_DIR)).replace("\\", "/"))
                if u not in seen_urls:
                    individual_urls.append({"name": f.stem, "url": u})
                    seen_urls.add(u)
            # summary tables (houses / planets / divisional / 108 rules)
            for item in summary_links:
                u = item.get("url", "")
                if u and u not in seen_urls and (BASE_DIR / u.lstrip("/")).is_file():
                    individual_urls.append(item)
                    seen_urls.add(u)
            return individual_urls

        lane_paths = [
            str(p.relative_to(BASE_DIR)).replace("\\", "/")
            for p in collect_lane_files(client_reports_dir, slug, TODAY)
        ]
        py_conf_rel = confluence_rel or f"reports/{slug}/Vedic_Confluence_{slug}_{TODAY}.html"
        py_user_rel = user_rel or f"reports/{slug}/user_report_{slug_lower}.html"

        save_session_manifest(
            session.dir,
            session_id=session.id,
            slug=slug,
            slug_lower=slug_lower,
            client_name=client_name,
            dob=dob,
            birth_time=birth_time_norm,
            birth_place=place_label,
            gender=gender,
            life_events=life_events,
            client_question=client_question,
            precomputed_json=precomputed_json_path or "",
            reports_dir=client_reports_dir,
            python_confluence=py_conf_rel,
            python_user=py_user_rel,
            lane_files=lane_paths,
            today=TODAY,
            birth_latitude=chart_kw.get("latitude"),
            birth_longitude=chart_kw.get("longitude"),
            birth_timezone=chart_kw.get("timezone"),
        )

        conf_path = BASE_DIR / py_conf_rel
        user_path = BASE_DIR / py_user_rel
        if conf_path.is_file() and user_path.is_file():
            await log("✅ Python confluence + user reports ready", "success")
            for s in ["pillar", "bnn", "bhardwaj", "kp", "jaimini", "vimshottari", "yogini",
                      "ashtakavarga", "rtvd", "longevity", "blindchart", "confluence", "user"]:
                await step(s, "done")
            await session.emit_raw({"kind": "progress", "value": 100, "msg": ""})

            cursor_available = bool(find_cursor_cmd())
            if cursor_available:
                await log("✨ Optional: use 'Generate Cursor Human Report' for AI narrative + follow-up chat.", "info")
            else:
                await log("ℹ cursor-agent not in PATH — Cursor human report button disabled.", "warn")

            await session.emit_raw({
                "kind": "done",
                "success": True,
                "confluence": to_url(py_conf_rel),
                "user": to_url(py_user_rel),
                "individual": collect_python_individual_urls(),
                "client": client_name or slug,
                "cursor_available": cursor_available,
                "msg": "Python reports generated successfully.",
            })
        else:
            await log("❌ Python confluence or user report missing on disk.", "error")
            await _fallback_search(session, slug, slug_lower)

        # Legacy full Cursor 15-step pipeline (opt-in via ASTRO_RUN_CURSOR_FULL=1)
        if os.environ.get("ASTRO_RUN_CURSOR_FULL", "").strip() in ("1", "true", "yes"):
            await log("⚙️ ASTRO_RUN_CURSOR_FULL=1 — running legacy full Cursor pipeline…", "warn")
            prompt = build_prompt(
                session_id=session.id,
                extracted_txt=rel_extracted,
                palm_paths=palm_paths,
                client_name=client_name,
                dob=dob,
                gender=gender,
                slug=slug,
                slug_lower=slug_lower,
                today=TODAY,
                life_events=life_events,
                client_question=client_question,
                precomputed_json=precomputed_json_path,
                bnn_done=bool(bnn_rel),
                bhardwaj_done=bool(bhardwaj_rel),
                jaimini_done=bool(jaimini_rel),
                ashtakavarga_done=bool(ashtaka_rel),
                kp_done=bool(kp_rel),
                rtvd_done=bool(rtvd_rel),
                longevity_done=bool(longevity_rel),
                blindchart_done=bool(blindchart_rel),
                pillar_done=bool(pillar_rel),
                vimshottari_done=bool(vimshottari_rel),
                yogini_done=bool(yogini_rel),
                palm_done=bool(palmistry_rel),
                confluence_done=bool(confluence_rel and user_rel),
            )
            (session.dir / "cursor_prompt.txt").write_text(prompt, encoding="utf-8")
            if _cursor:
                done_path = str(session.dir / "DONE.json")
                ok, _ = await loop.run_in_executor(
                    None, lambda: _cursor.run(str(BASE_DIR), prompt, done_path, max_minutes=30)
                )
                if ok:
                    await log("   ✓ Legacy Cursor full pipeline finished.", "success")

    except Exception as e:
        await log(f"❌ Unexpected error: {e}", "error")
        logger.exception(e)
        await session.emit_raw({"kind": "done", "success": False, "confluence": None, "user": None, "msg": str(e)})


async def _fallback_search(session: Session, slug: str, slug_lower: str):
    """If DONE.json wasn't written, look for report files in reports/{slug}/ or reports/ root."""
    for search_dir, url_prefix in [
        (REPORTS_DIR / slug, f"/reports/{slug}"),
        (REPORTS_DIR,        "/reports"),
    ]:
        conf_path = search_dir / f"Vedic_Confluence_{slug}_{TODAY}.html"
        user_path = search_dir / f"user_report_{slug_lower}.html"
        if conf_path.exists() and user_path.exists():
            await session.emit("⚡ Found reports via fallback scan.", "success")
            # Collect any individual reports in the same folder (dedupe by filename)
            individual_urls = []
            seen_names = set()
            for pattern in (
                f"Vedic_*_{slug}_{TODAY}.html",
                f"Vedic_BlindChart_{slug}_*.html",  # any date — TODAY mismatch used to drop this lane
            ):
                for f in sorted(search_dir.glob(pattern)):
                    if f.name in seen_names:
                        continue
                    seen_names.add(f.name)
                    individual_urls.append({"name": f.stem, "url": f"{url_prefix}/{f.name}"})
            for f in sorted(search_dir.glob(f"Palmistry_{slug}_{TODAY}.html")):
                if f.name not in seen_names:
                    seen_names.add(f.name)
                    individual_urls.append({"name": f.stem, "url": f"{url_prefix}/{f.name}"})
            for f in sorted(search_dir.glob(f"Numerology_{slug}_*.html")):
                if f.name not in seen_names:
                    seen_names.add(f.name)
                    individual_urls.append({"name": f.stem, "url": f"{url_prefix}/{f.name}"})
            for f in sorted(search_dir.glob(f"Vedic_Focus_*_{slug}_{TODAY}.html")):
                if f.name not in seen_names:
                    seen_names.add(f.name)
                    individual_urls.append({"name": f.stem, "url": f"{url_prefix}/{f.name}"})
            await session.emit_raw({
                "kind": "done", "success": True,
                "confluence": f"{url_prefix}/Vedic_Confluence_{slug}_{TODAY}.html",
                "user":       f"{url_prefix}/user_report_{slug_lower}.html",
                "individual": individual_urls,
                "client":     slug,
                "cursor_available": bool(find_cursor_cmd()),
                "msg":        "Reports found."
            })
            return
    await session.emit("❌ Reports not found. Check reports/ folder manually.", "error")
    await session.emit_raw({"kind": "done", "success": False, "confluence": None, "user": None, "msg": ""})


# ──────────────────── horary prompt builder ───────────────────────────
def build_horary_prompt(
    session_id: str,
    question: str,
    q_date: str,      # YYYY-MM-DD
    q_time: str,      # HH:MM  24-hr
    location: str,
    kp_number: str,   # "1"-"249" or "" to auto-derive
    out_file: str,    # relative path like "reports/Horary_XYZ_20260408.html"
    horary_json: str = None,  # path to precomputed JSON
) -> str:
    done_path = f"_astro_sessions/{session_id}/DONE_horary.json"
    kp_note = (
        f"KP Horary Number: {kp_number}"
        if kp_number.strip()
        else "KP Horary Number: Not provided — auto-derived from question-time minutes (see precomputed JSON)"
    )

    precomputed_section = ""
    if horary_json and Path(horary_json).exists():
        precomputed_section = f"""
=== PRE-COMPUTED HORARY MATH (USE THESE VALUES — DO NOT RECALCULATE) ===
All chart math has been pre-computed by horary_precompute.py and saved to:
  {horary_json}

READ THIS FILE FIRST before doing any analysis. It contains:
  - lagna: Sidereal Lahiri Asc (sign, degree, nakshatra, star lord, sub-lord). Field **asc_source** =
    **swiss_ephemeris_sidereal_lahiri_placidus** when pyswisseph ran; else legacy fallback (note in JSON).
  - planets: All 9 grahas with sidereal sign, degree, nakshatra, star lord, sub-lord, house
  - houses: House number (1-12) for each planet (whole-sign from Lagna)
  - jamakkol: Aarudam, Udhayam, Veedhi, Kavippu (sign + house), pre-computed verdict
  - kp_data: KP number → sign, nakshatra, star lord, sub-lord (Chart A rising **rāśi** band)
  - ruling_planets: Day lord, Lagna sign/star lord, Moon sign/star lord
  - radicality: Score + flags (is the question genuine?)
  - gender_check (children / sex-of-baby topics): rāśi mnemonic scores (**boy_score** / **girl_score** out of 6),
    **navamsa_lagna**, **verse100_mixed_rasi_navamsa** (*Prashna Kundali* Verse 100 — if true, do **not** claim
    HIGH confidence from rāśi-only counts), **kp_chart_a_sign**, **verdict** (may be **Mixed / verify …**),
    **confidence**, **note**. Full classical sex read = verses 86–100 + KP **5th/11th cusp sub-lords** per **rules39.md**.
  - llm_lane_instructions: Per-system instructions (jamakkol, kp_horary, prashna_kundali, gender_check)

  CRITICAL: The llm_lane_instructions section contains ready-to-use analysis text for each system.
  READ it and incorporate those values directly into the report sections.
  DO NOT re-derive Lagna, Aarudam, Kavippu, or KP sign from scratch — use the pre-computed values.
"""
    else:
        precomputed_section = f"""
=== CHART CALCULATION (no pre-computed JSON available) ===
Run **horary_precompute.py** (same question, date, time, location, KP#) when possible — it uses **Swiss Ephemeris**
sidereal Lahiri Asc when pyswisseph is installed. Otherwise follow **horary_prashna_skill.md** § C0 / § C1
(Jamakkol Udhayam Method 1 vs 2; do not mix formulas).
"""

    return f"""You are an expert horary / prashna astrologer.

READ THE SKILL FILE FIRST:
  horary_prashna_skill.md  (also at .cursor/skills/horary-prashna/SKILL.md)
{precomputed_section}
=== QUESTION DETAILS ===
Question   : {question}
Date       : {q_date}
Time       : {q_time} (24-hour, local IST unless stated otherwise)
Location   : {location}
{kp_note}

=== OUTPUT ===
Generate ONE comprehensive HTML report saved to:
  {out_file}

The report MUST look like the reference:
  reports/Horary_ChildSpeech_20260407.html
It must include (in order):
1. Hero banner — question + verdict badge (YES / LIKELY / UNCERTAIN / UNLIKELY / NO) + confidence
2. Chart snapshot — Lagna, planet positions table, special markers
3. Radicality check — is the question genuine? (§ H in skill)
4. System 1 — Jamakkol Prasanam analysis (Aarudam, Udhayam, Kavippu, Jamam)
5. System 2 — KP Horary analysis (significators, Ruling Planets, sub-lord)
6. System 3 — Prashna Kundali Siddhanta analysis
7. Confluence verdict — 3-system vote table, final answer, confidence level
8. If **gender_check** is present: show **navamsa_lagna**, Verse 100 mixed flag, **kp_chart_a_sign**, and scores;
   if verdict is **Mixed / verify**, state that **rāśi-only** tallies are insufficient (skill §C0d, rules39).
9. Timing windows — when and under what conditions the answer manifests
10. Remedies — specific to the question topic
11. Disclaimer

Dark-theme HTML with CSS variables — no external CDN dependencies.

=== DONE SIGNAL ===
After writing the report, write exactly:
  {done_path}
Content (valid JSON):
{{
  "report": "{out_file}",
  "question": "{question[:80]}",
  "verdict": "<YES|LIKELY|UNCERTAIN|UNLIKELY|NO>",
  "confidence": "<HIGH|MODERATE|LOW>",
  "generated": "{q_date}"
}}
"""


def western_horary_out_file(question: str, q_date: str) -> str:
    """Same slug stem as Vedic Horary_*.html but WesternHorary_ prefix."""
    stem = horary_question_slug(question, q_date).replace("Horary_", "WesternHorary_", 1)
    return f"reports/{stem}.html"


def build_western_horary_prompt(
    session_id: str,
    question: str,
    q_date: str,
    q_time: str,
    location: str,
    out_file: str,
    western_json: Optional[str],
) -> str:
    done_path = f"_astro_sessions/{session_id}/DONE_western_horary.json"
    if western_json and Path(western_json).exists():
        precomputed_section = f"""
=== PRE-COMPUTED WESTERN HORARY (TROPICAL PLACIDUS — USE THESE; DO NOT USE SIDEREAL / VEDIC) ===
Computed by western_horary_precompute.py (Swiss Ephemeris MOSEPH when installed). Read this file first:
  {western_json}

It contains: meta (UTC hint, lat/lon, chart_type day/night, house system), angles, Placidus cusps, planets with houses & speeds, llm_instructions.

Follow **.cursor/skills/western-horary/SKILL.md §2b** (Louis Chapter 2 checklist — void Moon, perfection, Asc vs 11th lord, etc.).
Procedure reference: **rules43.md**

**THIS REPORT IS WESTERN TRADITIONAL HORARY ONLY.**
Do NOT include KP, Jamakkol, Prashna Kundali, nakṣatras, or any Vedic technique in this HTML.
"""
    else:
        precomputed_section = """
=== NO PRE-COMPUTED WESTERN JSON ===
Use western-horary SKILL §5: WebSearch/WebFetch **Tropical** positions for the judgment instant and coordinates.
Still complete §2b checklist and rules43.md. Western-only — no Vedic.
"""

    return f"""You are an expert Western traditional horary astrologer (Lilly / Louis lineage).

READ FIRST:
  .cursor/skills/western-horary/SKILL.md  (especially §2b)
  rules43.md
{precomputed_section}
=== QUESTION (verbatim) ===
{question}

=== JUDGMENT TIME (app convention) ===
Date: {q_date}
Time: {q_time} (24h, IST — same as precompute when JSON exists)
Place: {location}

=== OUTPUT ===
1. Copy `reports/WesternHorary_template.html` to:
   {out_file}
2. Fill the template with your **Western-only** analysis per §2b. Remove author-only instruction boxes.
3. Self-contained HTML/CSS (no external CDN). Verdict badge in the report must match your conclusion.

=== DONE SIGNAL ===
After writing the report, write exactly:
  {done_path}
Content (valid JSON):
{{
  "report": "{out_file}",
  "question": "{question[:80]}",
  "verdict": "<YES|LIKELY|UNCERTAIN|UNLIKELY|NO>",
  "confidence": "<HIGH|MODERATE|LOW>",
  "generated": "{q_date}"
}}
"""


def horary_question_slug(question: str, q_date: str) -> str:
    """Convert question to a file-safe slug: 'when will child speak' → 'Horary_WhenChildSpeak_20260408'"""
    stop = {"will","when","how","what","is","are","the","my","a","an","to","for","of","in","i","do"}
    words = [w.capitalize() for w in re.sub(r"[^a-z0-9 ]", "", question.lower()).split()
             if w not in stop][:4]
    slug_part = "".join(words) or "Question"
    date_part = q_date.replace("-", "")
    return f"Horary_{slug_part}_{date_part}"


# ─────────────────── horary endpoint + background task ────────────────
@app.post("/horary")
async def horary(
    session_id: str = Form(...),
    question:   str = Form(...),
    q_date:     str = Form(...),
    q_time:     str = Form(...),
    location:   str = Form("New Delhi, India"),
    kp_number:  str = Form(""),
):
    if not question.strip():
        raise HTTPException(400, "Question cannot be empty.")
    session = get_session(session_id)
    asyncio.create_task(_run_horary(session, question.strip(), q_date.strip(),
                                    q_time.strip(), location.strip(), kp_number.strip()))
    return JSONResponse({"status": "queued"})


async def _run_horary(
    session: Session,
    question: str,
    q_date: str,
    q_time: str,
    location: str,
    kp_number: str,
):
    loop = asyncio.get_running_loop()

    async def log(msg: str, kind: str = "info"):
        await session.emit(f"[Horary] {msg}", kind)

    try:
        await log(f"🔮 Question received: {question[:60]}…" if len(question) > 60 else f"🔮 Question: {question}")
        await log(f"   📅 {q_date} {q_time} | 📍 {location}" + (f" | KP# {kp_number}" if kp_number else ""))

        # Determine output file
        q_slug = horary_question_slug(question, q_date)
        out_file = f"reports/{q_slug}.html"
        done_path = str(session.dir / "DONE_horary.json")

        # Remove stale DONE files if re-running
        for _done_name in ("DONE_horary.json", "DONE_western_horary.json"):
            _dp = session.dir / _done_name
            if _dp.exists():
                _dp.unlink()

        # ── Pre-compute Vedic horary math ─────────────────────────────
        horary_json_path = str(session.dir / "horary_precomputed.json")
        await log("🔢 Pre-computing Vedic horary chart math…")
        try:
            precompute_result = subprocess.run(
                [sys.executable, str(BASE_DIR / "horary_precompute.py"),
                 question, q_date, q_time, location, kp_number or "", horary_json_path],
                capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30
            )
            if precompute_result.returncode == 0:
                for ln in (precompute_result.stdout or "").splitlines()[:5]:
                    if ln.strip():
                        await log(f"   {ln.strip()}")
                await log(f"   ✓ Vedic pre-compute saved: {Path(horary_json_path).name}")
            else:
                await log(f"   ⚠ Vedic pre-compute warning: {(precompute_result.stderr or '')[:200]}", "warn")
                horary_json_path = None
        except Exception as e:
            await log(f"   ⚠ Vedic pre-compute skipped: {e}", "warn")
            horary_json_path = None

        # ── Pre-compute Western (Tropical Placidus) ───────────────────
        western_json_path = str(session.dir / "western_horary_precomputed.json")
        await log("🔢 Pre-computing Western Tropical horary…")
        try:
            western_pc = subprocess.run(
                [sys.executable, str(BASE_DIR / "western_horary_precompute.py"),
                 question, q_date, q_time, location, western_json_path],
                capture_output=True, text=True, cwd=str(BASE_DIR), timeout=30
            )
            if western_pc.returncode == 0:
                for ln in (western_pc.stdout or "").splitlines()[:5]:
                    if ln.strip():
                        await log(f"   [Western] {ln.strip()}")
                await log(f"   ✓ Western pre-compute saved: {Path(western_json_path).name}")
            else:
                await log(f"   ⚠ Western pre-compute warning: {(western_pc.stderr or '')[:200]}", "warn")
                western_json_path = None
        except Exception as e:
            await log(f"   ⚠ Western pre-compute skipped: {e}", "warn")
            western_json_path = None

        western_out_file = western_horary_out_file(question, q_date)
        western_stem = Path(western_out_file).stem

        # ── Lane 1: Vedic horary — deterministic Python (no LLM) ──────
        await session.emit_raw({"kind": "horary_progress", "value": 10, "msg": ""})
        await log("⚙️ Vedic horary — deterministic KP · Jamakkol · Prashna engine (no LLM)…")

        vedic_report_url: Optional[str] = None
        vedic_verdict, vedic_conf = "", ""
        vedic_ok = False

        def run_vedic_horary():
            html_doc, jv = generate_vedic_horary_html(question, q_date, q_time, location, kp_number)
            out_abs = BASE_DIR / out_file
            out_abs.parent.mkdir(parents=True, exist_ok=True)
            out_abs.write_text(finalize_report_html(html_doc), encoding="utf-8")
            return jv

        try:
            jv = await loop.run_in_executor(None, run_vedic_horary)
            vedic_ok = True
            vedic_report_url = f"/{Path(out_file).as_posix().lstrip('/')}"
            vedic_verdict = jv.get("verdict", "") or ""
            vedic_conf = jv.get("confidence", "") or ""
            sysmap = jv.get("systems", {})
            await log(f"   Jamakkol={sysmap.get('jamakkol','?')} · Prashna={sysmap.get('prashna','?')} · KP={sysmap.get('kp','?')}")
            await log(f"✅ Vedic horary — {vedic_verdict} ({vedic_conf})", "success")
        except Exception as ve:
            await log(f"❌ Vedic horary engine error: {ve}", "error")
            logger.exception(ve)
            fb = _fallback_vedic_horary_url(q_slug)
            if fb:
                vedic_ok = True
                vedic_report_url = fb
                await session.emit("[Horary] ⚡ Vedic report found via fallback scan.", "success")

        # ── Lane 2: Western horary — deterministic Python (no LLM) ───
        await session.emit_raw({"kind": "horary_progress", "value": 55, "msg": ""})
        await log("⚙️ Western horary — deterministic Lilly/Louis engine (no LLM)…")

        western_report_url: Optional[str] = None
        western_verdict, western_conf = "", ""
        western_ok = False

        def run_western_horary():
            html, j = generate_western_horary_html(question, q_date, q_time, location)
            out_abs = BASE_DIR / western_out_file
            out_abs.parent.mkdir(parents=True, exist_ok=True)
            out_abs.write_text(finalize_report_html(html), encoding="utf-8")
            return j

        try:
            j_w = await loop.run_in_executor(None, run_western_horary)
            western_ok = True
            western_report_url = f"/{Path(western_out_file).as_posix().lstrip('/')}"
            western_verdict = j_w.get("verdict", "") or ""
            western_conf = j_w.get("confidence", "") or ""
            await log(f"✅ Western horary — {western_verdict} ({western_conf})", "success")
        except Exception as we:
            await log(f"❌ Western horary engine error: {we}", "error")
            fbw = _fallback_western_horary_url(western_stem)
            if fbw:
                western_ok = True
                western_report_url = fbw
                await session.emit("[Horary] ⚡ Western report found via fallback scan.", "success")

        overall = vedic_ok or western_ok
        parts = []
        parts.append(f"Vedic: {vedic_verdict or 'ok'}" if vedic_ok else "Vedic: failed")
        parts.append(f"Western: {western_verdict or 'ok'}" if western_ok else "Western: failed")
        await session.emit_raw({
            "kind": "horary_done",
            "success": overall,
            "report": vedic_report_url,
            "verdict": vedic_verdict,
            "confidence": vedic_conf,
            "western_report": western_report_url,
            "western_verdict": western_verdict,
            "western_confidence": western_conf,
            "vedic_success": vedic_ok,
            "western_success": western_ok,
            "question": question[:80],
            "msg": " · ".join(parts),
        })
        if not overall:
            await session.emit("[Horary] ❌ Neither report found. Check reports/ and session folder.", "error")

    except Exception as e:
        await log(f"❌ Unexpected error: {e}", "error")
        logger.exception(e)
        await session.emit_raw({
            "kind": "horary_done",
            "success": False,
            "report": None,
            "verdict": "",
            "confidence": "",
            "western_report": None,
            "western_verdict": "",
            "western_confidence": "",
            "vedic_success": False,
            "western_success": False,
            "question": question[:80],
            "msg": str(e),
        })


def _fallback_vedic_horary_url(q_slug: str) -> Optional[str]:
    candidates = list(REPORTS_DIR.glob(f"{q_slug}*.html"))
    if not candidates:
        candidates = list(REPORTS_DIR.glob(f"Horary_*{TODAY}*.html"))
    if not candidates:
        return None
    rel = candidates[-1].relative_to(BASE_DIR)
    return f"/{rel.as_posix()}"


def _fallback_western_horary_url(western_stem: str) -> Optional[str]:
    candidates = list(REPORTS_DIR.glob(f"{western_stem}*.html"))
    if not candidates:
        candidates = list(REPORTS_DIR.glob(f"WesternHorary_*{TODAY}*.html"))
    if not candidates:
        return None
    rel = candidates[-1].relative_to(BASE_DIR)
    return f"/{rel.as_posix()}"


@app.get("/download/report/{path:path}")
async def download_report(path: str):
    """Force-download any report file (supports subfolder paths like Ritz/file.html)."""
    full_path = REPORTS_DIR / path
    # Security: ensure it stays inside REPORTS_DIR
    try:
        full_path.resolve().relative_to(REPORTS_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied.")
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(404, "Report not found.")
    return FileResponse(
        str(full_path), media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{full_path.name}"'}
    )


# ─────────────────────── entry point ──────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("ASTRO_PORT", "8091"))
    _urls = get_server_urls(port)
    print(f"\n{'='*60}")
    print(f"  ✦ Vedic Astrology Report Generator")
    print(f"  Local  :  {_urls['local']}")
    print(f"  Network:  {_urls['lan']}")
    if _urls.get("public"):
        print(f"  Universal (Wi-Fi + mobile data):  {_urls['public']}")
    else:
        print(f"  Universal:  NOT SET — set ASTRO_PUBLIC_URL or run ./scripts/run_with_ngrok.sh")
        print(f"              Production:  frontend/backend/deploy/setup-universal-server.sh")
    print()
    print(f"  HOW TO USE:")
    print(f"  1. Enter client name, DOB, time of birth, and place (pick from dropdown)")
    print(f"  2. Upload palm photos (optional but recommended)")
    print(f"  3. Add known life events for calibration (strongly recommended)")
    print(f"  4. Press 'Generate Reports' — Python lanes finish in ~1–3 minutes")
    print(f"  5. Optional: click 'Generate Cursor Human Report' for AI narrative (10–20 min)")
    print(f"  6. Use 'Follow-up with Cursor' for chart-grounded Q&A after human report")
    print()
    print(f"  OUTPUT:")
    print(f"  • Confluence report (technical, all systems, vote table)")
    print(f"  • User report (plain English, dates, traffic lights)")
    print(f"  • Individual lane reports saved in reports/ but not shown")
    print()
    print(f"  Cursor CLI: {'FOUND — ' + _cursor.cmd if _cursor else 'NOT FOUND — install cursor-agent'}")
    print(f"  Workspace: {BASE_DIR}")
    print(f"  Reports  : {REPORTS_DIR}")
    print(f"{'='*60}\n")

    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")
