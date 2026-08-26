"""Plain-English executive summary for finished customer reports.

Runs as the last pass after the final HTML is assembled. The LLM reads the
visible report text (what the customer sees) and returns short, jargon-free
sections. When the LLM is off or fails QA, a deterministic fallback is built
from meta/facts so the Summary button still works.
"""

from __future__ import annotations

import hashlib
import json
import re
from html.parser import HTMLParser
from typing import Any, Optional

from .rules import system_prompt_for
from .schemas import PlainSummaryProse

_MAX_INPUT_CHARS = 14000
_SKIP_CLASS_RE = re.compile(
    r"\b(blurred|lock-blur|lock-over|lock-wrap|locked-preview|fine)\b", re.I
)


class _ReportText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0
        self._raw = 0

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t in ("script", "style", "nav"):
            self._raw += 1
            return
        cls = ""
        for k, v in attrs:
            if k.lower() == "class":
                cls = str(v or "")
                break
        if _SKIP_CLASS_RE.search(cls):
            self._skip += 1

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("script", "style", "nav") and self._raw:
            self._raw -= 1
        if self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if self._raw or self._skip:
            return
        text = re.sub(r"\s+", " ", str(data or "")).strip()
        if text:
            self.parts.append(text)


def html_to_report_text(html: str) -> str:
    """Extract customer-visible prose from rendered report HTML."""
    p = _ReportText()
    try:
        p.feed(html or "")
        p.close()
    except Exception:  # noqa: BLE001
        return re.sub(r"<[^>]+>", " ", html or "")
    out = " ".join(p.parts)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out[:_MAX_INPUT_CHARS]


def _enabled() -> bool:
    try:
        from core.config import S
        return bool(S.llm_tab_enabled("summary"))
    except Exception:  # noqa: BLE001
        return False


def _complete(prose_schema, system: str, user: str):
    try:
        from core.llm_client import complete_model
        return complete_model(prose_schema, system, user, temperature=0.35)
    except Exception:  # noqa: BLE001
        return None


def _validate(prose: PlainSummaryProse, source: str) -> list[str]:
    errors: list[str] = []
    blob = " ".join(f"{s.title} {s.body}" for s in prose.sections).lower()
    if not prose.sections:
        errors.append("empty_sections")
    for bad in (
        "minilm", "pyjhora", "confluence_score", "facts_hash", "schema_version",
        "internal rule", "deterministic engine", "[placeholder", "pending llm",
    ):
        if bad in blob:
            errors.append(f"leak:{bad}")
    # Dates in summary should appear in source text (rough guard).
    for m in re.finditer(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+20\d{2}\b",
        blob,
        re.I,
    ):
        if m.group(0) not in source and m.group(0).title() not in source:
            errors.append(f"ungrounded_date:{m.group(0)}")
    return errors


def _kind_label(kind: str) -> str:
    return {
        "full_report": "full birth-chart confluence reading",
        "classical_report": "classical Vedic reading",
        "horary": "horary question reading",
        "user_question": "natal-chart question reading",
        "palm": "palmistry reading",
        "daily": "daily personal reading",
        "numerology": "numerology reading",
        "kundali_match": "kundali compatibility reading",
        "muhurat": "muhurat day check",
        "btr": "birth-time rectification reading",
    }.get(kind or "", "astrology reading")


def _fallback_from_report_text(text: str, *, max_sections: int = 5) -> list[dict]:
    """Multi-section fallback when the LLM is off — split visible report prose."""
    text = re.sub(r"\s{2,}", " ", (text or "").strip())
    if len(text) < 280:
        return []
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
        if len(s.strip()) > 24
    ]
    if len(sentences) < 2:
        return []
    titles = (
        "The direct answer", "The current phase", "What opens next",
        "Health and energy", "Gemstones and actions", "What to do today",
    )
    per = max(2, min(4, (len(sentences) + max_sections - 1) // max_sections))
    sections: list[dict] = []
    idx = 0
    for title in titles:
        if idx >= len(sentences) or len(sections) >= max_sections:
            break
        chunk = sentences[idx:idx + per]
        idx += per
        if chunk:
            sections.append({"title": title, "body": " ".join(chunk)[:900]})
    return sections


def _fallback_sections(kind: str, meta: dict, facts: Any, text: str) -> list[dict]:
    meta = meta or {}
    sections: list[dict] = []

    if kind in ("full_report", "classical_report"):
        ans = meta.get("answer") or {}
        if isinstance(ans, dict) and ans.get("label"):
            sections.append({
                "title": "Overall direction",
                "body": str(ans.get("label") or "")[:900],
            })
        teaser = str(meta.get("teaser") or "").strip()
        if teaser:
            sections.append({"title": "What matters now", "body": teaser[:900]})

    elif kind == "horary":
        text_sections = _fallback_from_report_text(text)
        if text_sections:
            sections.extend(text_sections)
        if not sections:
            ans = meta.get("answer") or {}
            q = str(meta.get("question") or "").strip()
            label = str(ans.get("label") or "Open").strip()
            conf = str(ans.get("confidence") or "moderate").strip()
            body = f"On your question{(' — ' + q) if q else ''}, the chart reads as {label} ({conf} confidence)."
            sections.append({"title": "The answer", "body": body[:900]})

    elif kind == "user_question":
        q = str(meta.get("question") or meta.get("area") or "").strip()
        sections = _fallback_from_report_text(text)
        if not sections:
            ans = meta.get("answer") or {}
            label = str(ans.get("label") or ans.get("direction") or "mixed").strip()
            bt = str(ans.get("breakthrough") or "").strip()
            low = label.lower()
            if low.startswith(("the chart", "your chart", "regarding", "on your question")):
                body = label
            elif q:
                body = f"On your question about {q}, the chart leans {label}."
            else:
                body = f"Regarding your question, the chart leans {label}."
            if bt:
                body += f" The strongest opening sits around {bt}."
            sections.append({"title": "Direct answer", "body": body[:900]})

    elif kind == "daily":
        teaser = str(meta.get("teaser") or "").strip()
        if teaser:
            sections.append({"title": "Today in plain terms", "body": teaser[:900]})

    elif kind == "palm":
        text_sections = _fallback_from_report_text(text)
        if text_sections:
            sections.extend(text_sections)
        if not sections:
            summary = str(meta.get("summary") or meta.get("teaser") or "").strip()
            if summary:
                sections.append({"title": "Both hands together", "body": summary[:900]})

    elif kind == "numerology":
        text_sections = _fallback_from_report_text(text)
        if text_sections:
            sections.extend(text_sections)
        if not sections:
            teaser = str(meta.get("teaser") or "").strip()
            if teaser:
                sections.append({"title": "Your numbers today", "body": teaser[:900]})

    elif kind == "kundali_match":
        headline = str(meta.get("headline") or meta.get("verdict") or "").strip()
        total = meta.get("total")
        if headline or total is not None:
            guna = f"{total}/{meta.get('maxGuna') or 36} guna" if total is not None else ""
            body = ". ".join(x for x in (headline, guna) if x)
            sections.append({"title": "Compatibility verdict", "body": body[:900]})

    elif kind == "muhurat":
        verdict = str(meta.get("verdict") or "").strip()
        if verdict:
            sections.append({"title": "Day verdict", "body": verdict[:900]})

    if kind in ("full_report", "classical_report") and not sections:
        text_sections = _fallback_from_report_text(text)
        if text_sections:
            sections.extend(text_sections)

    if not sections and text:
        snippet = re.sub(r"\s{2,}", " ", text)[:1200].strip()
        if snippet:
            sections.append({
                "title": "Overview",
                "body": snippet + ("…" if len(text) > len(snippet) else ""),
            })

    if not sections:
        sections.append({
            "title": "Overview",
            "body": "Open the full report below for the detailed reading. "
                    "A plain-English summary could not be generated for this version.",
        })
    return sections[:6]


def _llm_sections(kind: str, meta: dict, text: str) -> Optional[list[dict]]:
    if not _enabled() or not text.strip():
        return None
    report_label = _kind_label(kind)
    question = str(meta.get("question") or "").strip()
    user = (
        f"Report kind: {kind} ({report_label}).\n"
        + (f"Customer question: {question}\n" if question else "")
        + "Summarize ONLY what appears below. Return JSON matching PlainSummaryProse.\n"
        + "Visible report text:\n"
        + text
    )
    system = system_prompt_for("plain_summary")
    prose = _complete(PlainSummaryProse, system, user)
    if prose is None:
        return None
    fails = _validate(prose, text)
    if fails:
        print(f"[plain_summary] QA rejected ({kind}): {fails[:4]}", flush=True)
        return None
    return [{"title": s.title.strip(), "body": s.body.strip()} for s in prose.sections]


def build_plain_summary(
    *,
    kind: str,
    html: str,
    meta: Optional[dict] = None,
    facts: Any = None,
) -> dict:
    """Return {sections: [{title, body}], generated: 'llm'|'fallback'}."""
    meta = dict(meta or {})
    text = html_to_report_text(html)
    cache_key = hashlib.sha256(
        f"{kind}:{text[:4000]}:{json.dumps(meta, sort_keys=True, default=str)[:800]}".encode()
    ).hexdigest()[:24]

    sections = _llm_sections(kind, meta, text)
    generated = "llm"
    if not sections:
        sections = _fallback_sections(kind, meta, facts, text)
        generated = "fallback"

    return {
        "sections": sections,
        "generated": generated,
        "cache_key": cache_key,
    }


def attach_plain_summary(
    meta: dict,
    *,
    kind: str,
    free_html: str,
    paid_html: str,
    paid: bool,
    facts: Any = None,
) -> dict:
    """Mutate meta in place with plainSummary when possible."""
    meta = dict(meta or {})
    source = (paid_html if paid and (paid_html or "").strip() else free_html) or ""
    if not source.strip():
        return meta
    try:
        summary = build_plain_summary(
            kind=kind, html=source, meta=meta, facts=facts,
        )
        if summary.get("sections"):
            meta["plainSummary"] = {
                "sections": summary["sections"],
                "generated": summary.get("generated", "fallback"),
            }
    except Exception as exc:  # noqa: BLE001
        print(f"[plain_summary] skipped for {kind}: {exc}", flush=True)
    return meta
