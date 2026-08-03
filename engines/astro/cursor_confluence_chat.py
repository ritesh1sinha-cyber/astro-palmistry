#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cursor CLI human-style confluence + follow-up chat with session memory."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

BASE_DIR = Path(__file__).resolve().parent

CURSOR_HUMAN_RULES = """\
=== CURSOR HUMAN CONFLUENCE - STRICT RULES ===

You are an expert Vedic astrologer writing INSIDE the test8 workspace.
Python has ALREADY generated deterministic lane HTML + a semantic confluence + user report.
Your job: write a WARMER, more human, client-ready pair of reports that STAYS FAITHFUL to the data.

READ FIRST (mandatory):
  .cursor/skills/vedic-confluence/SKILL.md
  .cursor/skills/vedic-report-prediction/SKILL.md
  vedic_confluence_skill.md (Part 8 user hub layout)

ANTI-HALLUCINATION (blocking):
  1. Every factual claim MUST trace to: precomputed JSON, a lane HTML file, or Python user/confluence HTML.
  2. Book technique ONLY from rules*.md / book_ocr via skills - never from memory or generic astrology.
  3. If a lane is missing, say [SKIPPED: LaneName - reason] - do NOT invent placements or dates.
  4. Do NOT paste generic horoscope filler. If you cannot cite a chart fact, omit the sentence.
  5. Do NOT please the client with optimistic guesses. If lanes disagree or are silent, say so plainly.
  6. When evidence is weak: write "Unclear from available data" or "No" - not a soft maybe.
  7. Use gender-neutral "spouse" / "partner" - never wife/husband in client text.
  8. NO Sanskrit diacritics in HTML (use ASCII: Mahadasha, Vimshottari, Nakshatra, etc.).
  9. NO emoji in HTML (use text labels or simple symbols).
  10. Do NOT regenerate individual lane reports - they are final inputs.

OUTPUT FILES (write both before DONE signal):
  1) {cursor_confluence_path}
     - Human-readable multi-system synthesis; vote table; dated windows; remedies.
     - Improve readability over Python confluence; do not contradict lane facts.
  2) {cursor_user_path}
     - Plain-English client hub per vedic_confluence_skill.md Part 8.
     - Opening like a trusted astrologer talking to the client; traffic lights; past chapters.

REFERENCE (read, do not blindly copy):
  Python confluence: {python_confluence}
  Python user hub:   {python_user}

BIRTH DATA:
  Name: {client_name} | DOB: {dob} | Time: {birth_time} | Place: {birth_place} | Gender: {gender}

PRECOMPUTED CHART JSON (source of truth for planets, dasha, meta):
  {precomputed_json}

LANE HTML FILES (read each relevant file before writing):
{lane_list}

LIFE EVENTS (calibration - if empty, mark UNCALIBRATED in header):
{life_events}

CLIENT FOCUS QUESTION (if any - answer in user report opening):
{client_question}

DONE SIGNAL - write ONLY after BOTH HTML files exist on disk:
  {done_path}

Exact JSON:
{{
  "success": true,
  "cursor_confluence": "{cursor_confluence_rel}",
  "cursor_user": "{cursor_user_rel}",
  "client": "{slug}",
  "msg": "Cursor human reports ready."
}}
=== END RULES ===
"""


CURSOR_CHAT_GROUNDING = """\
=== FOLLOW-UP ANSWER - STRICT GROUNDING (BLOCKING) ===

ALLOWED SOURCES ONLY:
  1. Precomputed chart JSON (path below) - planets, houses, dasha dates, meta
  2. Lane HTML files listed in this session manifest - read before answering
  3. Python + Cursor human confluence/user HTML if present
  4. Book OCR / rules*.md ONLY through skills:
     .cursor/skills/vedic-confluence/SKILL.md
     .cursor/skills/vedic-report-prediction/SKILL.md
     (and lane-specific skills when the question needs them)

FORBIDDEN:
  - Pop astrology, sun-sign generalities, or facts not in the files above
  - Invented placements, dasha windows, significators, or life events
  - Soothing the client with a positive answer when data does not support it
  - Hedging with vague encouragement when the honest answer is No or Unclear

WHEN DATA DOES NOT MATCH THE QUESTION:
  - Say plainly at the start: "No - the chart data does not show [X]."
  - Or: "Unclear - lanes disagree or are silent on [X]."
  - Or: "Unlikely - only weak/indirect signals; no strong lane support."
  - Then cite what WAS checked (lane + fact). Do NOT invent missing support.

WHEN LANES CONFLICT:
  - Name the conflict. Do not merge into a single pleasing story.
  - Default to lower confidence, not a confident Yes.

ANSWER SHAPE:
  - Line 1: direct verdict (Yes / No / Unlikely / Unclear) in plain English
  - Then 2-5 short paragraphs, each tied to a cited lane fact or dated period
  - No "Question:" header (UI shows the question). No emoji. Gender-neutral spouse wording.
"""


class CursorChatMemory:
    """Session chat history - LangChain buffer if installed, else JSON file."""

    def __init__(self, path: Path):
        self.path = path
        self._lc_memory = None
        try:
            from langchain.memory import ConversationBufferMemory  # type: ignore

            self._lc_memory = ConversationBufferMemory(return_messages=False)
            if self.path.is_file():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for turn in data.get("turns", []):
                    if turn.get("human"):
                        self._lc_memory.chat_memory.add_user_message(turn["human"])
                    if turn.get("ai"):
                        self._lc_memory.chat_memory.add_ai_message(turn["ai"])
        except Exception:
            self._lc_memory = None

    def _load(self) -> dict:
        if not self.path.is_file():
            return {"turns": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"turns": []}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_turn(self, human: str, ai: str) -> None:
        data = self._load()
        data.setdefault("turns", []).append({
            "human": human,
            "ai": ai,
            "ts": datetime.now().isoformat(timespec="seconds"),
        })
        if len(data["turns"]) > 20:
            data["turns"] = data["turns"][-20:]
        self._save(data)
        if self._lc_memory:
            self._lc_memory.chat_memory.add_user_message(human)
            self._lc_memory.chat_memory.add_ai_message(ai)

    def get_turns(self, max_turns: int = 20) -> list[dict]:
        return self._load().get("turns", [])[-max_turns:]

    def format_history(self, max_turns: int = 8) -> str:
        if self._lc_memory:
            try:
                return self._lc_memory.load_memory_variables({}).get("history", "")
            except Exception:
                pass
        turns = self.get_turns(max_turns)
        if not turns:
            return "(no prior conversation)"
        lines = []
        for t in turns:
            lines.append(f"Client: {t.get('human', '')}")
            lines.append(f"You: {t.get('ai', '')}")
        return "\n".join(lines)


def find_cursor_cmd() -> Optional[str]:
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
    ):
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None


def send_cursor_prompt(cwd: str, prompt: str, cmd: Optional[str] = None) -> bool:
    cmd = cmd or find_cursor_cmd()
    if not cmd:
        return False
    import tempfile

    fd, prompt_path = tempfile.mkstemp(suffix=".txt", prefix="cursor_human_", text=True)
    fh = None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(prompt)
        fh = open(prompt_path, "r", encoding="utf-8")
        proc = subprocess.Popen(
            [cmd, "-p", "--yolo", "--trust", "--workspace", cwd],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=fh,
            text=True,
            encoding="utf-8",
            cwd=cwd,
        )
        if proc.stdout:
            for _ in proc.stdout:
                pass
        proc.wait()
        return proc.returncode == 0
    except Exception:
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


def wait_for_json(done_path: Path, max_minutes: int = 25) -> Optional[dict]:
    deadline = time.time() + max_minutes * 60
    while time.time() < deadline:
        if done_path.is_file():
            try:
                return json.loads(done_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        time.sleep(6)
    return None


def collect_lane_files(reports_dir: Path, slug: str, today: str) -> list[Path]:
    patterns = (
        f"Vedic_*_{slug}_{today}.html",
        f"Vedic_*_{slug}_*.html",
        f"Palmistry_{slug}_*.html",
        f"Numerology_{slug}_*.html",
        f"Remedy_Gemstone_{slug}_*.html",
        f"user_report_{slug.lower()}.html",
    )
    found: list[Path] = []
    seen: set[str] = set()
    for pat in patterns:
        for p in sorted(reports_dir.glob(pat)):
            if p.name.startswith("Cursor_"):
                continue
            if p.name not in seen and p.is_file():
                seen.add(p.name)
                found.append(p)
    return found


def save_session_manifest(
    session_dir: Path,
    *,
    session_id: str,
    slug: str,
    slug_lower: str,
    client_name: str,
    dob: str,
    birth_time: str,
    birth_place: str,
    gender: str,
    life_events: str,
    client_question: str,
    precomputed_json: str,
    reports_dir: Path,
    python_confluence: str,
    python_user: str,
    lane_files: list[str],
    today: str,
    birth_latitude: float | None = None,
    birth_longitude: float | None = None,
    birth_timezone: float | None = None,
) -> Path:
    manifest = {
        "session_id": session_id,
        "slug": slug,
        "slug_lower": slug_lower,
        "client_name": client_name,
        "dob": dob,
        "birth_time": birth_time,
        "birth_place": birth_place,
        "gender": gender,
        "life_events": life_events,
        "client_question": client_question,
        "precomputed_json": precomputed_json,
        "reports_dir": str(reports_dir.relative_to(BASE_DIR)).replace("\\", "/"),
        "python_confluence": python_confluence,
        "python_user": python_user,
        "lane_files": lane_files,
        "today": today,
        "cursor_confluence_out": f"reports/{slug}/Cursor_Confluence_{slug}_{today}.html",
        "cursor_user_out": f"reports/{slug}/cursor_user_report_{slug_lower}.html",
    }
    if birth_latitude is not None:
        manifest["birth_latitude"] = birth_latitude
    if birth_longitude is not None:
        manifest["birth_longitude"] = birth_longitude
    if birth_timezone is not None:
        manifest["birth_timezone"] = birth_timezone
    path = session_dir / "session_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_session_manifest(session_dir: Path) -> dict:
    path = session_dir / "session_manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"Session manifest missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_cursor_human_prompt(manifest: dict, session_dir: Path) -> str:
    slug = manifest["slug"]
    done_path = session_dir / "DONE_cursor_human.json"
    lane_lines = "\n".join(f"  - {p}" for p in manifest.get("lane_files", []))
    return CURSOR_HUMAN_RULES.format(
        cursor_confluence_path=manifest["cursor_confluence_out"],
        cursor_user_path=manifest["cursor_user_out"],
        python_confluence=manifest.get("python_confluence", ""),
        python_user=manifest.get("python_user", ""),
        client_name=manifest.get("client_name", slug),
        dob=manifest.get("dob", ""),
        birth_time=manifest.get("birth_time", ""),
        birth_place=manifest.get("birth_place", ""),
        gender=manifest.get("gender", ""),
        precomputed_json=manifest.get("precomputed_json", ""),
        lane_list=lane_lines or "  (none listed)",
        life_events=manifest.get("life_events", "") or "(none - mark UNCALIBRATED)",
        client_question=manifest.get("client_question", "") or "(none)",
        done_path=str(done_path.relative_to(BASE_DIR)).replace("\\", "/"),
        cursor_confluence_rel=manifest["cursor_confluence_out"],
        cursor_user_rel=manifest["cursor_user_out"],
        slug=slug,
    )


def build_cursor_chat_prompt(manifest: dict, memory: CursorChatMemory, question: str) -> str:
    lane_lines = "\n".join(f"  - {p}" for p in manifest.get("lane_files", []))
    return f"""{CURSOR_CHAT_GROUNDING}

You are continuing a consultation for {manifest.get('client_name', manifest['slug'])}.

BIRTH: {manifest.get('dob', '')} {manifest.get('birth_time', '')} | {manifest.get('birth_place', '')} | {manifest.get('gender', '')}

PRECOMPUTED CHART JSON (read this file first):
  {manifest.get('precomputed_json', '')}

LANE HTML (read relevant files before answering - do not guess):
{lane_lines or '  (none listed)'}

PYTHON REPORTS:
  {manifest.get('python_confluence', '')}
  {manifest.get('python_user', '')}

CURSOR HUMAN REPORTS (if they exist on disk):
  {manifest.get('cursor_confluence_out', '')}
  {manifest.get('cursor_user_out', '')}

PRIOR CONVERSATION:
{memory.format_history()}

CLIENT FOLLOW-UP QUESTION:
{question.strip()}

Write your full answer to:
  {manifest.get('reports_dir', '')}/cursor_chat_latest.txt
(one plain-text file, overwrite each time)

Then write:
  _astro_sessions/{manifest['session_id']}/DONE_cursor_chat.json
with: {{"success": true, "answer_file": "<relative path to cursor_chat_latest.txt>"}}
"""


def run_cursor_human_report(
    manifest: dict,
    session_dir: Path,
    *,
    log: Callable[[str], None] | None = None,
    max_minutes: int = 25,
) -> tuple[bool, dict]:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    cmd = find_cursor_cmd()
    if not cmd:
        return False, {"error": "cursor-agent not found in PATH"}

    prompt = build_cursor_human_prompt(manifest, session_dir)
    (session_dir / "cursor_human_prompt.txt").write_text(prompt, encoding="utf-8")
    done_path = session_dir / "DONE_cursor_human.json"
    if done_path.is_file():
        done_path.unlink()

    _log("Starting Cursor CLI for human-style confluence + user report...")
    send_cursor_prompt(str(BASE_DIR), prompt, cmd)
    result = wait_for_json(done_path, max_minutes=max_minutes)
    if not result:
        conf = BASE_DIR / manifest["cursor_confluence_out"]
        user = BASE_DIR / manifest["cursor_user_out"]
        if conf.is_file() and user.is_file():
            return True, {
                "success": True,
                "cursor_confluence": manifest["cursor_confluence_out"],
                "cursor_user": manifest["cursor_user_out"],
                "client": manifest["slug"],
                "msg": "Cursor human reports found on disk.",
            }
        return False, {"error": "Cursor timed out or did not write DONE_cursor_human.json"}

    return bool(result.get("success")), result


def run_cursor_chat(
    manifest: dict,
    session_dir: Path,
    question: str,
    memory: CursorChatMemory,
    *,
    max_minutes: int = 10,
) -> tuple[bool, str]:
    cmd = find_cursor_cmd()
    if not cmd:
        return False, "cursor-agent not found in PATH"

    prompt = build_cursor_chat_prompt(manifest, memory, question)
    (session_dir / "cursor_chat_prompt.txt").write_text(prompt, encoding="utf-8")
    done_path = session_dir / "DONE_cursor_chat.json"
    if done_path.is_file():
        done_path.unlink()

    send_cursor_prompt(str(BASE_DIR), prompt, cmd)
    result = wait_for_json(done_path, max_minutes=max_minutes)

    answer = ""
    reports_dir = BASE_DIR / manifest.get("reports_dir", "")
    latest = reports_dir / "cursor_chat_latest.txt"
    if latest.is_file():
        answer = latest.read_text(encoding="utf-8", errors="replace").strip()

    if not answer and result:
        rel = result.get("answer_file", "")
        if rel:
            p = BASE_DIR / rel
            if p.is_file():
                answer = p.read_text(encoding="utf-8", errors="replace").strip()

    if answer:
        memory.add_turn(question, answer)
        return True, answer
    return False, "Cursor did not return an answer. Check session logs."
