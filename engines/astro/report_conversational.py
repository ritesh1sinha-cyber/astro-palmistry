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
.transition-note{margin-top:6px;padding:10px 11px;background:#f1eee7;border-radius:9px}
.transition-note p{font-family:Georgia,serif;font-size:.87rem!important;margin:4px 0 0!important;line-height:1.5!important}
.lane-key{font-size:.68rem!important;color:#6a7080!important;margin:0 0 12px!important;line-height:1.45!important}
.conf-line{display:none}
@media(max-width:520px){.lane-chart{display:none}.lane-key{display:none}.ctx-row{grid-template-columns:1fr}
.conf-line{display:block;font-size:.72rem!important;color:#8a6a1f!important;font-weight:600;margin:0 0 10px!important}}
""".strip()


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
              <div class="transition-phase">{_e(field_of(t, "phase") or "Transition")}</div>
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
            return f"Not yet on — the demanding stretch begins {state['opens']}"
        # "Promised" is a claim about the birth chart, so it can only be used
        # where the chart actually made that promise.
        if _card_status(card) in ("weak", "insufficient_evidence"):
            return f"Not active — the next dated shift is {state['opens']}"
        return f"Promised, not yet active — opens {state['opens']}"
    return _readable_status(activation)


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
    prose = prose if isinstance(prose, dict) else {}
    cards = list(cards or [])
    first = (name or "").split()[0] if name else "You"

    lagna = str((pc.get("lagna") or {}).get("sign") or "")
    planets = pc.get("planets") or {}
    moon = planets.get("Moon") or {}
    moon_sign = str(moon.get("sign") or "")
    nakshatra = str(moon.get("nakshatra") or moon.get("nakshatra_name") or "")

    vim = pc.get("vimshottari") or {}
    md = vim.get("current_md") or {}
    ads = vim.get("current_md_antardashas") or []
    if not isinstance(md, dict):
        md = {}
    if not isinstance(ads, list):
        ads = []
    ad = next(
        (x for x in ads if isinstance(x, dict) and x.get("status") == "current"),
        ads[0] if ads else {},
    )
    if not isinstance(ad, dict):
        ad = {}

    md_lord = str(md.get("md_lord") or md.get("lord") or "")
    ad_lord = str(ad.get("ad_lord") or ad.get("lord") or "")
    md_end = str(md.get("end") or "").strip()

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

    personality = str(prose.get("personality") or "").strip()
    astrological_basis = str(prose.get("astrological_basis") or "").strip()
    interpretation = str(prose.get("interpretation") or "").strip()
    current_phase = str(prose.get("current_phase") or "").strip()
    recent_months = str(prose.get("recent_months") or "").strip()
    hardest = str(prose.get("hardest_area_note") or "").strip()
    why_now = str(prose.get("why_now") or "").strip()
    mind_now = [str(x).strip() for x in prose.get("mind_now", []) if str(x).strip()]
    family_note = [str(x).strip() for x in prose.get("family_note", []) if str(x).strip()]
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

    about_meaning = interpretation or personality
    if not about_meaning:
        about_meaning = (
            "The important distinction is between your underlying chart pattern "
            "and the temporary period you are moving through."
        )

    family_html = ""
    if family_note:
        labels = _family_labels(len(family_note))
        limit = len(family_note) if paid else min(2, len(family_note))
        items = []
        for i, line in enumerate(family_note[:limit]):
            label = labels[i] if i < len(labels) else "Family"
            items.append(
                f'<div class="family-item"><div class="family-label">{_e(label)}</div>'
                f"<p>{_e(line)}</p></div>"
            )
        more = (
            ""
            if paid or len(family_note) <= limit
            else '<p class="sec-note">The full reading also covers the remaining '
            "family relationships and the home environment.</p>"
        )
        family_html = f"""
        <section class="conv-block family-block">
          <div class="section-kicker">FAMILY & HOME</div>
          <h2>The people and home that shaped you</h2>
          <p class="sec-note">These are chart-derived patterns, not facts we were given about your family.</p>
          {"".join(items)}
          {more}
        </section>
        """

    current_html = ""
    if current_phase or why_now or md_lord:
        period_line = ""
        if md_lord and ad_lord:
            period_line = f"{md_lord}–{ad_lord} is the active dasha sequence."
        elif md_lord:
            period_line = f"{md_lord} is the active mahadasha."

        timing_bits = period_line
        if md_end:
            shown_end = _fmt_full_month(md_end) or md_end
            timing_bits = (timing_bits + " " if timing_bits else "") + f"It runs through {shown_end}."
        current_html = f"""
        <section class="conv-block current-block">
          <div class="section-kicker">YOUR CURRENT CHAPTER</div>
          <h2>Where life is putting its weight right now</h2>
          {f'<p class="fact-lead"><span class="ev-label">Current timing</span> {_e(timing_bits)}</p>' if timing_bits else ""}
          {f'<p class="lead-reading">{_e(current_phase)}</p>' if current_phase else ""}
          {f'<div class="why-now"><span class="ev-label">Why this period feels this way</span><p>{_e(why_now)}</p></div>' if why_now else ""}
          {f'<p class="hardest">{_e(hardest)}</p>' if hardest else ""}
        </section>
        """

    mind_html = ""
    if mind_now:
        mind_html = f"""
        <section class="conv-block">
          <div class="section-kicker">RIGHT NOW</div>
          <h2>What may be occupying your mind</h2>
          <p class="sec-note">These are chart-activated possibilities, not private facts we assume about you.</p>
          <ul class="conv-mind">
            {"".join(f"<li>{_e(x)}</li>" for x in mind_now[:3])}
          </ul>
        </section>
        """

    recent_html = ""
    if recent_months:
        recent_html = f"""
        <section class="conv-block">
          <div class="section-kicker">RECENTLY</div>
          <h2>The last few months</h2>
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
    if paid:
        ordered = [str(getattr(c, "area", "") or "") for c in cards if getattr(c, "area", "")]
        for area in ordered:
            card = card_for(area)
            block = areas.get(area) if isinstance(areas.get(area), dict) else {}

            basis = str(block.get("astrological_basis") or "").strip()
            interp = str(block.get("interpretation") or "").strip()
            outlook = str(block.get("outlook") or "").strip()
            manifestation = str(block.get("manifestation") or "").strip()
            remedy = str(block.get("remedy") or "").strip()

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
            fact_line = (
                f"House {house or '—'} · underlying promise: {_readable_status(status)} "
                f"· current activation: {activation_txt}"
            )

            # The map prints every window with its own dates, so a separate
            # timing strip above it only repeats the first row.
            map_html = _transition_map_html(pc, card, block)
            timing_html_area = "" if map_html else f"""
              <div class="area-timing">
                <span class="ev-label">Timing</span>
                <p>{_e(timing)}</p>
              </div>"""

            remedy_html_area = ""
            help_text = remedy or _fallback_help(card, _area_label(area, cards))
            if help_text:
                remedy_html_area = (
                    f'<div class="area-help"><span class="ev-label">What helps</span>'
                    f'<p>{_e(help_text)}</p></div>'
                )

            area_rows.append(f"""
            <article class="card conv-area">
              <div class="card-top">
                <span class="area">{_e(_area_label(area, cards))}</span>
                {_pill(block, card, today)}
              </div>
              <div class="area-fact"><span class="mini-label">Chart result</span>{_e(fact_line)}</div>
              <div class="area-reading">
                <div class="reading-label">What the chart is saying</div>
                <p class="astro-basis">{_e(basis)}</p>
                <p class="interpretation">{_e(interp)}</p>
                {f'<p class="outlook"><b>So, in practical terms:</b> {_e(outlook)}</p>' if outlook else ""}
              </div>
              {timing_html_area}
              {map_html}
              {f'<div class="area-manifest"><span class="ev-label">How this can show up</span><p>{_e(manifestation)}</p></div>' if manifestation else ""}
              {remedy_html_area}
              {evidence_html(card)}
            </article>
            """)

    areas_html = ""
    if area_rows:
        areas_html = f"""
        <section class="conv-block areas-block">
          <div class="section-kicker">THE ROAD AHEAD</div>
          <h2>Each important part of your life</h2>
          <p class="sec-note">The chart result is kept separate from the interpretation, so the reading remains a chart reading rather than a collection of philosophical statements.</p>
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

    body = f"""
    <header>
      <div class="eyebrow">Your Vedic reading</div>
      <h1>{_e(first)}, here is what your chart is saying.</h1>
      <div class="chartline">{_e(chart_line)} · read {today:%d %B %Y}</div>
    </header>

    <section class="hero">
      <div class="section-kicker hero-kicker">YOUR CHART SIGNATURE</div>
      <div class="chart-signature">
        {"".join(f'<span class="chart-chip">{_e(x)}</span>' for x in chips)}
      </div>
      <p>{_e(astrological_basis)}</p>
    </section>

    <section class="conv-block about-you">
      <div class="section-kicker">ABOUT YOU</div>
      <h2>Who you are beneath the current period</h2>
      <p class="fact-lead"><span class="ev-label">What the chart shows</span> {_e(astrological_basis)}</p>
      <p class="lead-reading"><span class="ev-label">What it means for you</span> {_e(about_meaning)}</p>
      {f'<p>{_e(personality)}</p>' if personality and personality != about_meaning else ""}
    </section>

    {family_html}
    {current_html}
    {mind_html}
    {recent_html}
    {areas_html}
    {remedy_html if paid else ""}
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
{TRANSITION_MAP_CSS}
@media(max-width:520px){{.evidence-row{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">{body}</div>{_INTERACT}</body></html>"""

    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)
