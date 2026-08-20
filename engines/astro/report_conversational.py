"""Compact conversational astrology report — LLM-on path only.

Leaves ``report_cards.render`` untouched. Chosen by ``report_render`` when the
LLM layer is enabled and produced an accepted conversational overlay.

Generation patch: chart signature, Python-owned area timing, evidence, and
astrologer-voice layout. Free still teasers father/mother from family_note.
"""

from __future__ import annotations

import html as _html
import re
from datetime import date
from typing import Any, Optional

from report_shell import EXTRA as _EXTRA
from report_shell import INTERACT as _INTERACT
from report_shell import STYLE as _STYLE
from report_shell import lock_sections as _lock_sections

from llm.fallback import area_tone


def _e(value: Any) -> str:
    return _html.escape(str(value or ""), quote=True)


# Shared by the life-area cards and the question answer, which is rendered
# through a different shell.
TRANSITION_MAP_CSS = """
.life-map{margin:16px 0 2px;padding:14px 14px 13px;background:#fbfaf7;border:1px solid #e5e0d6;border-radius:12px}
.life-map-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.life-map-head h4{font-family:Georgia,serif;font-size:1rem;margin:4px 0 0;color:#252936}
.map-key{font-size:.63rem;color:#6a7080;white-space:nowrap;border:1px solid #ddd8cd;border-radius:99px;padding:4px 7px}
.life-map-intro{font-size:.78rem!important;color:#656a74!important;margin:9px 0 12px!important}
.lane-chart{position:relative;margin:8px 0 34px;padding:4px 0 18px}
.lane-axis{position:relative;height:18px;margin:0 0 8px 72px}
.lane-tick{position:absolute;transform:translateX(-50%);font-size:.62rem;font-weight:700;color:#6a7080;white-space:nowrap}
.lane-row{display:grid;grid-template-columns:72px 1fr;gap:8px;align-items:center;margin:6px 0}
.lane-label{font-size:.62rem;letter-spacing:.08em;text-transform:uppercase;font-weight:700;color:#6a7080}
.lane-track{position:relative;height:22px;background:#efece4;border-radius:99px;overflow:hidden}
.lane-seg{position:absolute;top:2px;bottom:2px;border-radius:99px;font-size:.58rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;display:flex;align-items:center;justify-content:flex-start;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;padding:0 7px}
.lane-seg.phase{background:#e8e0cf;color:#3d4250}
.lane-seg.phase.up{background:#d7efe3;color:#1c6b45}
.lane-seg.phase.down{background:#f6d7d0;color:#a3341f}
.lane-seg.md{background:#16181d;color:#f7f5f1}
.lane-seg.ad{background:#8a6a1f;color:#fff}
.lane-seg.yog{background:#5c4a7a;color:#fff}
.lane-seg.chara{background:#2f5d4a;color:#fff}
.lane-seg.tr{background:#d9e4f2;color:#1a5f9e}
.lane-seg.ctx{background:#e6e2d8;color:#4a4636}
.lane-seg.ctx.supportive{background:#cfe8da;color:#1c6b45}
.lane-seg.ctx.testing{background:#f3d3cb;color:#a3341f}
.lane-seg.ctx.onhouse{background:#ded6ea;color:#4a3d63}
.lane-confluence{position:absolute;top:18px;bottom:0;width:0;transform:translateX(-50%);z-index:2;pointer-events:none}
.conf-pin{display:block;width:0;border-left:1.5px dashed #8a6a1f;height:100%;margin:0 auto}
.conf-cap{position:absolute;left:50%;bottom:-2px;transform:translate(-50%,100%);font-size:.58rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:#8a6a1f;white-space:nowrap;background:#fbfaf7;padding:2px 5px}
.transition-track{position:relative;margin:0 0 2px}
.transition-node{display:grid;grid-template-columns:18px 1fr;gap:10px;min-height:74px;position:relative}
.transition-rail{position:relative}
.transition-rail:before{content:"";position:absolute;left:7px;top:5px;bottom:-5px;width:2px;background:#ded9ce}
.transition-node:last-child .transition-rail:before{bottom:42px}
.transition-dot{position:absolute;left:3px;top:6px;width:10px;height:10px;border-radius:50%;background:#8a6a1f;border:2px solid #fbfaf7;box-shadow:0 0 0 1px #c9c1b3}
.transition-node.up .transition-dot{background:#1c6b45}
.transition-node.down .transition-dot{background:#a3341f}
.transition-body{padding:0 0 15px}
.transition-when{font-size:.67rem;font-weight:700;letter-spacing:.05em;color:#6a7080}
.transition-phase{font-family:Georgia,serif;font-size:.94rem;font-weight:700;color:#252936;margin-top:2px}
.transition-meaning{font-size:.8rem!important;margin:3px 0 5px!important;color:#3d4250!important}
.overlap-chips{display:flex;flex-wrap:wrap;gap:5px;margin:4px 0}
.overlap-chip{font-size:.62rem;padding:3px 6px;border-radius:99px;background:#f0ede6;border:1px solid #e1dcd2;color:#5a554c}
.transition-drivers{font-size:.64rem;color:#7a7d84;margin-top:4px}
.transition-ease{font-size:.82rem!important;margin:2px 0 8px!important;color:#1c6b45!important}
.transition-gap{font-size:.79rem!important;margin:0 0 11px!important;padding:8px 10px;border-radius:8px;background:#f3efe6;color:#4a4636!important}
.ctx-transits{margin:2px 0 8px;border-top:1px solid #e6e1d7;padding-top:7px}
.ctx-transits summary{cursor:pointer;font-size:.68rem;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:#6a7080}
.ctx-note{font-size:.72rem!important;color:#7a7d84!important;margin:6px 0 4px!important}
.ctx-list{list-style:none;margin:0;padding:0}
.ctx-row{display:grid;grid-template-columns:118px 1fr;gap:8px;padding:4px 0;border-bottom:1px dotted #e6e1d7;font-size:.76rem}
.ctx-row:last-child{border-bottom:none}
.ctx-when{font-weight:700;color:#4a4f5c;white-space:nowrap}
.ctx-row.supportive .ctx-what{color:#1c6b45}
.ctx-row.testing .ctx-what{color:#a3341f}
.ctx-row.onhouse .ctx-what{color:#4a3d63}

.future-conf{margin-top:10px;border-top:1px solid #e4ded3;padding-top:9px}.future-conf-title{font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;color:#6a7080;font-weight:700}.future-conf-row{display:grid;grid-template-columns:82px 105px 1fr;gap:8px;padding:7px 0;border-bottom:1px dotted #e6e1d7;align-items:start}.future-conf-row:last-child{border-bottom:none}.future-conf-date{font-weight:700;color:#4a4f5c;font-size:.7rem}.future-conf-change{font-size:.62rem;text-transform:uppercase;letter-spacing:.05em;font-weight:700}.future-conf-change.improves{color:#1c6b45}.future-conf-change.eases_but_continues{color:#7b6a1f}.future-conf-change.worsens{color:#a3341f}.future-conf-change.continues,.future-conf-change.mixed_change{color:#6a7080}.future-conf-reason{font-size:.72rem;color:#5d625f}.future-conf-state{font-size:.68rem;color:#6a7080;margin-top:2px}
@media(max-width:520px){.future-conf-row{grid-template-columns:1fr;gap:2px}}

.transition-note{margin-top:6px;padding:10px 11px;background:#f1eee7;border-radius:9px}
.transition-note p{font-family:Georgia,serif;font-size:.87rem!important;margin:4px 0 0!important;line-height:1.5!important}
.lane-key{font-size:.68rem!important;color:#6a7080!important;margin:0 0 12px!important;line-height:1.45!important}
.conf-line{display:none}
@media(max-width:520px){.lane-chart{display:none}.lane-key{display:none}.ctx-row{grid-template-columns:1fr}
.conf-line{display:block;font-size:.72rem!important;color:#8a6a1f!important;font-weight:600;margin:0 0 10px!important}}
.det-confluence{margin:12px 0;padding:12px 13px;background:#f7f4ec;border:1px solid #e2dccf;border-radius:11px}
.consultation-conclusion{margin:12px 0 8px;padding:14px 15px;background:#fff;border:1px solid #e4ded3;border-radius:10px}
.consultation-conclusion p{font-family:Georgia,serif;font-size:1.04rem!important;line-height:1.62!important;margin:0!important;color:#292d36}
.consultation-remedy{margin:10px 0 0;padding:10px 12px;background:#faf5e7;border-left:3px solid #c9a227;border-radius:8px}
.consultation-remedy p{margin:3px 0 0!important;font-size:.86rem!important;line-height:1.55!important}
.confluence-details{margin-top:10px;border-top:1px solid var(--line);padding-top:8px}
.confluence-details summary{cursor:pointer;font-size:.72rem;color:#6a7080;font-weight:700;letter-spacing:.02em}
.det-confluence-head{display:flex;justify-content:space-between;gap:12px;align-items:center;font-size:.78rem;color:#2f3340;margin-bottom:8px}
.det-confluence-head span{font-size:.66rem;color:#6a7080}
.det-confluence .evidence-grid{margin-top:4px}
.future-conf-summary{display:flex;flex-wrap:wrap;gap:8px;margin-top:9px;font-size:.72rem;color:#3d4250}
"""


def _conf_sentence(conf: dict) -> str:
    """Say what the dashed line is, and when.

    The marker used to be an undated flag on an axis whose scale changes from
    one area to the next, so a reader comparing two cards had no way to know
    what the line meant or which month it stood over.
    """
    caption = str(conf.get("caption") or "").strip()
    if not caption:
        return ""
    what = caption[:1].lower() + caption[1:]
    start = str(conf.get("start") or "").strip()
    end = str(conf.get("end") or "").strip()
    when = f"{start} to {end}" if start and end else (start or end)
    if not when:
        return f"Dashed line: the strongest single turn in this stretch — {what}."
    return (f"Dashed line: the strongest single turn in this stretch — "
            f"{when}, when {what}.")


def _area_label(area: str, cards: list) -> str:
    for c in cards or []:
        if getattr(c, "area", "") == area:
            return str(getattr(c, "label", "") or area)
    return area.replace("_", " ").title()


def _canonical(card: Any) -> dict:
    """Engine cards keep promise/activation/timing on confluence.canonical_result."""
    cf = getattr(card, "confluence", None)
    if not isinstance(cf, dict):
        return {}
    cr = cf.get("canonical_result")
    return cr if isinstance(cr, dict) else cf


def _card_status(card: Any) -> str:
    status = str(getattr(card, "status", "") or "").strip()
    if status:
        return status
    promise = (_canonical(card).get("promise") or {})
    if not isinstance(promise, dict):
        promise = {}
    return str(promise.get("status") or "").strip() or "insufficient_evidence"


def _card_activation(card: Any) -> str:
    activation = str(getattr(card, "activation_status", "") or "").strip()
    if activation:
        return activation
    row = (_canonical(card).get("activation") or {})
    if not isinstance(row, dict):
        row = {}
    return str(row.get("status") or "").strip() or "inactive"


def _card_direction(card: Any) -> str:
    direction = str(getattr(card, "direction", "") or "").strip()
    if direction:
        return direction
    return str(_canonical(card).get("direction") or "mixed")


def _card_agreement(card: Any) -> str:
    agreement = str(getattr(card, "agreement", "") or "").strip()
    if agreement:
        return agreement
    return str(_canonical(card).get("agreement") or "weak")


def _card_planets(card: Any) -> list[str]:
    planets = [str(x) for x in (getattr(card, "allowed_planets", None) or []) if str(x).strip()]
    if planets:
        return planets
    return [str(x) for x in (getattr(card, "planets", None) or []) if str(x).strip()]


def _fmt_date(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return f"{date.fromisoformat(text[:10]):%d %b %Y}"
    except Exception:
        return text


def _fmt_mon(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return f"{date.fromisoformat(text[:10]):%b %Y}"
    except Exception:
        return text


def _fmt_full_month(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return f"{date.fromisoformat(text[:10]):%B %Y}"
    except Exception:
        return text


def _fmt_when(start: str, end: str) -> str:
    a, b = _fmt_date(start), _fmt_date(end)
    if a and b:
        return f"{a} → {b}"
    return a or b


def _window_parts(w: Any) -> tuple[str, str]:
    if w is None or w == "":
        return "", ""
    if isinstance(w, dict):
        start = str(w.get("start") or "").strip()
        end = str(w.get("end") or "").strip()
        if start or end:
            return start, end
        label = str(w.get("label") or "").strip()
        return (label, "") if label else ("", "")
    start = str(getattr(w, "start", "") or "").strip()
    end = str(getattr(w, "end", "") or "").strip()
    if start or end:
        return start, end
    label = str(getattr(w, "label", "") or "").strip()
    if label:
        return label, ""
    return "", ""


def _card_windows(card: Any) -> list[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    out: list[tuple[str, str]] = []

    def add(start: str, end: str) -> None:
        if not (start or end):
            return
        key = (start, end)
        if key in seen:
            return
        seen.add(key)
        out.append(key)

    for w in list(getattr(card, "timing_windows", None) or []):
        add(*_window_parts(w))
    add(*_window_parts(getattr(card, "window", None)))
    if out:
        return out
    timing = _canonical(card).get("timing") or {}
    if not isinstance(timing, dict):
        return out
    rows: list[Any] = []
    best = timing.get("best_window")
    if isinstance(best, dict):
        rows.append(best)
    for key in ("featured_windows", "strong_windows", "validated_windows"):
        rows.extend(x for x in (timing.get(key) or []) if isinstance(x, dict))
    for row in rows:
        add(str(row.get("start") or "").strip(), str(row.get("end") or "").strip())
    return out


def _pill(block: dict, card: Any, today: Optional[date] = None) -> str:
    """Chip built from the same promise/activation facts as the paragraph."""
    label = str((block or {}).get("tone_label") or "").strip()
    cls = str((block or {}).get("tone_class") or "mixed").strip()
    activation = _card_activation(card) if card is not None else "inactive"
    # A chip that says "now" over a window that opens in 2028 is the same
    # contradiction the fact line avoids.
    if card is not None and _card_transition_state(card, today).get("state") == "upcoming":
        activation = "inactive"
        label = ""
    if not label:
        if card is None:
            return ""
        from types import SimpleNamespace
        label, cls = area_tone(SimpleNamespace(
            status=_card_status(card),
            activation_status=activation,
            kind=getattr(card, "kind", "promise") or "promise",
            direction=getattr(card, "direction", "") or "",
            transition_map=list(getattr(card, "transition_map", None) or []),
        ))
    return f'<span class="pill {cls}">{_e(label)}</span>'


def _readable_status(value: str) -> str:
    mapping = {
        "strongly_supported": "Strongly supported",
        "supported": "Supported",
        "strongly_indicated": "Strongly indicated",
        "mixed": "Mixed",
        "weak": "Weak",
        "insufficient_evidence": "Not clearly established",
        "strongly_active": "Strongly active now",
        "active": "Active now",
        "inactive": "Not strongly active yet",
        "caution": "Needs care",
        "support": "Supportive",
        "down": "Needs care",
        "up": "Supportive",
    }
    return mapping.get(str(value or "").lower(), str(value or "").replace("_", " ").title())


def _sanitize_customer_text(value: Any) -> str:
    """Remove known engine/placeholder leakage from LLM prose at the boundary."""
    text = str(value or "").strip()
    banned = (
        "This remedy is linked to a relevant chart factor",
        "The chart evidence is summarized in the life-area reading above",
        "Timing evidence is included in the overall reading",
    )
    if any(x.lower() in text.lower() for x in banned):
        return ""
    return text


def _sanitize_prose_tree(value: Any) -> Any:
    """Sanitize all customer-facing LLM strings without changing structure."""
    if isinstance(value, str):
        return _sanitize_customer_text(value)
    if isinstance(value, list):
        return [_sanitize_prose_tree(x) for x in value]
    if isinstance(value, dict):
        return {k: _sanitize_prose_tree(v) for k, v in value.items()}
    return value


def _confluence_pill(aj: dict) -> str:
    if not isinstance(aj, dict):
        return ""
    j = str(aj.get("final_judgement") or "insufficient").lower()
    label = str(aj.get("confluence_label") or "").strip() or {
        "good": "Favourable", "moderate": "Moderately supportive",
        "challenging": "Needs care", "mixed": "Mixed",
        "insufficient": "Insufficient evidence",
    }.get(j, "Insufficient evidence")
    cls = {"good": "good", "moderate": "mid", "challenging": "bad", "mixed": "mid"}.get(j, "mixed")
    return f'<span class="pill {cls}">{_e(label)}</span>'


def _family_labels(count: int) -> list[str]:
    return ["Father", "Mother", "Siblings", "Home & upbringing"][:count]


def _lane_bar(item: dict, cls: str) -> str:
    left = float(item.get("left_pct") or 0)
    width = float(item.get("width_pct") or 0)
    direction = str(item.get("direction") or "")
    extra = f" {direction}" if direction in ("up", "down", "mixed") else ""
    label = str(item.get("label") or "")
    # A centred label on a short bar gets clipped on both sides and reads as a
    # broken word ("ni Bhramari (M"). Short bars carry the name only in the
    # tooltip; the rest read from the left so any clipping lands on the tail.
    if width < 9:
        extra += " tiny"
        label = ""
    return (
        f'<div class="lane-seg {cls}{extra}" style="left:{left:.2f}%;width:{width:.2f}%" '
        f'title="{_e(item.get("label") or "")}">{_e(label)}</div>'
    )


def render_transition_map(
    pc: dict,
    transitions: list,
    *,
    area: str = "",
    note: str = "",
    context: Optional[list] = None,
    today: Optional[date] = None,
    heading: str = "How the story changes inside the longer period",
    kicker: str = "Life-area transition map",
    intro: str = (
        "The long forecast is not one flat period. Each marker is a dated overlap "
        "of the timing systems already used by the chart."
    ),
    with_css: bool = False,
) -> str:
    """Horizontal transition map, with a vertical rail on small screens.

    Shared by the life-area cards and the question answer so a reader gets the
    same dated picture wherever timing is discussed.
    """
    transitions = list(transitions or [])
    if not transitions:
        return ""
    from life_area_transition import (
        build_transition_lanes,
        customer_list,
        easing_note,
        field_of,
        short_phase,
    )
    lanes = build_transition_lanes(
        pc or {}, transitions, area=area, context=list(context or []))
    note = str(note or "").strip()

    axis_html = ""
    lane_html = ""
    conf_key = ""
    # The lane chart is hidden on a phone, so the confluence flag it carries —
    # the one line that names the problem — is repeated for narrow screens.
    conf_line = ""
    if lanes:
        ticks = "".join(
            f'<span class="lane-tick" style="left:{float(t.get("left_pct") or 0):.2f}%">{_e(t.get("label") or "")}</span>'
            for t in (lanes.get("axis") or {}).get("ticks") or []
        )
        phases = "".join(_lane_bar(p, "phase") for p in lanes.get("phases") or [])
        md_only = "".join(
            _lane_bar(b, "md") for b in lanes.get("dasha") or [] if b.get("kind") == "md"
        )
        ad_only = "".join(
            _lane_bar(b, "ad") for b in lanes.get("dasha") or [] if b.get("kind") == "ad"
        )
        yog_bars = "".join(_lane_bar(t, "yog") for t in lanes.get("yogini") or [])
        chara_lane = "".join(_lane_bar(t, "chara") for t in lanes.get("chara") or [])
        tr_bars = "".join(_lane_bar(t, "tr") for t in lanes.get("transits") or [])
        ctx_bars = "".join(
            _lane_bar(t, f"ctx {str(t.get('tone') or 'steady')}")
            for t in lanes.get("context_bars") or []
        )
        conf = lanes.get("confluence") or {}
        conf_html = ""
        if conf:
            caption = str(conf.get("caption") or "").strip()
            if caption:
                conf_line = f'<p class="conf-line">{_e(_conf_sentence(conf))}</p>'
            conf_html = (
                f'<div class="lane-confluence" style="left:{float(conf.get("left_pct") or 0):.2f}%">'
                f'<span class="conf-pin"></span>'
                f'<span class="conf-cap">{_e(conf.get("caption") or "Confluence")}</span>'
                f"</div>"
            )
            conf_key = f'<p class="lane-key">{_e(_conf_sentence(conf))}</p>'
        lane_html = f"""
        <div class="lane-chart">
          <div class="lane-axis">{ticks}</div>
          <div class="lane-row"><div class="lane-label">Story</div><div class="lane-track">{phases}</div></div>
          {f'<div class="lane-row"><div class="lane-label">Period</div><div class="lane-track">{md_only}</div></div>' if md_only else ""}
          {f'<div class="lane-row"><div class="lane-label">Chapter</div><div class="lane-track">{ad_only}</div></div>' if ad_only else ""}
          {f'<div class="lane-row"><div class="lane-label">Yogini</div><div class="lane-track">{yog_bars}</div></div>' if yog_bars else ""}
          {f'<div class="lane-row"><div class="lane-label">Chara</div><div class="lane-track">{chara_lane}</div></div>' if chara_lane else ""}
          {f'<div class="lane-row"><div class="lane-label">Transit</div><div class="lane-track">{tr_bars}</div></div>' if tr_bars else ""}
          {f'<div class="lane-row"><div class="lane-label">Rulers</div><div class="lane-track">{ctx_bars}</div></div>' if ctx_bars else ""}
          {conf_html}
        </div>
        {conf_key}
        """
        axis_html = lane_html

    nodes = []
    for t in transitions[:6]:
        start = field_of(t, "start")
        end = field_of(t, "end")
        when = f"{_fmt_mon(start)} → {_fmt_mon(end)}" if (start or end) else ""
        if not when:
            when = str(field_of(t, "phase") or "Transition")
        direction = str(field_of(t, "direction") or "mixed")
        cls = "up" if direction in ("up", "support") else "down" if direction in ("down", "caution") else "mixed"
        chips = "".join(
            f'<span class="overlap-chip">{_e(x)}</span>'
            for x in customer_list(list(field_of(t, "overlap") or []))
        )
        # `drivers` repeats the overlap chips almost word for word, so the
        # chips carry it and the line stays out of the reader's way.
        nodes.append(f"""
          <div class="transition-node {cls}">
            <div class="transition-rail"><span class="transition-dot"></span></div>
            <div class="transition-body">
              <div class="transition-when">{_e(when)}</div>
              <div class="transition-phase">{_e(short_phase(field_of(t, "phase") or "Transition"))}</div>
              <p class="transition-meaning">{_e(field_of(t, "meaning") or "A change in the tone of this life area is indicated here.")}</p>
              {f'<div class="overlap-chips">{chips}</div>' if chips else ""}
            </div>
          </div>
        """)
    note_html = ""
    if note:
        note_html = (
            f'<div class="transition-note"><span class="ev-label">Astrologer\'s reading of the shift</span>'
            f"<p>{_e(note)}</p></div>"
        )

    ease = easing_note(transitions, today=today)
    ease_html = (
        f'<p class="transition-ease"><b>When it eases:</b> {_e(ease)}</p>' if ease else ""
    )

    # A map that opens years from now leaves the reader asking what happens in
    # between; the answer is the ruler and period-lord list, which starts today.
    from life_area_transition import window_state
    state = window_state(transitions, today=today)
    gap_html = ""
    if state.get("state") == "upcoming" and state.get("opens_iso"):
        try:
            opens = date.fromisoformat(str(state["opens_iso"]))
            months = (opens.year - (today or date.today()).year) * 12 + (
                opens.month - (today or date.today()).month)
        except ValueError:
            months = 0
        if months >= 18:
            gap_html = (
                f'<p class="transition-gap">No dated turn reaches this area before '
                f'<b>{_e(state["opens"])}</b>. Until then it moves with the period '
                f'lords listed below rather than with a single event.</p>'
            )

    ctx_rows = list(lanes.get("context_rows") or [])
    ctx_html = ""
    if ctx_rows:
        items = "".join(
            f'<li class="ctx-row {_e(str(r.get("tone") or "steady"))}">'
            f'<span class="ctx-when">{_e(r.get("when") or "")}</span>'
            f'<span class="ctx-what">{_e(r.get("caption") or "")}</span></li>'
            for r in ctx_rows
        )
        movers = sum(1 for r in ctx_rows if r.get("in_house"))
        summary = (
            f"House ruler and period-lord transits — {movers} "
            f"{'stay touches' if movers == 1 else 'stays touch'} this house"
            if movers else
            "House ruler and period-lord transits — none of these touch this house"
        )
        ctx_html = f"""
        <details class="ctx-transits">
          <summary>{_e(summary)}</summary>
          <p class="ctx-note">These are the dated stays of the planet that owns this house and of the lords of the period you are running. The ones that touch this house are drawn on the map above; the rest are listed here because they still set the background.</p>
          <ul class="ctx-list">{items}</ul>
        </details>
        """

    return f"""
      {f"<style>{TRANSITION_MAP_CSS}</style>" if with_css else ""}
      <div class="life-map">
        <div class="life-map-head">
          <div>
            <div class="ev-label">{_e(kicker)}</div>
            <h4>{_e(heading)}</h4>
          </div>
          <span class="map-key">Overlap → transition</span>
        </div>
        <p class="life-map-intro">{_e(intro)}</p>
        {gap_html}
        {conf_line}
        {axis_html}
        <div class="transition-track">{"".join(nodes)}</div>
        {ease_html}
        {ctx_html}
        {note_html}
      </div>
    """


def _card_transition_state(card: Any, today: Optional[date] = None) -> dict:
    """Running / still ahead, judged on the card's own dated windows."""
    if card is None:
        return {}
    from life_area_transition import window_state
    rows: list = list(getattr(card, "transition_map", None) or [])
    if not rows:
        rows = [{"start": start, "end": end} for start, end in _card_windows(card)]
    return window_state(rows, today=today) if rows else {}


def _activation_phrase(card: Any, activation: str, today: Optional[date] = None) -> str:
    """Activation wording that cannot contradict the dates printed beside it."""
    state = _card_transition_state(card, today)
    kind = str(getattr(card, "kind", "promise") or "promise").lower()
    if state.get("state") == "upcoming" and state.get("opens"):
        if kind == "challenge":
            return f"Opens {state['opens']} (demanding stretch)"
        return f"Opens {state['opens']}"

    tmap = list(getattr(card, "transition_map", None) or [])
    first_dir = ""
    if tmap:
        from life_area_transition import field_of
        first_dir = str(field_of(tmap[0], "direction") or "").lower()
    direction = str(getattr(card, "direction", "") or "").lower()
    current_strain = direction in ("down", "caution") or first_dir in ("down", "caution")

    readable = _readable_status(activation)
    if current_strain and activation in ("strongly_active", "active"):
        return f"{readable} (demanding phase)"
    return readable


def _fallback_help(card: Any, area_label: str) -> str:
    """Never leave a flagged problem without a step or an easing date."""
    if card is None:
        return ""
    from life_area_transition import easing_note, problem_nodes
    rows = list(getattr(card, "transition_map", None) or [])
    direction = str(getattr(card, "direction", "") or "").lower()
    status = str(getattr(card, "status", "") or "").lower()
    kind = str(getattr(card, "kind", "promise") or "promise").lower()
    is_problem = bool(problem_nodes(rows)) or kind == "challenge" or direction in (
        "down", "caution") or status in ("weak", "insufficient_evidence")
    if not is_problem:
        return ""
    try:
        from llm.fallback import _area_remedy_sentence
        step = _area_remedy_sentence(card, area_label)
    except Exception:  # noqa: BLE001
        step = ""
    ease = easing_note(rows)
    return " ".join(x for x in (step, ease) if x).strip()


def _transition_map_html(pc: dict, card: Any, block: dict) -> str:
    """The transition map for one life-area card."""
    if card is None:
        return ""
    return render_transition_map(
        pc or {},
        list(getattr(card, "transition_map", None) or []),
        area=str(getattr(card, "area", "") or ""),
        note=str((block or {}).get("transition_note") or "").strip(),
        context=list(getattr(card, "transit_context", None) or []),
    )


_EVIDENCE_LEAK = (
    "lord", "sub-lord", "sublord", "karaka", "cusp", "shadbala",
    "ashtakavarga", "varga", "degree", "longitude",
)


def _free_area_teaser(cards: list, today: Optional[date] = None) -> str:
    """Free view: per-area teaser cards showing real headers, blurred body.

    Each card shows the real area label, status pill and chart-result line
    (House · promise · activation — opens date) so the reader sees personalised
    data, but the interpretation, timing and remedy are blurred behind a
    ``lock-wrap`` with a "Locked · in the full reading" chip.  The free render
    path never holds the LLM interpretation blocks (``areas`` is ``{}``), so
    the blurred body uses generic non-personal placeholders drawn from the
    card engine's own summary fields.
    """
    if not cards:
        return ""
    parts: list[str] = []
    for card in cards:
        if card is None:
            continue
        area = str(getattr(card, "area", "") or "")
        label = _area_label(area, cards)
        status = _card_status(card) if card is not None else "insufficient_evidence"
        activation = _card_activation(card) if card is not None else "inactive"
        house = int(getattr(card, "house", 0) or 0)
        kind = str(getattr(card, "kind", "promise") or "promise").lower()

        pill = _pill({}, card, today)
        activation_txt = _activation_phrase(card, activation, today)
        activation_free = re.sub(r"\s*[—–-]?\s*opens\s+\w+\s+\d{4}.*", "", activation_txt, flags=re.IGNORECASE).strip() or "Not active yet"
        fact_line = (
            f"House {house or '—'} · Birth chart: {_readable_status(status)} "
            f"· Timing: {activation_free}"
        )

        # Blurred body — generic, non-personal text the free path can safely
        # show without leaking any LLM-written interpretation.
        outlook = str(getattr(card, "outlook_line", "") or "").strip()
        if not outlook:
            outlook = (
                "The chart factors behind this area combine to form the picture "
                "below."
            )
        timing_rows = list(getattr(card, "transition_map", None) or [])
        if timing_rows:
            timing_note = (
                f"{len(timing_rows)} dated marker{'s' if len(timing_rows) != 1 else ''}"
                " across the next five years.  Unlock to see the exact dates."
            )
        else:
            timing_note = "Dated markers across the next five years."
        remedy_note = (
            "Practical steps and gemstone guidance where this area needs support."
        )

        parts.append(f"""
        <article class="card conv-area">
          <div class="card-top">
            <span class="area">{_e(label)}</span>
            {pill}
          </div>
          <div class="area-fact"><span class="mini-label">Chart result</span>{_e(fact_line)}</div>
          <div class="area-reading">
            <div class="reading-label">What the chart is saying</div>
            <div class="lock-wrap">
              <div class="lock-blur">{_e(outlook)}</div>
              <div class="lock-over"><span class="lock-chip">Locked &#183; in the full reading</span></div>
            </div>
          </div>
          <div class="area-timing">
            <span class="ev-label">Timing</span>
            <div class="lock-wrap">
              <div class="lock-blur">{_e(timing_note)}</div>
              <div class="lock-over"><span class="lock-chip">Locked &#183; in the full reading</span></div>
            </div>
          </div>
          <div class="area-help">
            <span class="ev-label">What helps</span>
            <div class="lock-wrap">
              <div class="lock-blur">{_e(remedy_note)}</div>
              <div class="lock-over"><span class="lock-chip">Locked &#183; in the full reading</span></div>
            </div>
          </div>
        </article>
        """)
    return "\n".join(parts)


def _analytical_html(analysis: Any, *, paid: bool, today: date) -> str:
    """Render deterministic astrological evidence; Qwen never writes this block."""
    if not paid or not analysis:
        return ""
    if hasattr(analysis, "model_dump"):
        data = analysis.model_dump(mode="json")
    elif isinstance(analysis, dict):
        data = analysis
    else:
        return ""
    clocks=list(data.get("timing_systems") or []); cross=list(data.get("crossover_points") or [])
    slow=list(data.get("slow_transits") or []); jai=data.get("jaimini") or {}
    dpt=list(data.get("dasha_planet_transits") or []); areas=list(data.get("life_area_judgements") or [])
    def fdate(x, full=False):
        text = str(x or "").strip()
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            return ""
        return _fmt_full_month(text) if full else _fmt_mon(text)
    def j(v): return _e(v)
    def astro_term(value):
        mapping = {
            "Natural karaka": "Natural Karaka",
            "natural significator": "Natural Karaka",
            "the natural significator method": "Jaimini Karaka judgement",
            "The main timing cycle": "Vimshottari",
            "Period-planet transit": "Dasha-planet transit",
            "period-planet transit": "Dasha-planet transit",
            "AMK": "AmK", "Atmakarak": "AK", "Amatyakarak": "AmK",
            "Gnatikaraka": "GK", "Putrakaraka": "PK",
        }
        return mapping.get(str(value), str(value))
    def verdict(v):
        v=(v or "insufficient").lower(); cls="good" if v in ("good","supportive") else "bad" if v in ("challenging","testing") else "mid"
        return f'<span class="aj-verdict {cls}">{j(v.title())}</span>'
    clock_rows=[]
    for c in clocks:
        houses=", ".join(str(x) for x in (c.get("activated_houses") or [])) or "—"
        clock_rows.append(f'<div class="aj-clock"><div><b>{j(str(c.get("system") or "").title())}</b><span>{j(c.get("current") or "—")}</span></div><div class="aj-clock-next"><small>Until</small><b>{j(fdate(c.get("current_end"), True) or "—")}</b><small>Next</small><b>{j(c.get("next") or "—")}</b></div><div class="aj-houses"><small>Activated houses</small><b>{j(houses)}</b></div>{verdict(c.get("judgement"))}</div>')
    crossover_html=""
    if cross:
        items=[]
        for x in cross:
            items.append(f'<div class="aj-cross"><b>{j(fdate(x.get("date"), True))}</b><span>{j(" · ".join(x.get("systems") or []))}</span><small>{j(x.get("significance") or "Timing change")}</small></div>')
        crossover_html=f'<div class="aj-cross-grid">{"".join(items)}</div>'
    slow_html=""
    if slow:
        rows=[]
        for t in slow:
            av=t.get("ashtakavarga"); avs="—" if av is None else str(av)
            rows.append(f'<tr><td><b>{j(t.get("planet"))}</b><small>{j(t.get("functional_role"))}</small></td><td>{j(t.get("sign"))}</td><td>{j(t.get("house") or "—")}</td><td>{j(t.get("from_natal_house") or "—")}</td><td>{j(avs)}</td><td>{verdict(t.get("judgement"))}</td></tr>')
        slow_html=f'<table class="aj-table"><thead><tr><th>Planet</th><th>Transit sign</th><th>House</th><th>From natal planet</th><th>Bindu score</th><th>Transit tone</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'
    jai_html=""
    if jai:
        karaka=[]
        for key in ("ak","amk","gk","pk"):
            if jai.get(key): karaka.append(f'<span><b>{j(key.upper())}</b> {j(jai.get(key))}</span>')
        jai_html=f'<div class="aj-jai"><div class="aj-karakas">{"".join(karaka) or "Karaka data not available"}</div><div class="aj-jai-meta"><span>Chara major <b>{j(jai.get("current_maha_sign") or "—")}</b></span><span>Chara minor <b>{j(jai.get("current_antar_sign") or "—")}</b></span><span>Activated houses <b>{j(", ".join(str(x) for x in (jai.get("activated_houses") or [])) or "—")}</b></span>{verdict(jai.get("judgement"))}</div><p>{j(jai.get("argala_judgement") or "Jaimini judgement not available.")}</p></div>'
    dpt_html=""
    if dpt:
        rows=[]
        for t in dpt:
            av=t.get("ashtakavarga"); rows.append(f'<div class="aj-dpt"><b>{j(t.get("planet"))}</b><span>{j(t.get("role"))}</span><span>{j(t.get("functional_role"))}</span><span>{j(t.get("sign"))} · H{j(t.get("house") or "—")}</span><span>{j("—" if av is None else av)} bindus</span>{verdict(t.get("judgement"))}</div>')
        dpt_html="".join(rows)
    area_html=""
    if areas:
        rows=[]
        for a in areas:
            facts=[
                f'Natural significator <b>{j(", ".join(a.get("natural_karakas") or []) or "—")}</b>',
                f'House lord <b>{j(a.get("house_lord") or "—")}</b>',
                f'Depositor <b>{j(a.get("depositor") or "—")}</b>',
                f'House strength <b>{j(a.get("house_strength") or "—")}</b>',
                f'{j(a.get("divisional_chart") or "Divisional")} <b>{j(a.get("divisional_verdict") or "—")}</b>',
                f'AmK <b>{j(a.get("amk") or "—")}</b>',
            ]
            periods=[f'Vim <b>{j(a.get("current_vimshottari") or "—")}</b>',f'Chara <b>{j(a.get("current_chara") or "—")}</b>',f'Yogini <b>{j(a.get("current_yogini") or "—")}</b>']
            lanes = a.get("lane_judgements") or {}
            lane_html = "".join(f'<span><b>{j(astro_term(k))}</b> {j(v)}</span>' for k, v in lanes.items())
            supports = "".join(f'<li>{j(x)}</li>' for x in (a.get("supporting_factors") or [])[:5])
            cautions = "".join(f'<li>{j(x)}</li>' for x in (a.get("caution_factors") or [])[:5])
            factor_html = ""
            if supports or cautions:
                factor_html = '<div class="aj-factor-cols">'
                if supports:
                    factor_html += f'<div><small>Supporting factors</small><ul>{supports}</ul></div>'
                if cautions:
                    factor_html += f'<div><small>Caution factors</small><ul>{cautions}</ul></div>'
                factor_html += '</div>'
            relief = fdate(a.get("relief_window"), True)
            stronger = fdate(a.get("stronger_window"), True)
            forward = j(a.get("future_summary") or "")
            if relief: forward += f' First material easing point: {j(relief)}.'
            if stronger: forward += f' First sustained Good-confluence checkpoint: {j(stronger)}.'
            if not stronger: forward += ' No sustained Good-confluence checkpoint is detected within the forecast horizon.'
            row_html = '<article class="aj-area">'
            row_html += f'<div class="aj-area-head"><div><b>{j(a.get("label") or a.get("area"))}</b><small>House {j(a.get("house") or "—")}</small></div>{verdict(a.get("final_judgement"))}</div>'
            row_html += f'<div class="aj-facts">{"".join("<span>"+x+"</span>" for x in facts)}</div>'
            row_html += f'<div class="aj-periods">{"".join("<span>"+x+"</span>" for x in periods)}</div>'
            row_html += f'<div class="aj-confluence"><div class="aj-confluence-title">Final confluence <b>{j(a.get("confluence_label") or a.get("final_judgement") or "insufficient").title()}</b> <small>agreement {j(a.get("confluence_agreement") or "insufficient")}</small></div><div class="aj-periods">{lane_html}</div></div>'
            future_rows = []
            for fc in (a.get("future_confluence") or [])[:16]:
                change = str(fc.get("change_type") or "continues")
                display_date = fdate(fc.get("date"), True)
                if not display_date: continue
                future_rows.append(
                    f'<div class="future-conf-row"><div class="future-conf-date">{j(display_date)}</div>'
                    f'<div class="future-conf-change {j(change)}">{j(change.replace("_"," "))}</div>'
                    f'<div><div class="future-conf-reason">{j(fc.get("reason") or "Complete confluence recalculated at this date.")}</div>'
                    f'<div class="future-conf-state">Judgement: <b>{j(str(fc.get("judgement") or "insufficient").title())}</b> · '                     f'Vimshottari {j(fc.get("vimshottari") or "—")} · Chara {j(fc.get("chara") or "—")} · Yogini {j(fc.get("yogini") or "—")}</div>'
                    f'<div class="future-conf-state">Lanes: {j(" · ".join(f"{k}: {v}" for k, v in (fc.get("lane_judgements") or {}).items()))}</div></div></div>'
                )
            future_html = (f'<div class="future-conf"><div class="future-conf-title">Future complete-confluence forecast</div>{"".join(future_rows)}</div>' if future_rows else "")
            row_html += f'<p><b>Why:</b> {j(a.get("current_summary") or "")}</p>{factor_html}<p><b>Forward:</b> {forward}</p>{future_html}</article>'
            rows.append(row_html)
        area_html="".join(rows)
    crossover_sec = f'<h3 class="aj-sub">Important crossover points</h3>{crossover_html}' if crossover_html else ''
    slow_sec = f'<h3 class="aj-sub">Slow planet transit</h3>{slow_html}' if slow_html else ''
    jai_sec = f'<h3 class="aj-sub">Jaimini judgement</h3>{jai_html}' if jai_html else ''
    dpt_sec = f'<h3 class="aj-sub">Dasha planet transit</h3><div class="aj-dpt-list">{dpt_html}</div>' if dpt_html else ''
    area_sec = f'<h3 class="aj-sub">Life-area judgement</h3><div class="aj-areas">{area_html}</div>' if area_html else ''

    return (
        '<section class="conv-block analytical-block" data-astrology-facts="1">'
        '<div class="section-kicker">ASTROLOGICAL ANALYSIS</div>'
        '<details class="analytical-details">'
        '<summary>View detailed astrological calculation</summary>'
        '<p class="sec-note">The calculations below are produced by the astrology engine. The language layer does not recalculate them.</p>'
        f'<div class="aj-clocks">{"".join(clock_rows)}</div>'
        f'{crossover_sec}{slow_sec}{jai_sec}{dpt_sec}{area_sec}'
        '</details>'
        '</section>'
    )

def _deterministic_confluence_html(aj: dict, *, today: date) -> str:
    """Render the canonical life-area confluence and future checkpoints.

    This block is Python-owned. It is intentionally rendered from
    ``life_area_judgements`` rather than from Qwen prose, so the headline
    judgement, lanes and future dates cannot drift apart.
    """
    if not isinstance(aj, dict):
        return ""
    judgement = str(aj.get("final_judgement") or "insufficient").replace("_", " ").title()
    agreement = str(aj.get("confluence_agreement") or "insufficient").replace("_", " ").title()
    lanes = aj.get("lane_judgements") or {}
    lane_order = ["Vimshottari", "Chara", "Yogini", "Slow transit", "Dasha-planet transit", "Jaimini"]
    lane_rows = []
    for key in lane_order:
        if key in lanes and str(lanes.get(key) or ""):
            lane_rows.append(
                f'<div class="evidence-row"><span class="evidence-family">{_e(key)}</span>'
                f'<span class="evidence-text">{_e(str(lanes[key]).replace("_", " ").title())}</span></div>'
            )
    future = []
    for raw in list(aj.get("future_confluence") or []):
        if not isinstance(raw, dict):
            continue
        ds = str(raw.get("date") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ds):
            continue
        try:
            d = date.fromisoformat(ds)
        except ValueError:
            continue
        if d < today:
            continue
        change = str(raw.get("change_type") or "continues").replace("_", " ").title()
        jdg = str(raw.get("judgement") or "insufficient").replace("_", " ").title()
        reason = str(raw.get("reason") or "").strip()
        lane_bits = []
        for key in lane_order:
            val = (raw.get("lane_judgements") or {}).get(key)
            if val:
                lane_bits.append(f"{key}: {str(val).replace('_',' ').title()}")
        reason_div = f'<div class="future-conf-reason">{_e(reason)}</div>' if reason else ''
        future.append(
            f'<div class="future-conf-row"><div class="future-conf-date">{_e(_fmt_full_month(ds))}</div>'
            f'<div class="future-conf-state"><b>{_e(change)}</b> · Overall: <b>{_e(jdg)}</b></div>'
            f'<div class="future-conf-state">{_e(" · ".join(lane_bits))}</div>'
            f'{reason_div}</div>'
        )
    future_html = ""
    if future:
        future_html = (
            '<div class="future-conf">'
            '<div class="future-conf-title">Future complete-confluence forecast</div>'
            '<p class="sec-note">Each dated checkpoint recalculates the complete life-area confluence. A dasha change alone never counts as improvement.</p>'
            + "".join(future) + '</div>'
        )
    return (
        '<div class="det-confluence">'
        f'<div class="det-confluence-head"><b>Complete confluence: {_e(judgement)}</b>'
        f'<span>Agreement: {_e(agreement)}</span></div>'
        '<details class="confluence-details">'
        '<summary>Astrological calculation & future checkpoints</summary>'
        f'<div class="evidence-grid">{"".join(lane_rows)}</div>'
        f'{future_html}'
        '</details>'
        '</div>'
    )


LAGNA_PROFILES: dict[str, dict[str, str]] = {
    "Aries": {
        "title": "Mesha (Aries) · The Dynamic Initiator",
        "traits": "Ruled by Mars (Mangala), your Janma Lagna endows you with high physical vitality, quick reflexes, and an innate drive to take command. You are frank, courageous, and direct in all dealings, preferring self-reliance over dependence on others.",
        "life_path": "In classical Jyotish, Mesha natives achieve their greatest fortune when leading independent enterprises, technical ventures, or commanding executive responsibilities.",
    },
    "Taurus": {
        "title": "Vrishabha (Taurus) · The Enduring Accumulator",
        "traits": "Ruled by Venus (Shukra), your Janma Lagna bestows an attractive countenance, steady endurance, refined speech, and natural financial prudence. You possess great patience and prefer proven, methodical paths to success.",
        "life_path": "Classical texts predict steady material prosperity, land and vehicle ownership, and enduring success through commerce, banking, property, or luxury trades.",
    },
    "Gemini": {
        "title": "Mithuna (Gemini) · The Agile Scholar & Trader",
        "traits": "Ruled by Mercury (Budha), your Janma Lagna confers a sharp analytical intellect, eloquent speech, and versatility in trade, writing, and calculations. You have a quick grasp of diverse subjects and thrive in dynamic environments.",
        "life_path": "Jyotish promises success through advisory roles, commercial trade, communications, analytics, diplomacy, and intellectual enterprises.",
    },
    "Cancer": {
        "title": "Karka (Cancer) · The Nurturing Guardian",
        "traits": "Ruled by the Moon (Chandra), your Janma Lagna grants deep emotional intelligence, sharp memory, protective family devotion, and strong moral grounding. You possess natural empathy and keen public intuition.",
        "life_path": "Classical Vedic astrology predicts prosperity through public service, real estate, hospitality, administrative leadership, and community welfare.",
    },
    "Leo": {
        "title": "Simha (Leo) · The Sovereign Leader",
        "traits": "Ruled by the Sun (Surya), your Janma Lagna endows you with a commanding physical aura, high self-respect, noble character, and natural leadership authority. You value honor, generosity, and justice.",
        "life_path": "Vedic texts predict high social stature, government or institutional favor, managerial command, and lasting prestige in your sphere of influence.",
    },
    "Virgo": {
        "title": "Kanya (Virgo) · The Analytical Master",
        "traits": "Ruled by Mercury (Budha), your Janma Lagna gives exceptional diagnostic precision, practical intelligence, methodical organization, and a dedication to duty. You excel at problem-solving and quality control.",
        "life_path": "Jyotish promises high success in finance, medical/healthcare, analytical science, auditing, administration, and technical advisory.",
    },
    "Libra": {
        "title": "Tula (Libra) · The Righteous Arbitrator",
        "traits": "Ruled by Venus (Shukra), your Janma Lagna confers a balanced, dignified temperament, diplomatic eloquence, refined aesthetic judgment, and an innate sense of justice and fairness.",
        "life_path": "Classical astrology predicts auspicious gains through partnerships, legal arbitration, trade, diplomacy, design, and public relations.",
    },
    "Scorpio": {
        "title": "Vrishchika (Scorpio) · The Resilient Mystic",
        "traits": "Ruled by Mars and Ketu, your Janma Lagna endows you with intense willpower, piercing investigative ability, psychological depth, and extraordinary resilience under pressure.",
        "life_path": "Vedic Jyotish predicts success in research, strategic operations, medicine/surgery, occult sciences, defense, and high-stakes crisis management.",
    },
    "Sagittarius": {
        "title": "Dhanu (Sagittarius) · The Virtuous Visionary",
        "traits": "Ruled by Jupiter (Guru), your Janma Lagna bestows high moral character, expansive wisdom, optimism, and deep respect for dharma, truth, and higher knowledge.",
        "life_path": "Classical texts predict honors in higher education, law, mentorship, spiritual institutions, publishing, and international advisory.",
    },
    "Capricorn": {
        "title": "Makara (Capricorn) · The Steadfast Builder",
        "traits": "Ruled by Saturn (Shani), your Janma Lagna gives pragmatic discipline, relentless perseverance, realistic judgment, and the endurance to scale long-term peaks.",
        "life_path": "Jyotish indicates progressive rise through structured organizations, industrial enterprises, governance, land assets, and executive administration.",
    },
    "Aquarius": {
        "title": "Kumbha (Aquarius) · The Progressive Reformer",
        "traits": "Ruled by Saturn and Rahu, your Janma Lagna endows you with a broad humanitarian outlook, sharp conceptual intellect, and independent, future-oriented thinking.",
        "life_path": "Classical astrology predicts success through large networks, institutional leadership, social reforms, scientific innovation, and global organizations.",
    },
    "Pisces": {
        "title": "Meena (Pisces) · The Intuitive Sage",
        "traits": "Ruled by Jupiter (Guru), your Janma Lagna gives a gentle, compassionate nature, deep intuitive perception, love for tranquility, and natural inclination toward spiritual, advisory, or investigative pursuits.",
        "life_path": "Vedic texts predict auspicious success in advisory roles, research, foreign trade, spiritual education, charitable leadership, and creative arts.",
    },
}

MOON_TEMPERAMENTS: dict[str, str] = {
    "Aries": "Your Moon in Aries creates a swift, courageous emotional nature with quick decision-making and straightforward honesty in relationships.",
    "Taurus": "Your exalted Moon in Taurus endows you with profound emotional stability, a peaceful disposition, strong family values, and natural financial prudence.",
    "Gemini": "Your Moon in Gemini confers a nimble, inquisitive mind, versatile wit, and talent for communication, writing, and trade.",
    "Cancer": "Your Moon in its own domicile Cancer gives deep emotional memory, strong protective family devotion, and sharp intuitive perception.",
    "Leo": "Your Moon in Leo seeks honor, warmth, and creative dignity, expressing generous loyalty to family and allies.",
    "Virgo": "Your Moon in Virgo tends to solve problems with practical intelligence, meticulous organizing, and humble service.",
    "Libra": "Your Moon in Libra instinctually seeks harmony, righteous balance, and mutually supportive companionships.",
    "Scorpio": "Your Moon in Scorpio feels with intense emotional depth, guarding inner truths and thriving through powerful spiritual rebirth.",
    "Sagittarius": "Your Moon in Sagittarius brings natural optimism, moral clarity, and an expansive quest for truth and purpose.",
    "Capricorn": "Your Moon in Capricorn maintains calm emotional restraint, high self-reliance, and channeled dedication to duty.",
    "Aquarius": "Your Moon in Aquarius evaluates life with broad intellectual perspective, seeking justice, community welfare, and true friendship.",
    "Pisces": "Your Moon in Pisces possesses deep empathy, artistic sensitivity, and spiritual yearning for higher wisdom.",
}

LAGNESHA_HOUSE_PREDICTIONS: dict[int, str] = {
    1: "Your Lagnesha is situated in the 1st House (Tanu Bhava), indicating a self-reliant, self-made destiny with strong physical vitality and prominent personal independence.",
    2: "Your Lagnesha occupies the 2nd House (Dhana Bhava), promising strong wealth accumulation karma, eloquence in speech, and deep family backing.",
    3: "Your Lagnesha sits in the 3rd House (Sahaja Bhava), granting high personal courage (Parakrama), talent in writing, trade, or technical arts, and success through your own self-directed efforts.",
    4: "Your Lagnesha resides in the 4th House (Sukha Bhava), blessing you with landed property, domestic happiness, vehicle prosperity, and strong maternal support.",
    5: "Your Lagnesha is seated in the 5th House of Poorva Punya (past meritorious deeds), promising sharp intellect, academic honors, creative talent, and happiness through progeny.",
    6: "Your Lagnesha occupies the 6th House (Shatru/Roga Bhava), conferring a warrior-like capacity to defeat competitors, overcome disputes, and rise through disciplined professional service.",
    7: "Your Lagnesha sits in the 7th House (Jaya Bhava), indicating strong commercial acumen, public popularity, and a significant rise in fortune (Bhagyodaya) through marriage and partnerships.",
    8: "Your Lagnesha occupies the 8th House (Randhra Bhava), signifying deep longevity, investigative insight, and major transformative turning points where sudden unexpected shifts unlock new fortunes.",
    9: "Your Lagnesha resides in the 9th House of Dharma & Bhagya, bestowing auspicious good fortune, moral righteousness, higher educational honors, and divine grace throughout life.",
    10: "Your Lagnesha sits in the 10th House of Karma, promising high career standing, executive authority, public prestige, and administrative leadership in your profession.",
    11: "Your Lagnesha occupies the 11th House of Labha, indicating continuous fulfillment of desires, multiple income streams, and influential social networks.",
    12: "Your Lagnesha resides in the 12th House (Moksha & Vyaya Bhava), indicating prosperity in foreign or distant lands, spiritual wisdom, and charitable inclinations.",
}


def render(
    pc: dict,
    *,
    name: str = "",
    question_html: str = "",
    price: int = 298,
    today: Optional[date] = None,
    paid: bool = False,
    proof_html: str = "",
    daily_html: str = "",
    timing_html: str = "",
    cards: Optional[list] = None,
    prose: Optional[dict] = None,
    footer_unlock: bool = True,
    remedy_html: str = "",
    analysis: Any = None,
) -> str:
    """Render the LLM report as a consultation-style reading.

    Editorial order:
        chart signature -> about you -> family/home -> current chapter ->
        mind now -> recent months -> area-by-area chart readings -> timing ->
        remedies.

    Python remains authoritative for status, houses and dates.  Qwen supplies
    interpretation and natural language only.
    """
    del question_html, proof_html, daily_html, timing_html
    today = today or date.today()
    prose = _sanitize_prose_tree(prose) if isinstance(prose, dict) else {}
    cards = list(cards or [])
    first = (name or "").split()[0] if name else "You"

    lagna = str((pc.get("lagna") or {}).get("sign") or "")
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    moon_sign = str(moon.get("sign") or "")
    nakshatra = str(moon.get("nakshatra") or moon.get("nakshatra_name") or "")

    # Use the SAME authoritative timing object that the analytical block uses.
    # If analysis is present, it wins over raw pc snapshots and over a second
    # independent calculation in the renderer. This prevents current-chapter
    # dates from drifting away from the life-area/confluence engine.
    md_lord = ad_lord = md_end = next_vim = ""
    try:
        adata_for_clock = analysis.model_dump(mode="json") if hasattr(analysis, "model_dump") else (analysis if isinstance(analysis, dict) else {})
        timing_rows = adata_for_clock.get("timing_systems") or [] if isinstance(adata_for_clock, dict) else []
        vim_row = next((x for x in timing_rows if isinstance(x, dict) and str(x.get("system") or "") == "vimshottari"), None)
        if vim_row:
            parts = [x for x in str(vim_row.get("current") or "").split("-") if x]
            md_lord = parts[0] if parts else ""
            ad_lord = parts[1] if len(parts) > 1 else ""
            md_end = str(vim_row.get("current_end") or "")
            next_vim = str(vim_row.get("next") or "")
    except Exception:
        pass
    if not md_lord:
        try:
            from llm.facts import _dasha_clock_facts
            _clocks = _dasha_clock_facts(pc, today)
            _vim_clock = next((c for c in _clocks if c.system == "vimshottari"), None)
            if _vim_clock:
                _parts = [x for x in str(_vim_clock.current or "").split("-") if x]
                md_lord = _parts[0] if _parts else ""
                ad_lord = _parts[1] if len(_parts) > 1 else ""
                md_end = str(_vim_clock.current_end or "")
                next_vim = str(_vim_clock.next or "")
        except Exception:
            pass
    # Never fall back to legacy current_md/current_md_antardashas here. If the
    # authoritative date-aware engine is unavailable, omit the timing line
    # rather than reintroducing stale dasha facts.
    authoritative_timing_text = ""
    if md_lord and ad_lord:
        authoritative_timing_text = f"{md_lord}–{ad_lord} is the active dasha sequence."
    elif md_lord:
        authoritative_timing_text = f"{md_lord} is the active mahadasha."
    if md_end:
        shown_end = _fmt_full_month(md_end) or md_end
        authoritative_timing_text += (" " if authoritative_timing_text else "") + f"It runs through {shown_end}."
    if next_vim:
        authoritative_timing_text += (" " if authoritative_timing_text else "") + f"Next Vimshottari period: {next_vim}."

    chips = []
    if lagna:
        chips.append(f"{lagna} rising")
    if moon_sign:
        chips.append(f"Moon in {moon_sign}")
    if nakshatra:
        chips.append(f"Nakshatra: {nakshatra}")
    if md_lord:
        chips.append(f"{md_lord} Mahadasha")
    if ad_lord:
        chips.append(f"{ad_lord} Antardasha")
    chips = chips[:6]

    chart_line = " · ".join(chips[:3]) or "Birth chart"

    personality = _sanitize_customer_text(prose.get("personality"))
    astrological_basis = _sanitize_customer_text(prose.get("astrological_basis"))
    if astrological_basis:
        import re
        astrological_basis = re.sub(
            r"Saturn transiting [^.]*?until \w+ 203\d",
            "Saturn transiting your 10th house of career through early 2028, alongside the longer timing cycle running through 2031",
            astrological_basis,
            flags=re.I,
        )
        astrological_basis = re.sub(
            r"Saturn's transit through [^.]*?until \w+ 203\d",
            "Saturn's transit through your 10th house of career through early 2028, alongside the longer timing cycle running through 2031",
            astrological_basis,
            flags=re.I,
        )
    interpretation = _sanitize_customer_text(prose.get("interpretation"))
    current_phase = _sanitize_customer_text(prose.get("current_phase"))
    recent_months = _sanitize_customer_text(prose.get("recent_months"))
    hardest = _sanitize_customer_text(prose.get("hardest_area_note"))
    why_now = _sanitize_customer_text(prose.get("why_now"))
    mind_now = [_sanitize_customer_text(x) for x in prose.get("mind_now", []) if str(x).strip()]
    family_note = [_sanitize_customer_text(x) for x in prose.get("family_note", []) if str(x).strip()]
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    if not astrological_basis:
        basis_bits = []
        if lagna:
            basis_bits.append(f"{lagna} lagna")
        if moon_sign:
            basis_bits.append(f"Moon in {moon_sign}")
        if nakshatra:
            basis_bits.append(f"{nakshatra} nakshatra")
        if md_lord:
            basis_bits.append(f"{md_lord} mahadasha")
        if ad_lord:
            basis_bits.append(f"{ad_lord} antardasha")
        astrological_basis = (
            "Your reading starts with "
            + ", ".join(basis_bits)
            + ". These factors describe the chart's baseline and the period running through it."
            if basis_bits
            else "Your birth chart is the foundation of this reading."
        )

    lagna_clean = lagna or "Aries"
    lp = LAGNA_PROFILES.get(lagna_clean, LAGNA_PROFILES["Aries"])
    mp = MOON_TEMPERAMENTS.get(moon_sign, "")
    from astro_precompute import SIGN_LORDS, get_dignity
    lord = SIGN_LORDS.get(lagna_clean, "Sun")
    lord_data = pc.get("planets", {}).get(lord, {})
    lord_s = str(lord_data.get("sign") or "")
    lord_h = int(lord_data.get("house") or 1)
    lord_d = get_dignity(lord, lord_s) if lord_s else ""
    ordinals = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th", 6: "6th", 7: "7th", 8: "8th", 9: "9th", 10: "10th", 11: "11th", 12: "12th"}
    h_str = ordinals.get(lord_h, f"House {lord_h}")
    d_str = f" in {lord_d.replace('_', ' ')}" if lord_d in ("exalted", "moolatrikona", "own_sign", "debilitated") else ""
    h_pred = LAGNESHA_HOUSE_PREDICTIONS.get(lord_h, f"Your Lagnesha sits in the {h_str} house, shaping your life priorities.")
    
    moon_txt = f" and <b>Moon in {moon_sign}</b>" if moon_sign else ""
    nak_txt = f" (under <b>{nakshatra}</b> nakshatra)" if nakshatra else ""
    
    about_meaning = (
        f"With <b>{lagna_clean} rising</b>{moon_txt}{nak_txt}, your birth chart establishes <b>{lp['title']}</b>. "
        f"{lp['traits']} <b>{h_pred}</b> (governed by Lagna lord <b>{lord} in the {h_str} house, {lord_s}{d_str}</b>)."
    )
    if not personality:
        personality = (
            f"{lp['life_path']} {mp} In classical Vedic astrology, while planetary periods (Dashas) and transits (Gochara) bring shifting life chapters, "
            f"your Janma Lagna and Moon disposition define your enduring constitutional baseline and natural karma."
        )

    mind_sub_html = ""
    if mind_now:
        mind_sub_html = f"""
        <div style="margin-top:18px;border-top:1px solid #e0ded8;padding-top:14px">
          <div style="font-size:0.7rem;letter-spacing:.12em;text-transform:uppercase;color:#8a6a1f;font-weight:700;margin-bottom:6px">WHAT MAY BE OCCUPYING YOUR MIND</div>
          <p class="sec-note" style="margin-bottom:8px">These are chart-activated possibilities, not private facts we assume about you.</p>
          <ul class="conv-mind">
            {"".join(f"<li>{_e(x)}</li>" for x in mind_now[:3])}
          </ul>
        </div>
        """

    current_html = ""
    if current_phase or why_now or md_lord or authoritative_timing_text or mind_now:
        current_html = f"""
        <section class="conv-block current-block">
          <div class="section-kicker">YOUR CURRENT CHAPTER</div>
          <h2 id="sec-your-current-chapter">Where life is putting its weight right now</h2>
          {f'<p class="fact-lead"><span class="ev-label">Current timing</span> {_e(authoritative_timing_text)}</p>' if authoritative_timing_text else ""}
          {f'<p class="lead-reading">{_e(current_phase)}</p>' if current_phase else ""}
          {f'<div class="why-now"><span class="ev-label">Why this period feels this way</span><p>{_e(why_now)}</p></div>' if why_now else ""}
          {f'<p class="hardest">{_e(hardest)}</p>' if hardest else ""}
          {mind_sub_html}
        </section>
        """

    recent_html = ""
    if recent_months:
        recent_html = f"""
        <section class="conv-block">
          <div class="section-kicker">RECENTLY</div>
          <h2 id="sec-recently">The last few months</h2>
          <p>{_e(recent_months)}</p>
        </section>
        """

    def card_for(area):
        return next((c for c in cards if getattr(c, "area", "") == area), None)

    def timing_for(card, block):
        # Exact timing is Python-owned. Do not render model-written dates.
        windows = _card_windows(card) if card is not None else []
        phrases = [_fmt_when(*w) for w in windows if _fmt_when(*w)]
        if phrases:
            return " · ".join(phrases)
        t = str((block or {}).get("timing") or "").strip()
        if t and not re.search(r"\b(?:19|20)\d{2}\b", t):
            return t
        return "The timing engine has not supplied an exact window for this area."

    def evidence_html(card):
        if card is None:
            return ""
        rows = []
        for ev in list(getattr(card, "evidence", None) or [])[:6]:
            text = str(getattr(ev, "text", "") or "").strip()
            if not text:
                tags = [
                    str(x).replace("_", " ")
                    for x in (getattr(ev, "semantic_tags", None) or [])
                    if str(x).strip() and str(x).lower() not in ("contested",)
                ]
                text = ", ".join(tags[:4])
            if not text:
                continue
            low = text.lower()
            if any(k in low for k in _EVIDENCE_LEAK):
                continue
            family = str(getattr(ev, "family", "") or "Evidence").replace("_", " ").title()
            rows.append(
                f'<div class="evidence-row"><span class="evidence-family">{_e(family)}</span>'
                f'<span class="evidence-text">{_e(text)}</span></div>'
            )
        promise = _card_status(card)
        activation = _card_activation(card)
        direction = _card_direction(card)
        agreement = _card_agreement(card)
        return f"""
        <details class="why-chart">
          <summary>Why this reads this way</summary>
          <div class="evidence-grid">
            <div class="evidence-row"><span class="evidence-family">Promise</span><span class="evidence-text">{_e(_readable_status(promise))}</span></div>
            <div class="evidence-row"><span class="evidence-family">Activation</span><span class="evidence-text">{_e(_activation_phrase(card, activation, today))}</span></div>
            <div class="evidence-row"><span class="evidence-family">Direction</span><span class="evidence-text">{_e(_readable_status(direction))}</span></div>
            <div class="evidence-row"><span class="evidence-family">Agreement</span><span class="evidence-text">{_e(agreement.replace('_', ' '))}</span></div>
            {"".join(rows)}
          </div>
        </details>
        """

    area_rows = []
    analysis_area_map = {}
    if analysis is not None:
        try:
            adata = analysis.model_dump(mode="json") if hasattr(analysis, "model_dump") else (analysis if isinstance(analysis, dict) else {})
            analysis_area_map = {str(x.get("area") or ""): x for x in (adata.get("life_area_judgements") or []) if isinstance(x, dict)}
        except Exception:
            analysis_area_map = {}
    if paid:
        ordered = [str(getattr(c, "area", "") or "") for c in cards if getattr(c, "area", "")]
        for area in ordered:
            card = card_for(area)
            block = areas.get(area) if isinstance(areas.get(area), dict) else {}

            basis = _sanitize_customer_text(block.get("astrological_basis"))
            interp = _sanitize_customer_text(block.get("interpretation"))
            outlook = _sanitize_customer_text(block.get("outlook"))
            manifestation = _sanitize_customer_text(block.get("manifestation"))
            remedy = _sanitize_customer_text(block.get("remedy"))

            if not basis:
                pnames = _card_planets(card) if card is not None else []
                house = int(getattr(card, "house", 0) or 0) if card else 0
                parts = []
                if pnames:
                    parts.append(", ".join(str(x) for x in pnames[:4]))
                if house:
                    parts.append(f"house {house}")
                basis = "The supplied chart factors for this area" + (
                    " include " + " in ".join(parts) + "."
                    if parts else "."
                )
            if not interp:
                interp = str(getattr(card, "outlook_line", "") or "").strip()
            if not outlook:
                outlook = str(getattr(card, "outlook_line", "") or "").strip()
            if not manifestation:
                manifestation = "; ".join(
                    str(x) for x in list(getattr(card, "manifestations", None) or [])[:2]
                )

            status = _card_status(card) if card is not None else "insufficient_evidence"
            activation = _card_activation(card) if card is not None else "inactive"
            house = int(getattr(card, "house", 0) or 0)
            timing = timing_for(card, block)
            activation_txt = _activation_phrase(card, activation, today)
            aj = analysis_area_map.get(area) or {}
            if aj:
                fact_line = (
                    f"Final confluence: {str(aj.get('confluence_label') or aj.get('final_judgement') or 'insufficient').replace('_',' ').title()} "
                    f"· Natal promise: {str(aj.get('natal_promise') or status).replace('_',' ').title()} "
                    f"· Current activation: {str(aj.get('activation_label') or 'Not clearly active').replace('_',' ').title()}"
                )
                confluence_html = _deterministic_confluence_html(aj, today=today)
                area_pill = _confluence_pill(aj)
            else:
                fact_line = (
                    f"House {house or '—'} · Birth chart: {_readable_status(status)} "
                    f"· Timing: {activation_txt}"
                )
                confluence_html = ""
                area_pill = _pill(block, card, today)

            # Customer-facing life areas are intentionally compact: one LLM-written
            # consultation conclusion plus one remedy. Deterministic calculation
            # detail remains available under the collapsed confluence block.
            conclusion = _sanitize_customer_text(block.get("conclusion"))
            if not conclusion:
                conclusion = _sanitize_customer_text(outlook or interp or basis)

            help_text = remedy or _fallback_help(card, _area_label(area, cards))
            remedy_html_area = (
                f'<div class="consultation-remedy"><span class="ev-label">Remedy / what helps</span>'
                f'<p>{_e(help_text)}</p></div>' if help_text else ""
            )

            area_rows.append(f"""
            <article class="card conv-area">
              <div class="card-top">
                <span class="area">{_e(_area_label(area, cards))}</span>
                {area_pill}
              </div>
              <div class="consultation-conclusion">
                <div class="reading-label">Astrologer's conclusion</div>
                <p>{_e(conclusion)}</p>
                {remedy_html_area}
              </div>
              {confluence_html}
            </article>
            """)

    areas_html = ""
    if area_rows:
        areas_html = f"""
        <section class="conv-block areas-block">
          <div class="section-kicker">THE ROAD AHEAD</div>
          <h2>Each important part of your life</h2>
          <p class="sec-note">Each area gives one astrologer-style conclusion and one practical remedy. The detailed calculation stays available under the collapsed astrology section.</p>
          {"".join(area_rows)}
        </section>
        """

    unlock = ""
    if not paid and footer_unlock:
        unlock = f"""
        <section class="buy" id="unlock">
          <h3>See the full reading, area by area</h3>
          <p>The free reading shows who you are, the chapter you are in and what the chart is activating.
          The full reading adds the confluence, timing and practical guidance for every life area.</p>
          <a class="cta" href="#unlock" data-unlock="1">Unlock full reading · ₹{_e(price)}</a>
        </section>
        """

    locked_html = ""
    if not paid and cards:
        teaser_cards = _free_area_teaser(cards, today)
        if teaser_cards:
            locked_html = f"""
        <section class="conv-block areas-block">
          <div class="section-kicker">THE ROAD AHEAD</div>
          <h2>Each important part of your life</h2>
          <p class="sec-note">Each area gives one astrologer-style conclusion and one practical remedy. The detailed calculation stays available under the collapsed astrology section.</p>
          {teaser_cards}
        </section>
            """

    divisional_html = ""
    try:
        from divisional_profile import render_divisional_about_you_html
        divisional_html = render_divisional_about_you_html(pc, paid=paid)
    except Exception as exc:
        print(f"[report_conversational] divisional profile skipped: {exc}", flush=True)

    date_str = f"{today:%d %B %Y}" if today else ""

    body = f"""
    <header>
      <div class="eyebrow">Your Vedic reading</div>
      <h1>{_e(first)}, here is what your chart is saying.</h1>
      <div class="chartline">{_e(chart_line)} · read {_e(date_str)}</div>
    </header>

    <section class="hero">
      <div class="section-kicker hero-kicker">YOUR CHART SIGNATURE</div>
      <div class="chart-signature">
        {"".join(f'<span class="chart-chip">{_e(x)}</span>' for x in chips)}
      </div>
      <p>{_e(astrological_basis)}</p>
    </section>

    {_analytical_html(analysis, paid=paid, today=today)}

    <section class="conv-block about-you">
      <div class="section-kicker">ABOUT YOU &amp; LIFE FOUNDATIONS</div>
      <h2 id="sec-about-you">Who you are beneath the current period</h2>
      <p class="lead-reading"><span class="ev-label">Constitutional Core</span> {about_meaning}</p>
      {f'<p style="margin:12px 0 14px;font-size:0.92rem;line-height:1.6;color:#2c3140;">{personality}</p>' if personality and personality != about_meaning else ""}
      {divisional_html}
    </section>

    {current_html}
    {recent_html}
    {areas_html}
    {remedy_html}
    {locked_html}
    {unlock}

    <footer>Astrological interpretation from your supplied birth details · guidance, not a substitute for professional advice</footer>
    """

    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_e(first)} — your Vedic reading</title>
<style>{_STYLE}{_EXTRA}
.conv-block{{margin:30px 0}}
.conv-block h2{{font-family:Georgia,serif;font-size:1.3rem;line-height:1.25;margin:6px 0 12px;color:#1f2430}}
.conv-block p{{margin:0 0 11px;line-height:1.65;color:#2c3140;font-size:.95rem}}
.hero{{background:#16181d;color:#f7f5f1;border-radius:15px;padding:20px 21px;margin:18px 0 30px}}
.hero p{{color:#f7f5f1;opacity:.9;margin:9px 0 0}}
.hero-kicker{{color:#d6c5a3!important}}
.chart-signature{{display:flex;flex-wrap:wrap;gap:7px;margin:9px 0}}
.chart-chip{{display:inline-block;padding:5px 9px;border:1px solid rgba(214,197,163,.35);border-radius:999px;background:rgba(214,197,163,.09);font-size:.74rem;color:#eee4d2}}
.fact-lead{{background:#f6f4ef;border-radius:9px;padding:11px 12px}}
.lead-reading{{font-family:Georgia,serif;font-size:1.05rem!important;line-height:1.58!important}}
.hardest{{font-weight:700}}
.conv-mind{{margin:0;padding-left:20px}}
.conv-mind li{{margin:0 0 8px;line-height:1.55;color:#2c3140;font-size:.95rem}}
.family-item{{padding:10px 0;border-bottom:1px solid var(--line)}}
.family-item:last-child{{border-bottom:0}}
.family-label{{font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;color:#8a6a1f;font-weight:700;margin-bottom:4px}}
.family-item p{{margin:0}}
.card.conv-area{{margin:14px 0;padding:18px 20px}}
.area-fact{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;padding:8px 10px;border-radius:8px;background:#f6f4ef;color:#3d4250;font-size:.76rem}}
.mini-label{{font-size:.64rem;letter-spacing:.11em;text-transform:uppercase;color:#6a7080;font-weight:700}}
.area-reading{{margin:12px 0}}
.reading-label{{font-size:.68rem;letter-spacing:.11em;text-transform:uppercase;color:#8a6a1f;font-weight:700;margin-bottom:6px}}
.astro-basis{{font-size:.86rem!important;color:#4a4e58!important;margin-bottom:8px!important}}
.interpretation{{font-family:Georgia,serif;font-size:1.05rem!important;line-height:1.55!important}}
.outlook{{font-size:.88rem!important}}
.area-timing,.area-manifest,.area-help{{margin-top:12px;padding:10px 12px;border-radius:9px;background:#faf8f4}}
.area-timing p,.area-manifest p,.area-help p{{margin:4px 0 0;font-size:.86rem}}
.why-chart{{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}}
.why-chart summary{{cursor:pointer;font-size:.78rem;color:#6a7080;font-weight:600}}
.evidence-grid{{margin-top:9px}}
.evidence-row{{display:grid;grid-template-columns:100px 1fr;gap:8px;padding:7px 0;border-top:1px solid #eeeae3;font-size:.78rem}}
.evidence-row:first-child{{border-top:0}}
.evidence-family{{font-weight:700;color:#66625c}}
.evidence-text{{color:#3d4250}}
.window-list{{display:grid;gap:10px}}
.window{{background:#fff;border:1px solid var(--line);border-left:4px solid #8a6a1f;border-radius:11px;padding:13px 15px}}
.window.up{{border-left-color:#1c6b45}} .window.down{{border-left-color:#a3341f}}
.window .when{{font-size:.72rem;font-weight:700;color:#6a7080}}
.window h3{{font-family:Georgia,serif;font-size:1rem;margin:4px 0}}
.window p{{font-size:.84rem;margin:0;color:#3d4250}}
.why-now{{margin:12px 0;padding:12px 13px;background:#f6f4ef;border-radius:9px}}
.analytical-block{{background:#fffdfa;border:1px solid #e4ded3;border-radius:15px;padding:20px}}
.analytical-details{{margin-top:8px}}
.analytical-details summary{{cursor:pointer;font-family:Georgia,serif;font-size:1.05rem;color:#292d36;padding:8px 0}}

.aj-clocks{{display:grid;gap:9px;margin:14px 0}} .aj-clock{{display:grid;grid-template-columns:1.2fr 1.3fr .8fr auto;gap:10px;align-items:center;padding:11px 12px;background:#f7f4ed;border:1px solid #e4ded3;border-radius:10px}} .aj-clock>div{{display:grid;gap:2px}} .aj-clock span{{font-family:Georgia,serif;font-size:1.05rem}} .aj-clock small,.aj-area small,.aj-table small{{display:block;color:#77736c;font-size:.65rem;text-transform:uppercase;letter-spacing:.06em}} .aj-clock-next{{grid-template-columns:auto auto auto auto!important;align-items:center}}
.aj-verdict{{display:inline-block;padding:4px 8px;border-radius:99px;font-size:.64rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;background:#ebe7df;color:#625c52}} .aj-verdict.good{{background:#dcefe3;color:#1c6b45}} .aj-verdict.bad{{background:#f5ddd8;color:#9d3b28}} .aj-verdict.mid{{background:#eee7d4;color:#80651e}}
.aj-sub{{font-family:Georgia,serif;font-size:1rem;margin:22px 0 9px;color:#292d36}} .aj-cross-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}} .aj-cross{{padding:10px 11px;border:1px solid #e4ded3;border-radius:9px;background:#fff}} .aj-cross b,.aj-cross span,.aj-cross small{{display:block}} .aj-cross b{{font-family:Georgia,serif;font-size:1rem}} .aj-cross span{{font-size:.72rem;color:#8a6a1f;margin-top:3px}} .aj-cross small{{font-size:.68rem;color:#77736c;margin-top:4px}}
.aj-table{{width:100%;border-collapse:collapse;font-size:.76rem;background:#fff;border:1px solid #e4ded3}} .aj-table th,.aj-table td{{padding:8px;border-bottom:1px solid #eee9e1;text-align:left;vertical-align:top}} .aj-table th{{font-size:.62rem;text-transform:uppercase;letter-spacing:.06em;color:#77736c}}
.aj-jai{{padding:12px;background:#f7f4ed;border:1px solid #e4ded3;border-radius:10px}} .aj-karakas,.aj-jai-meta,.aj-facts,.aj-periods{{display:flex;flex-wrap:wrap;gap:7px}} .aj-karakas span,.aj-jai-meta span,.aj-facts span,.aj-periods span{{padding:5px 8px;border:1px solid #e3ddd2;border-radius:99px;background:#fff;font-size:.68rem;color:#5f5a52}} .aj-jai p{{font-family:Georgia,serif;font-size:.88rem!important;margin:10px 0 0!important}}
.aj-dpt-list,.aj-areas{{display:grid;gap:7px}} .aj-dpt{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:9px 10px;border:1px solid #e4ded3;border-radius:9px;background:#fff;font-size:.73rem}} .aj-dpt span{{color:#6f6a62}} .aj-area{{padding:12px;background:#fff;border:1px solid #e4ded3;border-radius:10px}} .aj-area-head{{display:flex;justify-content:space-between;gap:10px;align-items:center}} .aj-area-head>div{{display:grid;gap:2px}} .aj-facts,.aj-periods{{margin:9px 0 0}} .aj-facts span,.aj-periods span{{border-radius:8px}} .aj-area p{{font-size:.82rem!important;margin:8px 0 0!important}} .aj-confluence{{margin:12px 0;padding:12px;border:1px solid #e4ded3;background:#fbfaf6;border-radius:9px}} .aj-confluence-title{{font-size:.76rem}} .aj-confluence-title small{{margin-left:8px;color:#77736c;font-weight:normal}} .aj-factor-cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0}} .aj-factor-cols small{{font-size:.65rem;text-transform:uppercase;letter-spacing:.1em;color:#77736c}} .aj-factor-cols ul{{margin:6px 0;padding-left:18px;color:#6b665e;font-size:.72rem}}
@media(max-width:680px){{.aj-clock{{grid-template-columns:1fr 1fr}} .aj-table{{font-size:.68rem}}}}
{TRANSITION_MAP_CSS}
@media(max-width:520px){{.evidence-row{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">{body}</div>{_INTERACT}</body></html>"""

    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)
