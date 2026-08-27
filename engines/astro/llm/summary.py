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
    r"\b(blurred|lock-blur|lock-over|lock-wrap|locked-preview|fine|astro-proof-details)\b", re.I
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


def _disclaimer_section(kind: str) -> dict:
    if kind == "user_question":
        return {
            "title": "Unlock Full Report",
            "body": "To unlock the full classical verdict, exact breakthrough dates, milestone timeline, and targeted Vedic remedies (Upaya), unlock the full report.",
        }
    elif kind in ("full_report", "classical_report"):
        return {
            "title": "Unlock Full Reading",
            "body": "To access the complete life area predictions, full Dasha timeline dates, and customized Vedic remedies, unlock the full report.",
        }
    elif kind == "horary":
        return {
            "title": "Unlock Full Reading",
            "body": "To view the complete multi-tradition working, timing windows, and specific guidance, unlock the full report.",
        }
    elif kind == "palm":
        return {
            "title": "Unlock Full Reading",
            "body": "To unlock your complete chronological life timeline, future age chapters, line markings, and planetary mount remedies, unlock the full reading.",
        }
    elif kind == "numerology":
        return {
            "title": "Unlock Full Reading",
            "body": "To unlock name corrections, remedies for empty Lo Shu cells, and the next 3-year forecast dates, unlock the full report.",
        }
    elif kind == "daily":
        return {
            "title": "Full Daily Forecast",
            "body": "Subscribe for full daily access to unlock your complete Moon transit timing, running Dasha milestone dates, and daily remedies.",
        }
    return {
        "title": "Unlock Full Report",
        "body": "To unlock the full report with complete dates, milestone timelines, and targeted remedies, unlock the full reading.",
    }


def _fallback_from_palm_text(text: str, *, paid: bool = True) -> list[dict]:
    """Extract personalized personality traits, thumb decision style, and strengths for palmistry."""
    text = re.sub(r"\s{2,}", " ", (text or "").strip())
    if not text:
        return []
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
        if len(s.strip()) > 18
    ]
    if not sentences:
        return []

    shape_sentences: list[str] = []
    thumb_sentences: list[str] = []
    other_sentences: list[str] = []

    for s in sentences:
        low = s.lower()
        if any(w in low for w in ("hand shape", "air hand", "fire hand", "water hand", "earth hand", "thinker", "strategist", "communicator", "monotony", "receptive palm", "slender fingers", "square palm", "practical builder", "spontaneous", "intuitive")):
            shape_sentences.append(s)
        elif any(w in low for w in ("thumb", "governing thumb", "will and logic", "will section", "logic section", "receptive thumb", "commanding thumb", "decision", "negotiation", "phalanx", "open-set")):
            thumb_sentences.append(s)
        elif not any(w in low for w in ("unlock", "paywall", "upaya", "targeted remedies")):
            other_sentences.append(s)

    sections: list[dict] = []
    if shape_sentences:
        sections.append({
            "title": "Personality & Core Temperament",
            "body": " ".join(shape_sentences[:4])[:900],
        })

    if thumb_sentences:
        sections.append({
            "title": "Innate Strengths & Decision Style",
            "body": " ".join(thumb_sentences[:4])[:900],
        })

    if paid and other_sentences:
        line_sentences = [s for s in other_sentences if any(w in s.lower() for w in ("line", "mount", "vitality", "head line", "heart line", "fate line", "career", "chapter"))]
        if line_sentences:
            sections.append({
                "title": "Major Lines & Life Guidance",
                "body": " ".join(line_sentences[:4])[:900],
            })

    if not sections:
        titles = ("Personality & Core Temperament", "Innate Strengths & Decision Style", "Palm Features & Observations") if not paid else ("Personality & Core Temperament", "Decision Style & Strengths", "Major Lines & Life Guidance", "Energy & Practical Focus")
        limit = min(3 if not paid else 4, len(titles))
        per = max(2, min(4, (len(sentences) + limit - 1) // limit))
        idx = 0
        for title in titles:
            if idx >= len(sentences) or len(sections) >= limit:
                break
            chunk = sentences[idx:idx + per]
            idx += per
            if chunk:
                sections.append({"title": title, "body": " ".join(chunk)[:900]})

    return sections


def _fallback_from_report_text(text: str, *, max_sections: int = 5, paid: bool = True) -> list[dict]:
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
    if paid:
        titles = (
            "Direct answer & overview", "Planetary phase & influences", "Key milestone windows",
            "Energy & personal focus", "Guidance & remedies", "Recommended action",
        )
    else:
        titles = (
            "Initial situation assessment", "Current planetary influences", "Key astrological factors",
        )
    limit = min(max_sections, len(titles))
    per = max(2, min(4, (len(sentences) + limit - 1) // limit))
    sections: list[dict] = []
    idx = 0
    for title in titles:
        if idx >= len(sentences) or len(sections) >= limit:
            break
        chunk = sentences[idx:idx + per]
        idx += per
        if chunk:
            sections.append({"title": title, "body": " ".join(chunk)[:900]})
    return sections


def _fallback_sections(kind: str, meta: dict, facts: Any, text: str, *, paid: bool = True) -> list[dict]:
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
        if not sections and text:
            text_sections = _fallback_from_report_text(text, paid=paid)
            if text_sections:
                sections.extend(text_sections)

    elif kind == "horary":
        text_sections = _fallback_from_report_text(text, paid=paid)
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
        ans = meta.get("answer") or {}
        label = str(ans.get("label") or ans.get("direction") or "mixed").strip()
        bt = str(ans.get("breakthrough") or "").strip()
        low = label.lower()
        if low.startswith(("the chart", "your chart", "regarding", "on your question")):
            body = label
        elif q:
            body = f"On your question about {q}, the chart indicates: {label}."
        else:
            body = f"Regarding your question, the chart indicates: {label}."
        if paid and bt:
            body += f" The strongest opening sits around {bt}."
        sections.append({"title": "Direct assessment", "body": body[:900]})

        text_sections = _fallback_from_report_text(text, max_sections=2, paid=paid)
        if text_sections:
            for ts in text_sections:
                if ts["body"] != body:
                    sections.append(ts)
                    break

    elif kind == "daily":
        teaser = str(meta.get("teaser") or "").strip()
        if teaser:
            sections.append({"title": "Today in plain terms", "body": teaser[:900]})

    elif kind == "palm":
        text_sections = _fallback_from_palm_text(text, paid=paid)
        if text_sections:
            sections.extend(text_sections)
        if not sections:
            summary = str(meta.get("summary") or meta.get("teaser") or "").strip()
            if summary:
                sections.append({"title": "Both hands together", "body": summary[:900]})

    elif kind == "numerology":
        text_sections = _fallback_from_report_text(text, paid=paid)
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

    # For free / unpaid reports, ensure the disclaimer section is appended
    if not paid:
        disc = _disclaimer_section(kind)
        has_disc = any(
            "unlock" in (s.get("title") or "").lower() or "unlock" in (s.get("body") or "").lower()
            for s in sections
        )
        if not has_disc:
            sections.append(disc)

    return sections[:6]


def _llm_sections(kind: str, meta: dict, text: str, *, paid: bool = True) -> Optional[list[dict]]:
    if not _enabled() or not text.strip():
        return None
    report_label = _kind_label(kind)
    question = str(meta.get("question") or "").strip()
    disc = _disclaimer_section(kind)

    if kind == "palm":
        if paid:
            user = (
                f"Report kind: palm ({report_label}).\n"
                f"Report status: Full Unlocked Reading.\n"
                "Summarize the reading into 2–4 clear, warm, deeply personal sections.\n"
                "IMPORTANT: You MUST highlight the user's Core Personality Traits & Temperament derived from their hand shape (e.g. Air/Fire/Water/Earth), thinking style, thumb will/logic balance, and innate strengths, alongside their major line indicators and life guidance.\n"
                "Return JSON matching PlainSummaryProse.\n"
                "Visible report text:\n"
                f"{text}"
            )
        else:
            user = (
                f"Report kind: palm ({report_label}).\n"
                f"Report status: FREE PREVIEW (unlocked full reading is NOT active).\n"
                "IMPORTANT: For this free preview palmistry report, you MUST provide a deeply personalized summary of the user's Core Personality Traits & Temperament derived from their hand shape, thumb morphology, and thinking/decision style in the visible text below (1-2 sections, e.g. 'Personality Traits & Hand Shape' and 'Decision Style & Strengths').\n"
                "DO NOT hallucinate, assume, or invent specific future dates, age milestone timelines, or locked remedies — those are locked.\n"
                f"The final section MUST be titled '{disc['title']}' with body explaining: '{disc['body']}'\n"
                "Visible report text:\n"
                f"{text}"
            )
    elif paid:
        user = (
            f"Report kind: {kind} ({report_label}).\n"
            + f"Report status: Full Unlocked Reading.\n"
            + (f"Customer question: {question}\n" if question else "")
            + "Summarize ONLY what appears below. Return JSON matching PlainSummaryProse.\n"
            + "Visible report text:\n"
            + text
        )
    else:
        user = (
            f"Report kind: {kind} ({report_label}).\n"
            + f"Report status: FREE PREVIEW (unlocked full reading is NOT active).\n"
            + (f"Customer question: {question}\n" if question else "")
            + "IMPORTANT: This is a free preview report. Summarize ONLY the initial free diagnostic overview in the visible text below (1-2 short sections).\n"
            + "DO NOT hallucinate, assume, or invent specific breakthrough dates, milestone timelines, or remedies — those are locked.\n"
            + f"The final section MUST be titled '{disc['title']}' with body explaining: '{disc['body']}'\n"
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
    sections = [{"title": s.title.strip(), "body": s.body.strip()} for s in prose.sections]
    if not paid:
        disc = _disclaimer_section(kind)
        has_disc = any(
            "unlock" in (s.get("title") or "").lower() or "unlock" in (s.get("body") or "").lower()
            for s in sections
        )
        if not has_disc:
            sections.append(disc)
    return sections


def build_plain_summary(
    *,
    kind: str,
    html: str,
    meta: Optional[dict] = None,
    facts: Any = None,
    paid: bool = True,
) -> dict:
    """Return {sections: [{title, body}], generated: 'llm'|'fallback'}."""
    meta = dict(meta or {})
    text = html_to_report_text(html)
    cache_key = hashlib.sha256(
        f"{kind}:{paid}:{text[:4000]}:{json.dumps(meta, sort_keys=True, default=str)[:800]}".encode()
    ).hexdigest()[:24]

    sections = _llm_sections(kind, meta, text, paid=paid)
    generated = "llm"
    if not sections:
        sections = _fallback_sections(kind, meta, facts, text, paid=paid)
        generated = "fallback"

    return {
        "sections": sections,
        "generated": generated,
        "cache_key": cache_key,
        "paid": bool(paid),
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
            kind=kind, html=source, meta=meta, facts=facts, paid=bool(paid),
        )
        if summary.get("sections"):
            meta["plainSummary"] = {
                "sections": summary["sections"],
                "generated": summary.get("generated", "fallback"),
                "paid": bool(paid),
            }
    except Exception as exc:  # noqa: BLE001
        print(f"[plain_summary] skipped for {kind}: {exc}", flush=True)
    return meta
