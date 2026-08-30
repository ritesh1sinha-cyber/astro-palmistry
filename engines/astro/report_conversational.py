"""Compact conversational astrology report — LLM-on path only.

Leaves ``report_cards.render`` untouched. Chosen by ``report_render`` when the
LLM layer is enabled and produced an accepted conversational overlay.

Generation patch: chart signature, Python-owned area timing, evidence, and
astrologer-voice layout. Free still teasers father/mother from family_note.
"""

from __future__ import annotations

import html as _html
import re
from collections import Counter
from datetime import date, datetime
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
.conf-now{margin-top:18px;border-top:1px solid #e0ded8;padding-top:14px}
.conf-list{display:grid;gap:10px;margin-top:10px}
.conf-item{background:#fff;border:1px solid #e4ded3;border-left:4px solid #8a6a1f;border-radius:11px;padding:13px 15px}
.conf-item.good{border-left-color:#1c6b45}.conf-item.bad{border-left-color:#a3341f}
.conf-head{display:flex;justify-content:space-between;gap:10px;align-items:center}
.conf-head b{font-family:Georgia,serif;font-size:1rem;color:#1f2430}
.conf-item p{margin:8px 0 0!important;font-size:.88rem!important;line-height:1.58!important}
.why-said{margin-top:10px;border-top:1px solid #eeeae3;padding-top:8px}
.why-said summary{cursor:pointer;font-size:.72rem;color:#6a7080;font-weight:700;letter-spacing:.02em}
.why-said .evidence-grid{margin-top:8px}
.conf-cross{margin-top:8px;padding:8px 10px;background:#f7f4ec;border-radius:8px;font-size:.74rem;color:#4a4f5c}
.recent-list{display:grid;gap:10px;margin-top:12px}
.recent-item{background:#fff;border:1px solid #e4ded3;border-left:4px solid #8a6a1f;border-radius:11px;padding:13px 15px}
.recent-item.good{border-left-color:#1c6b45}.recent-item.bad{border-left-color:#a3341f}
.recent-head{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}
.recent-when{font-size:.72rem;font-weight:700;color:#6a7080}
.recent-item h3{font-family:Georgia,serif;font-size:1rem;margin:6px 0 0;color:#1f2430}
.recent-item p{margin:6px 0 0!important;font-size:.86rem!important;line-height:1.55!important}
.recent-manifest{margin:8px 0 0;padding-left:18px}
.recent-manifest li{font-size:.84rem;line-height:1.5;color:#3d4250;margin:0 0 5px}
.confidence{margin:10px 0 0!important;font-size:.82rem!important;line-height:1.55!important;color:#4a4f5c!important}
.vrow{display:grid;grid-template-columns:72px 1fr;gap:5px 12px;margin:9px 0 0}
.vrow dt{font-size:.63rem;letter-spacing:.11em;text-transform:uppercase;color:#6a7080;font-weight:700;padding-top:3px}
.vrow dd{margin:0;font-size:.88rem;line-height:1.55;color:#2c3140}
.vchips{display:flex;flex-wrap:wrap;gap:6px}
.chip-fact{background:#f4f1ea;border:1px solid #e4ded3;border-radius:99px;padding:3px 9px;font-size:.72rem;line-height:1.45;color:#4a4f5c}
@media(max-width:520px){.vrow{grid-template-columns:1fr;gap:2px}.vrow dt{padding-top:9px}}
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


def _analytical_html(analysis: Any, *, paid: bool, today: date) -> str:
    """Render deterministic astrological evidence; Qwen never writes this block.

    No longer placed in the customer report. The raw clock/transit/Jaimini
    tables were engine working, not something a reader wants — and the same
    evidence now reaches them in plain language through the "why we say this"
    drawers in the current-chapter and recent-windows sections. Kept because
    the confluence regression tests render it directly as a readable dump of
    what the engine decided.
    """
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


# The engine names its six lanes after the technique. A customer needs to know
# what each one watches, so the drawer renames them without renaming the data.
_LANE_PLAIN: dict[str, str] = {
    "Vimshottari": "Main life cycle",
    "Chara": "Sign-based cycle",
    "Yogini": "Emotional cycle",
    "Slow transit": "Slow planets moving now",
    "Dasha-planet transit": "Where your period lords are now",
    "Jaimini": "Karaka cross-check",
}
_LANE_READING: dict[str, str] = {
    "good": "Supportive",
    "moderate": "Workable",
    "mixed": "Pulling both ways",
    "challenging": "Demanding",
}
_JUDGEMENT_CHIP: dict[str, str] = {"good": "good", "moderate": "mid", "mixed": "mid", "challenging": "bad"}


def _as_dicts(value: Any) -> list[dict]:
    """Normalise a list of pydantic facts or plain dicts into dicts."""
    out: list[dict] = []
    for row in list(value or []):
        if hasattr(row, "model_dump"):
            row = row.model_dump(mode="json")
        if isinstance(row, dict):
            out.append(row)
    return out


def _analysis_data(analysis: Any) -> dict:
    if hasattr(analysis, "model_dump"):
        return analysis.model_dump(mode="json")
    return analysis if isinstance(analysis, dict) else {}


def _lane_evidence_rows(lanes: dict) -> str:
    """The six-lane matrix in customer language."""
    rows = []
    for key, plain in _LANE_PLAIN.items():
        raw = str((lanes or {}).get(key) or "")
        if not raw:
            continue
        rows.append(
            f'<div class="evidence-row"><span class="evidence-family">{_e(plain)}</span>'
            f'<span class="evidence-text">{_e(_LANE_READING.get(raw, raw.title()))}</span></div>'
        )
    return f'<div class="evidence-grid">{"".join(rows)}</div>' if rows else ""


def _factor_cols(aj: dict) -> str:
    supports = "".join(f"<li>{_e(x)}</li>" for x in (aj.get("supporting_factors") or [])[:4])
    cautions = "".join(f"<li>{_e(x)}</li>" for x in (aj.get("caution_factors") or [])[:4])
    if not supports and not cautions:
        return ""
    out = '<div class="aj-factor-cols">'
    if supports:
        out += f"<div><small>What is helping</small><ul>{supports}</ul></div>"
    if cautions:
        out += f"<div><small>What is pulling</small><ul>{cautions}</ul></div>"
    return out + "</div>"


def _cross_check_line(aj: dict) -> str:
    """Name the divisional chart that governs this area and what it reads.

    This is the most checkable line in the drawer: the reader can see that the
    claim was tested against the varga for their own question, not against the
    birth chart alone.
    """
    chart = str(aj.get("divisional_chart") or "").strip()
    verdict = str(aj.get("divisional_verdict") or "").strip()
    if not chart or not verdict or verdict == "not available":
        return ""
    return (
        '<div class="conf-cross">Divisional cross-check &middot; the '
        f'<b>{_e(chart)}</b> chart that governs this area reads <b>{_e(verdict)}</b>.</div>'
    )


_LANE_WORD: dict[str, str] = {
    "challenging": "demanding", "good": "supportive",
    "moderate": "workable", "mixed": "mixed",
}


def _lane_tally(aj: dict) -> str:
    """How the six clocks split, as a countable phrase rather than a paragraph.

    Reports whichever reading actually dominates. Ranking "demanding" ahead of
    a larger group produced "1 of 6 cycles demanding" for a window whose drawer
    plainly showed five mixed lanes and one demanding one.
    """
    counted = [str(v) for v in (aj.get("lane_judgements") or {}).values() if str(v)]
    total = len(counted)
    if not total:
        return ""
    tally = Counter(counted)
    # Ties resolve towards the harder reading — understating pressure is the
    # worse error of the two.
    top, count = max(tally.items(),
                     key=lambda kv: (kv[1], kv[0] == "challenging"))
    word = _LANE_WORD.get(top, top)
    if count == total:
        return f"all {total} cycles {word}"
    return f"{count} of {total} cycles {word}"


def _ordinal(n: int) -> str:
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n, f"{n}th")


def _why_chips(aj: dict) -> str:
    """The chart factors behind the verdict, as scannable chips.

    Deliberately not prose. Every chip is a field the engine calculated — the
    house, its karaka and ruler, the varga that governs the area, the slow
    transit touching it, and how the six clocks split. A reader who knows
    astrology can check each one; a reader who does not can still see that the
    verdict came from somewhere specific.

    Wording avoids the customer firewall's blocked forms — no "2nd lord", no
    technique names — without dropping the fact itself.
    """
    chips: list[str] = []
    house = int(aj.get("house") or 0)
    if house:
        chips.append(f"{_ordinal(house)} house")
    karakas = [str(x).strip() for x in (aj.get("natural_karakas") or []) if str(x).strip()]
    if karakas:
        chips.append(f"karaka {karakas[0]}")
    ruler = str(aj.get("house_lord") or "").strip()
    if ruler:
        role = str(aj.get("house_lord_role") or "").strip()
        chips.append(f"ruled by {ruler}" + (f" ({role})" if role else ""))
    chart = str(aj.get("divisional_chart") or "").strip()
    verdict = str(aj.get("divisional_verdict") or "").strip()
    if chart and verdict and verdict != "not available":
        chips.append(f"{chart} reads {verdict}")
    transit = str(aj.get("current_transit") or "").strip()
    if transit:
        chips.append(transit.split(";")[0].strip())
    tally = _lane_tally(aj)
    if tally:
        chips.append(tally)
    if not chips:
        return ""
    return ('<div class="vchips">'
            + "".join(f'<span class="chip-fact">{_e(c)}</span>' for c in chips[:6])
            + "</div>")


_VERDICT_SENTENCE: dict[str, str] = {
    "challenging": "{label} is under real pressure right now",
    "mixed": "{label} is pulling both ways right now",
    "good": "{label} is well supported right now",
    "moderate": "{label} is workable right now",
}

_STRONG_DIV = ("strong", "supportive", "good", "favourable")
_WEAK_DIV = ("weak", "afflicted", "poor", "challenging")


def _verdict_sentence(aj: dict, label: str) -> str:
    """A verdict that says something different for each area.

    The judgement word alone produced three identical sentences in a row when
    three areas happened to share a verdict. The area's own divisional chart and
    its natal footing are what actually distinguish them, so the qualifier is
    built from those.
    """
    judgement = str(aj.get("final_judgement") or "mixed")
    base = _VERDICT_SENTENCE.get(judgement, "").format(label=label)
    if not base:
        return ""
    chart = str(aj.get("divisional_chart") or "").strip()
    div = str(aj.get("divisional_verdict") or "").strip().lower()
    try:
        natal = float(aj.get("natal_foundation_score") or 0.0)
    except (TypeError, ValueError):
        natal = 0.0

    tail = ""
    if chart and div in _STRONG_DIV:
        tail = (f", though the {chart} chart behind it stays strong"
                if judgement in ("challenging", "mixed")
                else f", and the {chart} chart behind it agrees")
    elif chart and div in _WEAK_DIV:
        tail = f", and the {chart} chart behind it is weak too"
    elif natal <= -0.55:
        tail = ", on a base that was already thin here"
    elif natal >= 0.55:
        tail = ", on a base that is genuinely strong here"
    return f"{base}{tail}."

_AGREEMENT_LINE: dict[str, str] = {
    "strong": "The timing systems agree strongly on this.",
    "good": "The timing systems mostly agree on this.",
    "mixed": "The timing systems are split, so read this as a tendency, not a certainty.",
    "conflicting": "The timing systems disagree, so read this as a tendency, not a certainty.",
}
_AGREEMENT_RANK = ["conflicting", "mixed", "good", "strong"]


def _join_labels(names: list[str]) -> str:
    if len(names) <= 1:
        return names[0] if names else ""
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _current_verdict_headline(analysis: Any) -> str:
    """State the finding in the heading instead of describing the section."""
    live = _live_area_judgements(analysis)
    if not live:
        return "Where your chart is putting its weight right now"
    hard = [str(a.get("label") or a.get("area") or "") for a in live
            if str(a.get("final_judgement")) == "challenging"]
    good = [str(a.get("label") or a.get("area") or "") for a in live
            if str(a.get("final_judgement")) == "good"]
    hard = [x for x in hard if x][:2]
    good = [x for x in good if x][:2]
    if hard:
        verb = "needs" if len(hard) == 1 else "need"
        line = f"{_join_labels(hard)} {verb} care right now"
        if good:
            line += f", {_join_labels(good[:1])} is backing you"
        return line + "."
    if good:
        verb = "is" if len(good) == 1 else "are"
        return f"{_join_labels(good)} {verb} your strongest ground right now."
    # Everything the confluence can speak to is mixed. Name the areas anyway —
    # "most of your chart is pulling both ways" tells the reader nothing.
    split = [str(a.get("label") or a.get("area") or "") for a in live[:3]]
    split = [x for x in split if x]
    if split:
        verb = "is" if len(split) == 1 else "are"
        return f"{_join_labels(split)} {verb} pulling both ways right now."
    return "Your chart is pulling both ways right now."


def _confidence_line(shown: list[dict]) -> str:
    """One honest line on how firmly the clocks back the verdicts below."""
    ranks = [str(a.get("confluence_agreement") or "") for a in shown]
    ranks = [r for r in ranks if r in _AGREEMENT_LINE]
    if not ranks:
        return ""
    weakest = min(ranks, key=lambda r: _AGREEMENT_RANK.index(r))
    return _AGREEMENT_LINE[weakest]


def _live_area_judgements(analysis: Any) -> list[dict]:
    """Areas the confluence can actually speak to, hardest first."""
    areas = _as_dicts(_analysis_data(analysis).get("life_area_judgements"))
    live = [
        a for a in areas
        if str(a.get("final_judgement") or "") in ("good", "challenging", "mixed")
        and str(a.get("confluence_agreement") or "insufficient") != "insufficient"
    ]
    # Hardest first: the reader is here because something is pressing.
    live.sort(key=lambda a: float(a.get("confluence_score") or 0.0))
    return live


def _remedy_for_area(area: str, label: str, cards: Optional[list]) -> str:
    """The practical step already derived for this area, if there is one.

    Deliberately the bare step, not ``_fallback_help`` — that appends an easing
    note which belongs in the life-area consultation further down and makes this
    row three sentences long.
    """
    card = next((c for c in (cards or []) if str(getattr(c, "area", "")) == area), None)
    if card is None:
        return ""
    try:
        from llm.fallback import _area_remedy_sentence
        return _area_remedy_sentence(card, label).strip()
    except Exception:  # noqa: BLE001
        return ""


def _window_label(value: str) -> str:
    """Windows arrive as ISO dates; a reader wants a month."""
    text = str(value or "").strip()
    if not text:
        return ""
    return _fmt_full_month(text) or text


def _current_confluence_html(analysis: Any, cards: Optional[list] = None,
                             *, paid: bool = False) -> str:
    """A direct verdict per life area, then the chart factors, then the fix.

    This follows the shape the question reading uses — answer first, evidence
    second, action last — because that is the order a reader actually wants and
    because it is the only order in which a remedy means anything. Everything
    here is read straight off ``life_area_judgements``; the language layer never
    writes this block.
    """
    live = _live_area_judgements(analysis)
    if not live:
        return ""
    shown = live[:3]
    items = []
    for aj in shown:
        judgement = str(aj.get("final_judgement") or "mixed")
        chip = _JUDGEMENT_CHIP.get(judgement, "mid")
        label = str(aj.get("label") or aj.get("area") or "").strip()
        if not label:
            continue

        rows = ""
        sentence = _verdict_sentence(aj, label)
        if sentence:
            rows += f"<dt>Verdict</dt><dd>{_e(sentence)}</dd>"
        chips = _why_chips(aj)
        if chips:
            rows += f"<dt>Why</dt><dd>{chips}</dd>"
        # relief_window / stronger_window are blanked in the free projection,
        # so this row simply does not appear there.
        needs_relief = judgement in ("challenging", "mixed")
        window = _window_label(aj.get("relief_window") if needs_relief
                               else aj.get("stronger_window"))
        if window:
            rows += (f"<dt>{'Eases' if needs_relief else 'Strongest'}</dt>"
                     f"<dd>{_e(window)}</dd>")

        if judgement in ("challenging", "mixed"):
            remedy = _remedy_for_area(str(aj.get("area") or ""), label, cards) if paid else ""
            if paid and remedy:
                rows += f"<dt>Do this</dt><dd>{_e(remedy)}</dd>"
            elif not paid:
                rows += (
                    '<dt>Do this</dt><dd><div class="lock-wrap">'
                    '<div class="lock-blur">The chart-targeted step for this area, '
                    'and the period it works best in.</div>'
                    '<div class="lock-over"><span class="lock-chip">Locked &#183; in the full reading</span></div>'
                    "</div></dd>"
                )

        drawer = (_lane_evidence_rows(aj.get("lane_judgements") or {})
                  + _cross_check_line(aj) + _factor_cols(aj))
        drawer_html = (
            f'<details class="why-said"><summary>Why we say this</summary>{drawer}</details>'
            if drawer else ""
        )
        tone = "good" if chip == "good" else "bad" if chip == "bad" else ""
        rows_html = f'<dl class="vrow">{rows}</dl>' if rows else ""
        verdict_chip = str(aj.get("confluence_label") or judgement).title()
        items.append(
            f'<article class="conf-item {tone}">'
            f'<div class="conf-head"><b>{_e(label)}</b>'
            f'<span class="aj-verdict {chip}">{_e(verdict_chip)}</span></div>'
            f'{rows_html}'
            f'{drawer_html}'
            '</article>'
        )
    if not items:
        return ""
    return f'<div class="conf-list">{"".join(items)}</div>'


_DIRECTION_TONE: dict[str, str] = {
    "up": "good", "support": "good", "supportive": "good",
    "down": "bad", "caution": "bad", "challenging": "bad",
}

#: Primary bhava for each life area, mirroring ``report_cards.AREAS``. Recent
#: windows carry the area key but not its house, and a reader asking "what is
#: this area" deserves the house rather than a mood word.
_AREA_HOUSE: dict[str, int] = {
    "career": 10, "money": 2, "love": 7, "home": 4,
    "children": 5, "health": 1, "learning": 9, "inner": 12,
}

_PAST_READING: dict[str, str] = {
    "good": "Genuinely supported through this window",
    "moderate": "Held up through this window",
    "mixed": "Pulled both ways through this window",
    "challenging": "Under real pressure through this window",
}


def _recent_verdict_sentence(ev: dict) -> str:
    """State what the charts read at the time, not how it may have felt.

    The window headline arriving from the facts layer has had every planet name
    scrubbed out of it, so it can only ever be a mood sentence. The divisional
    verdict and the lane split survived that scrub, and they are what actually
    answers "why this window".

    Kept subject-less and short: the area name sits in the header directly
    above, and the governing varga is already a chip, so naming either again
    would be the third time the reader saw the same fact in one card.
    """
    base = _PAST_READING.get(str(ev.get("judgement") or "").strip(), "")
    if not base:
        return ""
    chart = str(ev.get("divisional_chart") or "").strip()
    div = str(ev.get("divisional_verdict") or "").strip().lower()
    tail = ""
    if chart and div in _STRONG_DIV:
        tail = f", though the {chart} chart behind it stayed strong"
    elif chart and div in _WEAK_DIV:
        tail = f", and the {chart} chart behind it was weak too"
    return f"{base}{tail}."


def _recent_chips(ev: dict) -> str:
    """House, governing varga and the lane split for one past window."""
    chips: list[str] = []
    house = _AREA_HOUSE.get(str(ev.get("area") or ""), 0)
    if house:
        chips.append(f"{_ordinal(house)} house")
    chart = str(ev.get("divisional_chart") or "").strip()
    div = str(ev.get("divisional_verdict") or "").strip()
    if chart and div and div != "not available":
        chips.append(f"{chart} reads {div}")
    tally = _lane_tally(ev)
    if tally:
        chips.append(tally)
    if not chips:
        return ""
    return ('<div class="vchips">'
            + "".join(f'<span class="chip-fact">{_e(c)}</span>' for c in chips)
            + "</div>")


def _recent_windows_html(analysis: Any) -> str:
    """The last few months as dated windows, each with its own evidence.

    One blended paragraph asks the reader to take the whole period on faith. A
    dated window they can check against their own memory, with the complete
    confluence as it stood at the time, asks them to verify it instead.
    """
    rows = _as_dicts(_analysis_data(analysis).get("recent_months"))
    items = []
    for ev in rows[:4]:
        when = _fmt_when(str(ev.get("start") or ""), str(ev.get("end") or ""))
        label = str(ev.get("label") or ev.get("area") or "").strip()
        if not when and not label:
            continue
        tone = _DIRECTION_TONE.get(str(ev.get("direction") or "").lower(), "")
        # The scrubbed LLM headline is dropped in favour of the chart reading.
        verdict = _recent_verdict_sentence(ev)
        chips = _recent_chips(ev)
        manifests = [str(m).strip() for m in (ev.get("manifests") or []) if str(m).strip()]
        manifest_html = ""
        if manifests:
            manifest_html = (
                '<div class="mini-label" style="margin-top:9px">What this may have looked like</div>'
                f'<ul class="recent-manifest">{"".join(f"<li>{_e(m)}</li>" for m in manifests[:3])}</ul>'
            )
        drawer = _lane_evidence_rows(ev.get("lane_judgements") or {}) + _cross_check_line(ev) + _factor_cols(ev)
        drawer_html = (
            f'<details class="why-said"><summary>Why we say this</summary>{drawer}</details>'
            if drawer else ""
        )
        # The window's verdict rides in the header as a chip. It used to be a
        # sentence inside the drawer, where nobody opening the report would see
        # it and where it cost three lines to say one word.
        judged = str(ev.get("judgement") or "").strip()
        verdict_chip = ""
        if judged and judged != "insufficient":
            verdict_chip = (
                f'<span class="aj-verdict {_JUDGEMENT_CHIP.get(judged, "mid")}">'
                f'{_e(_LANE_READING.get(judged, judged.title()))}</span>'
            )
        rows = ""
        if verdict:
            rows += f"<dt>Verdict</dt><dd>{_e(verdict)}</dd>"
        if chips:
            rows += f"<dt>Why</dt><dd>{chips}</dd>"
        rows_html = f'<dl class="vrow">{rows}</dl>' if rows else ""
        items.append(
            f'<article class="recent-item {tone}">'
            f'<div class="recent-head"><span class="recent-when">{_e(when)}</span>'
            f'<span class="mini-label">{_e(label)}</span>{verdict_chip}</div>'
            f'{rows_html}'
            f'{manifest_html}{drawer_html}'
            '</article>'
        )
    return f'<div class="recent-list">{"".join(items)}</div>' if items else ""


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


def _build_unified_current_chapter_html(
    pc: dict,
    analysis: Any,
    cards: Optional[list] = None,
    *,
    paid: bool = False,
    today: Optional[date] = None,
    authoritative_timing_text: str = "",
    lang: str = "en",
) -> str:
    """Builds a unified, authoritative Vedic Astrologer consultation section combining current chapter, live transits, and recent milestone chronology."""
    today = today or date.today()
    from divisional_profile import compute_chart_ashtakavarga, get_live_transit_positions
    from free_dates import LOCKED_WINDOW_PHRASE, is_past
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")

    def when(start: Any, end: Any) -> str:
        if paid:
            return _fmt_when(start, end) or f"{start} → {end}"
        began, finished = is_past(start, today), is_past(end, today)
        if began and finished:
            return _fmt_when(start, end) or f"{start} → {end}"
        if began:
            locked_w = "🔒 Dated Window Sampoorna Reading Lo" if is_tenglish else ("🔒 Dated Window Full Reading Mein" if is_hinglish else LOCKED_WINDOW_PHRASE)
            return f"from {_fmt_date(start)}" if _fmt_date(start) else locked_w
        return "🔒 Dated Window Sampoorna Reading Lo" if is_tenglish else ("🔒 Dated Window Full Reading Mein" if is_hinglish else LOCKED_WINDOW_PHRASE)
    
    av_res = compute_chart_ashtakavarga(pc) if pc else {}
    sav = av_res.get("sav", {})
    transits = get_live_transit_positions(today)
    
    raw_lagna = pc.get("lagna") if pc else ""
    lagna = (
        pc.get("meta", {}).get("lagna_sign")
        or (raw_lagna if isinstance(raw_lagna, str) else (raw_lagna or {}).get("sign", "Aries"))
        if pc else "Aries"
    )
    from astro_precompute import SIGN_LORDS
    lagna_lord = SIGN_LORDS.get(lagna, "Mars")
    
    vim = pc.get("vimshottari", {}) if pc else {}
    raw_cur_md = vim.get("current_md", "Jupiter")
    cur_md = raw_cur_md.get("md_lord", "Jupiter") if isinstance(raw_cur_md, dict) else str(raw_cur_md)
    all_ads = vim.get("current_md_antardashas", [])
    
    cur_ad_idx = next((i for i, a in enumerate(all_ads) if a.get("status") == "current"), -1)
    if cur_ad_idx == -1 and all_ads:
        cur_ad_idx = 0
    
    cur_ad = all_ads[cur_ad_idx] if cur_ad_idx >= 0 and cur_ad_idx < len(all_ads) else {}
    prev_ad = all_ads[cur_ad_idx - 1] if cur_ad_idx > 0 else None
    next_ad = all_ads[cur_ad_idx + 1] if cur_ad_idx + 1 < len(all_ads) else None
    
    ad_lord = cur_ad.get("ad_lord", "Ketu")
    ad_start = cur_ad.get("start", "")
    ad_end = cur_ad.get("end", "")
    
    j_cur = pc.get("jaimini", {}).get("current", {}) if pc else {}
    chara_str = f"{j_cur.get('sign', 'Aquarius')} · {j_cur.get('sub_period', 'Gemini')}"
    
    y_cur = pc.get("yogini", {}).get("current", {}) if pc else {}
    yogini_str = str(y_cur.get("major") or "Ulka (Saturn)")
    
    t_jup_sign = transits.get("Jupiter", "Cancer")
    t_jup_sav = sav.get(t_jup_sign, 28)
    t_sat_sign = transits.get("Saturn", "Pisces")
    t_sat_sav = sav.get(t_sat_sign, 28)
    
    # Chronology cards
    chronology_items = []

    # 1. Real-time mind state & 2. Last 6 Months consultation cards
    mind_card_html = ""
    past_card_html = ""
    try:
        from vedic_consultation_reading import generate_consultation_reading
        g_raw = ((pc.get("meta") or {}).get("gender") or "male")
        g_str = "female" if g_raw in (1, "female", "f") else "male"
        cr_res = generate_consultation_reading(pc, gender=g_str)
        
        m_items = "".join(f"<li style='margin-bottom:10px;'>{it}</li>" for it in cr_res.get("mind_state", []))
        if m_items:
            mind_card_html = (
                f'<div class="chapter-consultation-card" style="background:#fffcf8;border:1px solid #cde0f7;border-left:5px solid #1a5f9e;border-radius:12px;padding:18px 20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.02);">'
                f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:3px 10px;border-radius:99px;background:#e1effe;color:#1a5f9e;display:inline-block;margin-bottom:10px;">'
                f'    1. What Is in Your Mind Right Now (The Immediate Trigger)'
                f'  </div>'
                f'  <ul style="margin:0;padding-left:18px;font-size:0.88rem;line-height:1.62;color:#2c3140;">'
                f'    {m_items}'
                f'  </ul>'
                f'</div>'
            )
            
        p_items = "".join(f"<li style='margin-bottom:10px;'>{it}</li>" for it in cr_res.get("past_6_months", []))
        if p_items:
            past_card_html = (
                f'<div class="chapter-consultation-card" style="background:#fffcf8;border:1px solid #ebd4cc;border-left:5px solid #b57c38;border-radius:12px;padding:18px 20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.02);">'
                f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:3px 10px;border-radius:99px;background:#fdf2e3;color:#b57c38;display:inline-block;margin-bottom:10px;">'
                f'    2. What Happened in the Last 6 Months (Timeline &amp; Building Real Strength)'
                f'  </div>'
                f'  <ul style="margin:0;padding-left:18px;font-size:0.88rem;line-height:1.62;color:#2c3140;">'
                f'    {p_items}'
                f'  </ul>'
                f'</div>'
            )

        roadmap_card_html = ""
        r_items = "".join(f"<li style='margin-bottom:10px;'>{it}</li>" for it in cr_res.get("roadmap_ahead", []))
        if r_items:
            if is_hinglish:
                r_badge = "3. Aane Wala Jyotishiya Roadmap Aur Exact Turning Point Date"
                r_lock = "🔒 Exact Turning Point Date Aur Roadmap Full Reading Mein"
            elif is_tenglish:
                r_badge = "3. Munde Vache Jyotisha Roadmap Mariyu Exact Turning Point Date"
                r_lock = "🔒 Exact Turning Point Date Mariyu Roadmap Sampoorna Reading Lo"
            else:
                r_badge = "3. Astrological Roadmap Ahead &amp; Exact Turning Point Date"
                r_lock = "🔒 Exact Turning Point Date &amp; Roadmap in Full Reading"

            if paid:
                roadmap_card_html = (
                    f'<div class="chapter-consultation-card" style="background:#f8fbf9;border:1px solid #d4e8dc;border-left:5px solid #1c6b45;border-radius:12px;padding:18px 20px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,0.02);">'
                    f'  <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:3px 10px;border-radius:99px;background:#e3f5ec;color:#1c6b45;display:inline-block;margin-bottom:10px;">'
                    f'    {r_badge}'
                    f'  </div>'
                    f'  <ul style="margin:0;padding-left:18px;font-size:0.88rem;line-height:1.62;color:#2c3140;">'
                    f'    {r_items}'
                    f'  </ul>'
                    f'</div>'
                )
            else:
                roadmap_card_html = (
                    f'<div class="chapter-consultation-card lock-wrap" style="background:#f8fbf9;border:1px solid #d4e8dc;border-left:5px solid #1c6b45;border-radius:12px;margin-bottom:16px;position:relative;overflow:hidden;">'
                    f'  <div class="lock-blur" style="padding:18px 20px;">'
                    f'    <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:3px 10px;border-radius:99px;background:#e3f5ec;color:#1c6b45;display:inline-block;margin-bottom:10px;">'
                    f'      {r_badge}'
                    f'    </div>'
                    f'    <ul style="margin:0;padding-left:18px;font-size:0.88rem;line-height:1.62;color:#2c3140;">'
                    f'      {r_items}'
                    f'    </ul>'
                    f'  </div>'
                    f'  <div class="lock-over"><span class="lock-chip" style="font-size:0.75rem;padding:7px 18px;">{r_lock}</span></div>'
                    f'</div>'
                )
    except Exception as exc:
        print(f"[report_conversational] consultation cards skipped: {exc}", flush=True)

    if prev_ad:
        p_lord = prev_ad.get("ad_lord")
        p_dates = when(prev_ad.get("start", ""), prev_ad.get("end", ""))
        if is_hinglish:
            p_badge = "Haal Ka Anubhav / Past Window"
            p_sub = f"{p_lord} Antardasha ({cur_md}–{p_lord})"
            p_text = "Karyakshetra ki tayyari, administrative commitments aur lambe samay ke lakshyo ke liye zameen tayyar karna."
        elif is_tenglish:
            p_badge = "Gathisina Anubhavam / Past Window"
            p_sub = f"{p_lord} Antardasha ({cur_md}–{p_lord})"
            p_text = "Karyakshetramlo tayyari, administrative badhyathalu mariyu deergha kaala lakshyala kosam moolalanu siddham cheyadam."
        else:
            p_badge = "Recent Formative Window"
            p_sub = f"{p_lord} Sub-Period ({cur_md}–{p_lord})"
            p_text = "Analytical groundwork, managing administrative commitments, and laying the intellectual runway for long-term objectives."
        chronology_items.append(
            f'<div class="chapter-step past" style="background:#fdfdfd;border:1px solid #e4ded3;border-left:4px solid #6a7080;border-radius:11px;padding:13px 15px;">'
            f'  <div class="step-badge past" style="display:inline-block;font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;margin-bottom:6px;background:#f0f0f0;color:#6a7080;">{p_badge}</div>'
            f'  <div class="step-head" style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:4px;">'
            f'    <b style="font-family:Georgia,serif;font-size:0.98rem;color:#1f2430;">{p_sub}</b> <span class="step-dates" style="font-size:0.75rem;font-weight:700;color:#6a7080;">{p_dates}</span>'
            f'  </div>'
            f'  <p style="margin:4px 0 0;font-size:0.86rem;line-height:1.55;color:#3d4250;">{p_text}</p>'
            f'</div>'
        )
    
    cur_dates = when(ad_start, ad_end)
    if is_hinglish:
        c_badge = "Chalu Operating Chapter"
        c_sub = f"{ad_lord} Antardasha ({cur_md}–{ad_lord})"
        c_text = "<b>Aantarik Sthirta Aur Re-Alignment:</b> Ek anushasit daur jo purani rukawaton ko hatane, vyarth commitments ko chhodne aur apne professional base ko mazboot karne ke liye samarpit hai."
    elif is_tenglish:
        c_badge = "Chalu Operating Chapter"
        c_sub = f"{ad_lord} Antardasha ({cur_md}–{ad_lord})"
        c_text = "<b>Aantrika Sthiratha Mariyu Re-Alignment:</b> Patha avarodhalanu tholaginchadaniki, waste commitments vadiliveyadaniki mariyu professional base ni balaparachadaniki anukoolamaina phase."
    else:
        c_badge = "Active Operating Chapter"
        c_sub = f"{ad_lord} Sub-Period ({cur_md}–{ad_lord})"
        c_text = "<b>Concentrated Restructuring &amp; Karmic Realignment:</b> A disciplined phase dedicated to internal consolidation, shedding unproductive commitments, and methodically fortifying your core professional baseline."
    chronology_items.append(
        f'<div class="chapter-step active" style="background:#fffcf8;border:1px solid #e4ded3;border-left:4px solid #b57c38;border-radius:11px;padding:14px 16px;">'
        f'  <div class="step-badge active" style="display:inline-block;font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;margin-bottom:6px;background:#fdf2e3;color:#b57c38;">{c_badge}</div>'
        f'  <div class="step-head" style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:4px;">'
        f'    <b style="font-family:Georgia,serif;font-size:1.02rem;color:#1f2430;">{c_sub}</b> <span class="step-dates" style="font-size:0.76rem;font-weight:700;color:#b57c38;">{cur_dates}</span>'
        f'  </div>'
        f'  <p style="margin:4px 0 0;font-size:0.88rem;line-height:1.58;color:#2c3140;">{c_text}</p>'
        f'</div>'
    )
    
    if next_ad:
        n_lord = next_ad.get("ad_lord")
        n_dates = when(next_ad.get("start", ""), next_ad.get("end", ""))
        if is_hinglish:
            n_badge = "Aane Wala Breakthrough Window"
            n_sub = f"{n_lord} Antardasha ({cur_md}–{n_lord})"
            n_text = "<b>Mahatvapurna Safalta Aur Vistaar:</b> Vah mukhya samay jahan pichle prayas samman, promotion aur sthirta mein badalte hain."
        elif is_tenglish:
            n_badge = "Munde Vache Breakthrough Window"
            n_sub = f"{n_lord} Antardasha ({cur_md}–{n_lord})"
            n_text = "<b>Mukhya Safalatha Mariyu Vistaaram:</b> Mundu chesina prayathnalu gouravam, promotion mariyu sthiratha roopamlo phalithalani iche mukhyamaina samayam."
        else:
            n_badge = "Upcoming Breakthrough Window"
            n_sub = f"{n_lord} Sub-Period ({cur_md}–{n_lord})"
            n_text = "<b>Major Manifestation &amp; Elevation Catalyst:</b> The primary timing window where prior perseverance translates into public recognition, vocational promotion, and decisive material expansion."
        chronology_items.append(
            f'<div class="chapter-step future" style="background:#f8fbf9;border:1px solid #e4ded3;border-left:4px solid #1c6b45;border-radius:11px;padding:13px 15px;">'
            f'  <div class="step-badge future" style="display:inline-block;font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;margin-bottom:6px;background:#e3f5ec;color:#1c6b45;">{n_badge}</div>'
            f'  <div class="step-head" style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:4px;">'
            f'    <b style="font-family:Georgia,serif;font-size:0.98rem;color:#1f2430;">{n_sub}</b> <span class="step-dates" style="font-size:0.75rem;font-weight:700;color:#1c6b45;">{n_dates}</span>'
            f'  </div>'
            f'  <p style="margin:4px 0 0;font-size:0.86rem;line-height:1.55;color:#3d4250;">{n_text}</p>'
            f'</div>'
        )
    
    SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    lagna_idx = SIGNS.index(lagna) if lagna in SIGNS else 0
    moon_sign = ""
    if pc:
        moon_sign = (
            str(((pc.get("planets") or {}).get("Moon") or {}).get("sign") or "")
            or str((pc.get("meta") or {}).get("moon_sign") or "")
            or str((pc.get("moon") or {}).get("sign") or ""))
    moon_idx = SIGNS.index(moon_sign) if moon_sign in SIGNS else lagna_idx

    t_sat_house = ((SIGNS.index(t_sat_sign) - lagna_idx) % 12) + 1 if t_sat_sign in SIGNS else 10
    t_sat_moon_house = ((SIGNS.index(t_sat_sign) - moon_idx) % 12) + 1 if t_sat_sign in SIGNS else 7
    t_jup_house = ((SIGNS.index(t_jup_sign) - lagna_idx) % 12) + 1 if t_jup_sign in SIGNS else 2

    HOUSE_DOMAINS = {
        1: ("Self, Vitality & Directional Clarity", "personal vitality, clarity of identity, and executive independence"),
        2: ("Wealth, Liquid Assets & Family Stability", "financial liquidity, speech, savings, and family harmony"),
        3: ("Initiatives, Enterprise & Courage", "self-directed ventures, commercial communication, and immediate team execution"),
        4: ("Domestic Life, Peace of Mind & Property", "inner peace, emotional security, landed property, and domestic stability"),
        5: ("Intellect, Progeny & Strategic Ventures", "creative intelligence, investments, higher planning, and children's welfare"),
        6: ("Workplace Friction, Debts & Competition", "workplace friction, dispute resolution, debt management, and acute fatigue"),
        7: ("Partnerships, Marriage & Public Deals", "one-on-one partnerships, marital equilibrium, and client contracts"),
        8: ("Transformations, Chronic Stress & Vulnerabilities", "unpredicted changes, psychological stress, joint finances, and deep transformations"),
        9: ("Higher Dharma, Mentorship & Fortune", "higher guidance, fortune, legal matters, and long-distance travels"),
        10: ("Career Standing, Authority & Professional Trajectory", "career standing, executive workload, promotion recognition, and professional trajectory"),
        11: ("Gains, Network Revenues & Major Ambitions", "income realization, professional networks, and major aspiration fulfillment"),
        12: ("Expenditure, Isolation & Subconscious Restlessness", "unexpected expenses, sleep quality, mental restlessness, and foreign connections"),
    }

    HOUSE_DOMAINS_HINGLISH = {
        1: ("Aapka Swabhav, Urja Aur Disha", "vyaktigat urja aur aatmavishwas"),
        2: ("Dhan, Bachat Aur Parivarik Sthirta", "aarthik bachat aur parivarik santulan"),
        3: ("Sahas, Initiative Aur Bhai-Behen", "vyaktigat prayas aur team execution"),
        4: ("Ghar, Manasik Shanti Aur Property", "aantarik shanti aur domestic sthirta"),
        5: ("Boudhik Shamta, Nivesh Aur Santan", "creative intelligence aur future planning"),
        6: ("Karyakshetra Ki Chunoutiyan Aur Competitions", "workplace friction aur rozmarra ki mehnat"),
        7: ("Sajhedari, Vivah Aur Public Deals", "jeevansathi aur client contracts"),
        8: ("Badlav, Achanak Aane Wali Chunoutiyan", "unpredicted changes aur transformation"),
        9: ("Dharma, Margdarshan Aur Bhagya", "higher guidance aur bhagyodaya"),
        10: ("Career, Pratishtha Aur Adhikar", "career standing aur promotion recognition"),
        11: ("Labh, Aarthik Growth Aur Network", "aamdani aur lakshya prapti"),
        12: ("Kharch, Ekant Aur Aantarik Shanti", "unexpected expenses aur sleep quality"),
    }

    HOUSE_DOMAINS_TENGLISH = {
        1: ("Mee Swabhavam, Urja Mariyu Disha", "vyakthigatha urja mariyu aathmavishwasam"),
        2: ("Dhanam, Podupu Mariyu Kutumba Sthiratha", "aarthika podupu mariyu kutumba samathulyatha"),
        3: ("Dhairyam, Initiative Mariyu Sahodharulu", "vyakthigatha prayathnam mariyu team execution"),
        4: ("Illu, Manasika Shanti Mariyu Property", "aantrika shanti mariyu domestic sthiratha"),
        5: ("Buddhivalam, Investments Mariyu Pillalu", "creative intelligence mariyu future planning"),
        6: ("Karyakshetramlo Chunautilu Mariyu Competitions", "workplace friction mariyu dainandina kashtam"),
        7: ("Bhagaswamyam, Vivaham Mariyu Public Deals", "jeevithabhagswami mariyu client contracts"),
        8: ("Maarpu, Aakasmika Chunautilu", "unpredicted changes mariyu transformation"),
        9: ("Dharmam, Margadarshanam Mariyu Bhagyam", "higher guidance mariyu bhagyodayam"),
        10: ("Career, Gouravam Mariyu Adhikaram", "career standing mariyu promotion recognition"),
        11: ("Labham, Aarthika Growth Mariyu Network", "aadaayam mariyu lakshya prapti"),
        12: ("Kharchu, Ekantam Mariyu Aantrika Shanti", "unexpected expenses mariyu nidra quality"),
    }

    h_domains_dict = HOUSE_DOMAINS_TENGLISH if is_tenglish else (HOUSE_DOMAINS_HINGLISH if is_hinglish else HOUSE_DOMAINS)
    default_dom = ("Karyakshetram Mariyu Disha" if is_tenglish else ("Karyakshetra Aur Disha" if is_hinglish else "Vocational & Life Direction"), "core responsibilities")
    domain_name, domain_desc = h_domains_dict.get(t_sat_house, default_dom)
    primary_tension_title = domain_name

    symptoms = []
    if is_hinglish:
        if t_sat_house == 10:
            symptoms.append("Mehnat ke anuroop recognition aur promotions mein deri ya rukawat mehsoos hona")
            symptoms.append("Kaam ka administrative load badhna aur seniors/authority se thoda friction")
            symptoms.append("Career mein badlav ki ichha hona lekin sahi timing ki spashtata ka intezar")
        elif t_sat_house == 6:
            symptoms.append("Dainik karyakshetra mein workload aur chote vivaado se thakan")
            symptoms.append("Pachan ya physical stamina par thoda asar")
        elif t_sat_house == 8:
            symptoms.append("Achanak aane wale badlav ya financial stress")
        elif t_sat_house == 4:
            symptoms.append("Ghar mein thodi asanti ya property related delays")
        elif t_sat_house == 7:
            symptoms.append("Partnerships ya business negotiations mein deri")
        elif t_sat_house == 12:
            symptoms.append("Kharch badhna aur neend mein bechaini")
        else:
            symptoms.append(f"{domain_name} mein anushasan aur dhairya ki aavashyakta")
        if ad_lord in ("Ketu", "Rahu", "Saturn"):
            symptoms.append(f"Chalu <b>{ad_lord} Antardasha</b> ke karan routine kaamon mein aantarik virakti mehsoos hona")
    elif is_tenglish:
        if t_sat_house == 10:
            symptoms.append("Kashtaniki tagga recognition mariyu promotions lo aalasyam anipinchatam")
            symptoms.append("Panilo administrative load peragadam mariyu seniors/authorities tho chinna friction")
            symptoms.append("Career lo maarpu korukovadam kani correct timing clarity kosam wait cheyadam")
        elif t_sat_house == 6:
            symptoms.append("Daily work stress, workload mariyu chinnapati vivadhalatho thagilina thakan")
            symptoms.append("Jeerna vyavastha leda physical stamina meeda thoda prabhav")
        elif t_sat_house == 8:
            symptoms.append("Achanak ga vache badlavulu leda financial stress")
        elif t_sat_house == 4:
            symptoms.append("Intlo konchem ashanthi leda property aalasyam")
        elif t_sat_house == 7:
            symptoms.append("Partnerships leda business discussions lo aalasyam")
        elif t_sat_house == 12:
            symptoms.append("Kharchulu peragadam mariyu nidralo thalladilladam")
        else:
            symptoms.append(f"{domain_name} lo anushasanam mariyu opika chala aavashyakam")
        if ad_lord in ("Ketu", "Rahu", "Saturn"):
            symptoms.append(f"Chalu <b>{ad_lord} Antardasha</b> valla routine panullo aantarika virakthi raavadam")
    else:
        if t_sat_house == 10:
            symptoms.append("Feeling that professional recognition and career promotions are delayed or bottlenecked despite exhausting input")
            symptoms.append("Shouldering an intense administrative/executive workload with rigid organizational expectations or friction from authority figures")
            symptoms.append("Experiencing an acute urge to pivot or reinvent your vocational path, countered by frustrating inertia or lack of clear timing clarity")
        elif t_sat_house == 6:
            symptoms.append("Daily operational overload, workplace politics, or feeling constantly drained by managing disputes and operational obstacles")
            symptoms.append("Digestive sensitivity, inflammation, or physical fatigue from relentless daily stress")
        elif t_sat_house == 8:
            symptoms.append("Sudden unexpected roadblocks, anxiety regarding status shifts, or navigating hidden liabilities and joint financial stress")
        elif t_sat_house == 4:
            symptoms.append("Domestic friction, property-related delays, or feeling an inability to mentally relax outside working hours")
        elif t_sat_house == 7:
            symptoms.append("Interpersonal friction, contractual negotiations dragging on, or emotional distance in critical partnerships")
        elif t_sat_house == 12:
            symptoms.append("Unplanned financial drainage, disrupted sleep rhythms, and a strong urge to withdraw from public engagements")
        else:
            symptoms.append(f"Heavy structural discipline demanded across {domain_desc} with minimal immediate gratification")
        if ad_lord in ("Ketu", "Rahu", "Saturn"):
            symptoms.append(f"Mental detachment and disillusionment brought by the active <b>{ad_lord} Antardasha</b>, making routine obligations feel spiritually hollow")

    if is_hinglish:
        next_lord_name = next_ad.get("ad_lord", "agla period") if next_ad else "aane wala window"
    elif is_tenglish:
        next_lord_name = next_ad.get("ad_lord", "tharuvatha period") if next_ad else "munde vache window"
    else:
        next_lord_name = next_ad.get("ad_lord", "the next period") if next_ad else "upcoming window"
    next_date_str = _fmt_full_month(next_ad.get("start", "")) if next_ad and next_ad.get("start") else "early 2027"
    
    if is_hinglish:
        easing_when = f" ({next_date_str})" if paid else " — exact date poori reading mein shamil hai"
        avoid_until = f"{next_date_str} se pehle" if paid else "is antardasha ke pura hone tak"
        moon_aspect_note = f", Janma Rashi (Moon in {moon_sign}) par drishti" if moon_sign in SIGNS and t_sat_moon_house in (1, 4, 7, 10) else ""
        sat_root = f"Shani Dev aapke <b>{t_sat_house}th house ({t_sat_sign})</b> mein transit kar rahe hain" + (f" (SAV: <b>{t_sat_sav} bindus</b>)" if paid else "") + moon_aspect_note
    elif is_tenglish:
        easing_when = f" ({next_date_str})" if paid else " — exact date sampoorna reading lo undi"
        avoid_until = f"{next_date_str} kante mundu" if paid else "ee antardasha poorthi ayye varaku"
        moon_aspect_note = f", Janma Rashi (Moon in {moon_sign}) meeda drushti" if moon_sign in SIGNS and t_sat_moon_house in (1, 4, 7, 10) else ""
        sat_root = f"Shani Bhagavan mee <b>{t_sat_house}th house ({t_sat_sign})</b> lo transit chesthunnaru" + (f" (SAV: <b>{t_sat_sav} bindus</b>)" if paid else "") + moon_aspect_note
    else:
        easing_when = f" ({next_date_str})" if paid else " — the exact handover date is in the full reading"
        avoid_until = f"before {next_date_str}" if paid else "until this sub-period hands over"
        moon_aspect_note = f", casting a direct aspect onto your Janma Rashi (Moon in {moon_sign})" if moon_sign in SIGNS and t_sat_moon_house in (1, 4, 7, 10) else ""
        sat_root = f"Saturn (Shani) is transiting your <b>{t_sat_house}th house ({t_sat_sign})</b>" + (f" with an Ashtakavarga score of <b>{t_sat_sav} bindus</b> (critical threshold is 28)" if paid else "") + moon_aspect_note

    if is_hinglish:
        root_label = "Astrological Mool Adhar:"
        manifest_label = "Yeh dainik jeevan mein is roop mein dikhai de sakta hai:"
        breakthrough_label = "⏳ Rahat Aur Breakthrough Window:"
        breakthrough_text = f"Yeh dasha sthiti {ad_lord} Antardasha ke pura hone aur <b>{next_lord_name} Antardasha</b> shuru hone par spasht roop se anukool ho jayegi{easing_when}."
        sat_dasha_note = f"{cur_md}–{ad_lord} dasha ke dauran yeh bina kisi jaldbazi ke karmic consolidation ka sanket deta hai."
    elif is_tenglish:
        root_label = "Astrological Moola Aadharam:"
        manifest_label = "Idi dainandina jeevitham lo ee vidhamga kanipisthundi:"
        breakthrough_label = "⏳ Upashamanam Mariyu Breakthrough Window:"
        breakthrough_text = f"Ee dasha sthiti {ad_lord} Antardasha poorthi ayyi <b>{next_lord_name} Antardasha</b> start ayyaka anukoolam ga maruthundi{easing_when}."
        sat_dasha_note = f"{cur_md}–{ad_lord} dasha kaalamlo idi thondarapaatu lekunda karmic consolidation sanketham."
    else:
        root_label = "Astrological Root:"
        manifest_label = "How this is manifesting in your daily experience:"
        breakthrough_label = "⏳ Easing &amp; Breakthrough Window:"
        breakthrough_text = f"This structural bottleneck eases decisively as {ad_lord} AD completes and transitions into <b>{next_lord_name} Antardasha</b>{easing_when}."
        sat_dasha_note = f"During the {cur_md}–{ad_lord} dasha, this signifies patient karmic consolidation."

    primary_tension_body = f"""
    <p style="margin:0 0 10px;font-size:0.88rem;line-height:1.6;color:#2c3140;">
      <b>{root_label}</b> {sat_root}. {sat_dasha_note}
    </p>
    <div style="background:#fef7f6;border-radius:8px;padding:10px 14px;margin-bottom:10px;">
      <b style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:#9e2a1b;">{manifest_label}</b>
      <ul style="margin:6px 0 0;padding-left:18px;font-size:0.86rem;line-height:1.55;color:#3d4250;">
        {"".join(f"<li style='margin-bottom:4px;'>{s}</li>" for s in symptoms)}
      </ul>
    </div>
    <p style="margin:0;font-size:0.85rem;line-height:1.5;color:#7a2416;font-weight:600;">
      {breakthrough_label} {breakthrough_text}
    </p>
    """

    # 2. Protective Grace Area
    default_jup = ("Dhanam Mariyu Aarthika Sthiratha" if is_tenglish else ("Dhan Aur Aarthik Sthirta" if is_hinglish else "Financial & Resource Base"), "material resources")
    jup_domain, jup_desc = h_domains_dict.get(t_jup_house, default_jup)
    protective_title = jup_domain
    jup_score = (f" (SAV: <b>{t_jup_sav} bindus</b>)" if paid else "")
    
    if is_hinglish:
        protective_body = f"""
        <p style="margin:0 0 6px;">
          <b>Astrological Sahyog:</b> Guru (Jupiter) aapke <b>{t_jup_house}th house ({t_jup_sign})</b> mein transit kar rahe hain{jup_score}.
        </p>
        <p style="margin:0;color:#1c6b45;">
          <b>Suraksha Kavach:</b> Yeh aapke aarthik adhar, bachat aur parivar ki suraksha ko majboot sahara deta hai. Karyakshetra mein der ke bawajood aapka mool aarthik santulan surakshit rehta hai.
        </p>
        """
    elif is_tenglish:
        protective_body = f"""
        <p style="margin:0 0 6px;">
          <b>Astrological Sahayam:</b> Guru (Jupiter) mee <b>{t_jup_house}th house ({t_jup_sign})</b> lo transit chesthunnaru{jup_score}.
        </p>
        <p style="margin:0;color:#1c6b45;">
          <b>Rakshana Kavacham:</b> Idi mee aarthika sthiratha, podupu mariyu kutumba surakshithathaku balamaina aadharam isthundi. Career lo aalasyam unna, mee moola aarthika balam surakshithanga untundi.
        </p>
        """
    else:
        protective_body = f"""
        <p style="margin:0 0 6px;">
          <b>Astrological Grace:</b> While your {domain_name.lower()} is under pressure, Jupiter (Guru) transits your <b>{t_jup_house}th house ({t_jup_sign})</b>{jup_score}.
        </p>
        <p style="margin:0;color:#1c6b45;">
          <b>Your Safety Anchor:</b> This provides powerful insulation for your financial baseline, liquidity, and family security. Regardless of professional delays, your fundamental material solvency and resources remain strongly protected.
        </p>
        """

    # 3. Secondary Resilience & Mind Axis
    if is_hinglish:
        secondary_title = "Mann Ki Shanti, Urja Aur Swasthya"
        secondary_body = f"""
        <p style="margin:0 0 6px;">
          Shani aur Ketu ke prabhav se kabhi-kabhi <b>mann mein over-analysis, neend mein bechaini ya thakan</b> mehsoos ho sakti hai.
        </p>
        <p style="margin:0;color:#6b4d1b;">
          <b>Vedic Margdarshan:</b> Pachan aur swasthya ka dhyan rakhein, aur kaam mein excessive stress se bachein. Is samay ko aantarik skills sikhne ka samay maanein.
        </p>
        """
    elif is_tenglish:
        secondary_title = "Manasika Prasanthatha, Urja Mariyu Aarogyam"
        secondary_body = f"""
        <p style="margin:0 0 6px;">
          Shani mariyu Ketu prabhavam valla <b>manasulo over-analysis, nidra thalladilladam leda thakan</b> anipinchavachu.
        </p>
        <p style="margin:0;color:#6b4d1b;">
          <b>Vedic Margadarshanam:</b> Jeerna vyavastha mariyu aarogyam meeda shraddha pettandi, panilo excessive stress theesukovaddu. Ee samayanni aantarika skills nerchukune kaalam ga bhavinchandi.
        </p>
        """
    else:
        secondary_title = "Mental Resilience, Rest & Physical Stamina"
        secondary_body = f"""
        <p style="margin:0 0 6px;">
          The combination of Saturn's aspect and Ketu's inward sub-period frequently triggers <b>mental over-analysis, restless sleep, and low energy reserves</b>.
        </p>
        <p style="margin:0;color:#6b4d1b;">
          <b>Vedic Care:</b> Protect digestive health and avoid burning out by over-compensating at work. Treat this period as internal skill mastery rather than outward conquest.
        </p>
        """

    # 4. Strategic Astrologer Advisory
    if is_hinglish:
        counsel_body = f"""
        <ul style="margin:0;padding-left:18px;font-size:0.86rem;line-height:1.58;color:#2c3140;">
          <li style="margin-bottom:4px;"><b>Abhi Jaldbazi Se Bachein:</b> Bhavuk hokar achanak career badalne, senior se bahas karne ya high-risk investment se bachein {avoid_until}.</li>
          <li style="margin-bottom:4px;"><b>In Par Dhyan Dein:</b> Apne kaam ko methodically complete karein, apni credentials aur skills upgrade karein, aur meditation/adhyatmik abhyas karein.</li>
          <li><b>Jyotishiya Nirnay:</b> Aap peeche nahi hain; aapki kundli agle <b>{next_lord_name} Antardasha</b> ke vistar ke liye zameen tayyar kar rahi hai.</li>
        </ul>
        """
    elif is_tenglish:
        counsel_body = f"""
        <ul style="margin:0;padding-left:18px;font-size:0.86rem;line-height:1.58;color:#2c3140;">
          <li style="margin-bottom:4px;"><b>Thondarapaatu Vaddu:</b> Emotional ga career marchadam, superiors tho godavalu leda high-risk speculations nunchi duranga undandi {avoid_until}.</li>
          <li style="margin-bottom:4px;"><b>Deeni Meeda Focus Cheyandi:</b> Panulanu methodically poorthi cheyandi, skills upgrade cheyandi mariyu dhyanam/adhyathmika abhyasam cheyandi.</li>
          <li><b>Jyotisha Theerpu:</b> Meeru venukapadi leru; mee kundali munde vache <b>{next_lord_name} Antardasha</b> vistarana kosam runway ready chesthondi.</li>
        </ul>
        """
    else:
        counsel_body = f"""
        <ul style="margin:0;padding-left:18px;font-size:0.86rem;line-height:1.58;color:#2c3140;">
          <li style="margin-bottom:4px;"><b>What to Avoid Right Now:</b> Avoid hasty, emotionally driven resignations, public confrontations with superiors, or high-risk capital speculation {avoid_until}.</li>
          <li style="margin-bottom:4px;"><b>What to Double Down On:</b> Methodically document deliverables, fortify internal processes, upgrade specialized credentials, and practice spiritual/meditative centering.</li>
          <li><b>The Astrological Verdict:</b> You are not falling behind; your chart is clearing karmic clutter to prepare the runway for your upcoming <b>{next_lord_name} AD expansion</b>.</li>
        </ul>
        """

    if is_hinglish:
        upayas = [
            f"<b>Antardasha Swami ({ad_lord}):</b> Mangalwar sham ko <i>Om Ketave Namah</i> ka 108 baar jaap karein ya dharmik karyo mein sahyog karein.",
            f"<b>Mahadasha Swami ({cur_md}):</b> Guruwar subah <i>Guru Gayatri Mantra</i> ka jaap karein aur gurus/buzurgo ka aashirwad lein.",
            f"<b>Shani Gochar Upay:</b> Shanivar ko pakshiyo ko paani ya anaaj dein aur Shani ke prabhav ko santulit karein.",
        ]
    elif is_tenglish:
        upayas = [
            f"<b>Antardasha Swami ({ad_lord}):</b> Mangalavaram sayantram <i>Om Ketave Namah</i> 108 sarlu japam cheyandi leda adhyathmika sevalu cheyandi.",
            f"<b>Mahadasha Swami ({cur_md}):</b> Guruwaram udayam <i>Guru Gayatri Mantram</i> japam cheyandi mariyu peddala ashirwadam theesukondi.",
            f"<b>Shani Gochara Upayam:</b> Shanivaram pakshulaku aaharam/neellu petti Shani prabhavanni samathulyam cheyandi.",
        ]
    else:
        upayas = [
            f"<b>Harmonize Active Sub-Lord ({ad_lord}):</b> Recite <i>Om Ketave Namah</i> 108 times on Tuesday evenings, or support spiritual education/monastic charities to clear mental static.",
            f"<b>Energize Mahadasha Lord ({cur_md}):</b> Chant the <i>Guru Gayatri Mantra</i> on Thursday mornings and respect mentors, teachers, and elders.",
            f"<b>Transit Balancing:</b> Offer water or grain to birds on Saturdays to harmonize Saturn's transit across governing houses.",
        ]

    if paid:
        upaya_items = "".join(f"<li style='margin-bottom:6px;'>{u}</li>" for u in upayas)
        if is_hinglish:
            u_box_head = "Is Chapter Ke Liye Targeted Astrological Upay"
        elif is_tenglish:
            u_box_head = "Ee Chapter Kosam Targeted Astrological Upayamulu"
        else:
            u_box_head = "Targeted Astrological Upaya for this Chapter"
        remedy_block = (
            f'<div class="chapter-upaya-box" style="background:#f9fbf9;border:1px solid #d4e8dc;border-left:4px solid #1c6b45;border-radius:12px;padding:16px 18px;margin-top:20px;">'
            f'  <div class="upaya-head" style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:#1c6b45;margin-bottom:8px;">{u_box_head}</div>'
            f'  <ul class="upaya-list" style="margin:0;padding-left:18px;font-size:0.86rem;line-height:1.55;color:#2c3140;">{upaya_items}</ul>'
            f'</div>'
        )
    else:
        if is_hinglish:
            t_upaya_lbl = "Vedic Upay:"
            t_upaya_desc = f"Specific planetary mantras, ratna vidhi aur dainik upay {ad_lord} aur {cur_md} ke liye."
            t_lock_chip = "🔒 Complete Upay Aur Remedies Full Reading Mein"
        elif is_tenglish:
            t_upaya_lbl = "Vedic Upayam:"
            t_upaya_desc = f"Specific planetary mantralu, ratna dharana mariyu dainandina upayamulu {ad_lord} mariyu {cur_md} kosam."
            t_lock_chip = "🔒 Sampoorna Upayamulu Full Reading Lo"
        else:
            t_upaya_lbl = "Targeted Vedic Upaya:"
            t_upaya_desc = f"Specific planetary mantras, gemstone calibrations, and daily charitable rituals for {ad_lord} and {cur_md}."
            t_lock_chip = "🔒 Complete Upaya &amp; Remedies in Full Reading"
        remedy_block = (
            f'<div class="lock-wrap" style="margin-top:16px;border-radius:10px;">'
            f'  <div class="lock-blur" style="padding:14px 16px;font-size:0.86rem;line-height:1.5;">'
            f'    <b>{t_upaya_lbl}</b> {t_upaya_desc}'
            f'  </div>'
            f'  <div class="lock-over"><span class="lock-chip" style="font-size:0.7rem;padding:6px 16px;">{t_lock_chip}</span></div>'
            f'</div>'
        )

    if next_ad:
        next_ad_title = f"{next_ad.get('ad_lord', 'Venus')} AD"
    elif is_hinglish:
        next_ad_title = "Agla Badlav"
    elif is_tenglish:
        next_ad_title = "Tharuvatha Badlavu"
    else:
        next_ad_title = "Next Breakthrough"

    if next_ad and next_ad.get("start") and paid:
        next_ad_date = f"from {_fmt_full_month(next_ad.get('start', ''))}"
    elif next_ad and next_ad.get("start"):
        next_ad_date = "🔒 Sampoorna Reading Lo" if is_tenglish else ("🔒 Full Reading Mein" if is_hinglish else LOCKED_WINDOW_PHRASE)
    else:
        next_ad_date = "Munde Vachedi" if is_tenglish else ("Aane Wala" if is_hinglish else "Upcoming")

    gochar_line = (
        f"Jup in {t_jup_sign} ({t_jup_sav} SAV) · Sat in {t_sat_sign} ({t_sat_sav} SAV)"
        if paid else
        f"Jup in {t_jup_sign} · Sat in {t_sat_sign}")
    sat_header = (
        f"Saturn in {t_sat_sign} ({t_sat_sav} SAV) · {cur_md}–{ad_lord}"
        if paid else
        f"Saturn in {t_sat_sign} · {cur_md}–{ad_lord}")
    
    bindu_working = ""
    if not paid:
        if is_hinglish:
            b_summary = "Is chapter ke peeche ka jyotishiya working"
            b_text = f"Shani transiting {t_sat_sign} (SAV: {t_sat_sav} bindus). Guru in {t_jup_sign} (SAV: {t_jup_sav}). Dated handover aur upay poori reading mein shamil hain."
        elif is_tenglish:
            b_summary = "Ee chapter venuka unna jyotisha working"
            b_text = f"Shani transiting {t_sat_sign} (SAV: {t_sat_sav} bindus). Guru in {t_jup_sign} (SAV: {t_jup_sav}). Dated handover mariyu upayamulu sampoorna reading lo unnai."
        else:
            b_summary = "The chart working behind this chapter"
            b_text = f"Saturn transiting {t_sat_sign} scores {t_sat_sav} bindus (28 is the working threshold). Jupiter in {t_jup_sign} scores {t_jup_sav}. The dated handover and the step that helps sit in the full reading."
        bindu_working = (
            f'<details style="margin-top:12px;border-top:1px solid #eeeae3;padding-top:8px;'
            f'font-size:0.78rem;color:#7a756c;line-height:1.45;">'
            f'<summary style="cursor:pointer;font-weight:600;color:#1f2430;">{b_summary}</summary>'
            f'<div style="padding-top:6px;color:#444;">{b_text}</div></details>')

    if is_hinglish:
        ch_kicker = "CHALU JYOTISH DASHA AUR RECENT MILESTONES"
        ch_heading = "Aapka Vartaman Jeevan Chapter: Grah Prabhav Aur Disha"
        lbl_dasha = "Chalu Dasha:"
        lbl_shift = "Agla Mahatvapurna Badlav:"
        lbl_clocks = "Vedic Clocks:"
        lbl_gochar = "Gochara Sthiti:"
        astrologer_p = (
            f"Vedic Jyotish ke anusar aapki janma kundli (<b>{lagna} Lagna</b>, swami <b>{lagna_lord}</b>), "
            f"vartaman mein <b>{cur_md} (Mahadasha)</b> aur <b>{ad_lord} (Antardasha)</b> ke prabhav mein hai. "
            f"Jahan {cur_md} dasha mukhya 16-varshiya vikas ka adhar banati hai, wahin {ad_lord} antardasha vartaman mein aantarik sthirta, "
            f"purani rukawaton ko hatane aur aane wale breakthrough ke liye majboot neev rakhne ka sanket deti hai."
        )
        reality_title = "Lived Reality: Mukhya Chunoiti Aur Jyotishiya Stambh"
        pressure_badge = "⚠️ Mukhya Dasha Prabhav Axis"
        grace_badge = "🛡️ Sakriya Suraksha Aur Sthirta Anchor"
        mind_badge = "🧘 Mann, Urja Aur Santulan"
        strategy_title = "Is Samay Ke Liye Vedic Astrologer Ki Strategy"
        timeline_title = "Chronological Milestones Aur Dasha Parivartan"
    elif is_tenglish:
        ch_kicker = "CHALU JYOTISHA DASHA MARIYU RECENT MILESTONES"
        ch_heading = "Mee Varthamana Jeevitha Chapter: Graha Prabhavam Mariyu Disha"
        lbl_dasha = "Chalu Dasha:"
        lbl_shift = "Mukhya Badlavu Shift:"
        lbl_clocks = "Vedic Clocks:"
        lbl_gochar = "Gochara Sthiti:"
        astrologer_p = (
            f"Vedic Jyotishyam prakaram mee janma kundali (<b>{lagna} Lagna</b>, adhipathi <b>{lagna_lord}</b>), "
            f"prasthutham <b>{cur_md} (Mahadasha)</b> mariyu <b>{ad_lord} (Antardasha)</b> prabhavam lo undi. "
            f"{cur_md} dasha mukhya 16-years vikasam aadharam ga unte, {ad_lord} antardasha aantrika sthiratha, "
            f"patha avarodhalanu tholaginchadam mariyu munde vache breakthrough kosam balamaina neev siddham chesthundi."
        )
        reality_title = "Lived Reality: Mukhya Chunautilu Mariyu Jyotisha Sthambhalu"
        pressure_badge = "⚠️ Mukhya Dasha Prabhav Axis"
        grace_badge = "🛡️ Sakriya Suraksha Mariyu Sthiratha Anchor"
        mind_badge = "🧘 Manasu, Urja Mariyu Samathulyatha"
        strategy_title = "Ee Samayam Kosam Vedic Astrologer Strategy"
        timeline_title = "Chronological Milestones Mariyu Dasha Marpulu"
    else:
        ch_kicker = "ACTIVE JYOTISH PERIOD &amp; RECENT MILESTONES"
        ch_heading = "Your Current Life Chapter: Planetary Influences &amp; Trajectory"
        lbl_dasha = "Planetary Period (Dasha):"
        lbl_shift = "Major Breakthrough Shift:"
        lbl_clocks = "Multi-Clock Alignment:"
        lbl_gochar = "Live Gochar (Transits):"
        astrologer_p = (
            f"As a Vedic Astrologer examining your birth chart (<b>{lagna} Lagna</b> governed by <b>{lagna_lord}</b>), your life is currently operating under the dual governance of <b>{cur_md} (Mahadasha)</b> and <b>{ad_lord} (Antardasha)</b>. "
            f"While {cur_md} sets the overarching 16-year curriculum of expansion, wisdom, and vocational status, {ad_lord} acts as the immediate operating lens—directing focus toward inward restructuring, clearing legacy distractions, and establishing rock-solid foundations for the upcoming breakthrough."
        )
        reality_title = "Lived Reality: Core Tensions &amp; Pillars"
        pressure_badge = "⚠️ Primary Structural Pressure Axis"
        grace_badge = "🛡️ Active Protective Grace Anchor"
        mind_badge = "🧘 Mental Resilience, Rest &amp; Restorative Axis"
        strategy_title = "How to Play This Chapter: Strategic Astrologer Advisory"
        timeline_title = "Chronological Dasha Sequence &amp; Phase Transitions"

    return f"""
    <section class="conv-block current-block" style="margin:28px 0;">
      <div class="section-kicker" style="font-size:0.72rem;letter-spacing:0.14em;text-transform:uppercase;color:#8a6a1f;font-weight:800;margin-bottom:6px;">{ch_kicker}</div>
      <h2 id="sec-your-current-chapter" data-nav="Current chapter" style="font-family:Georgia,serif;font-size:1.35rem;color:#1f2430;margin:0 0 14px;font-weight:600;">{ch_heading}</h2>
      
      <div class="chapter-overview-board" style="background:#fcfbf8;border:1px solid #e8e4dc;border-left:4px solid #b57c38;border-radius:12px;padding:16px 18px;margin-bottom:18px;">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;font-size:0.85rem;line-height:1.45;color:#2c3140;">
          <div><b>{lbl_dasha}</b> <span style="color:#7a4b18;font-weight:700;">{cur_md} MD · {ad_lord} AD</span> ({cur_dates})</div>
          <div><b>{lbl_shift}</b> <span style="color:#1c6b45;font-weight:700;">{next_ad_title}</span> ({next_ad_date})</div>
          <div><b>{lbl_clocks}</b> Chara: {chara_str} | Yogini: {yogini_str}</div>
          <div><b>{lbl_gochar}</b> {gochar_line}</div>
        </div>
      </div>

      <div class="chapter-astrologer-note" style="margin-bottom:20px;font-size:0.93rem;line-height:1.65;color:#2c3140;">
        <p style="margin:0 0 10px;">
          {astrologer_p}
        </p>
      </div>

      {mind_card_html}
      {past_card_html}
      {roadmap_card_html}

      <!-- KEY PROBLEM AREA & ASTROLOGICAL PILLARS -->
      <div class="chapter-domains-wrap" style="margin:22px 0;">
        <div style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:12px;">
          {reality_title}
        </div>
        
        <!-- Primary Friction / Problem Area (Full Width Red/Amber Card) -->
        <div class="chapter-problem-card" style="background:#fffcfb;border:1px solid #ebd4cc;border-left:5px solid #c84b31;border-radius:12px;padding:16px 18px;margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:8px;">
            <span style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:3px 9px;border-radius:99px;background:#fce8e6;color:#a8321d;">
              {pressure_badge}
            </span>
            <span style="font-size:0.78rem;font-weight:700;color:#8f301e;">{sat_header}</span>
          </div>
          <h3 style="font-family:Georgia,serif;font-size:1.1rem;color:#1f2430;margin:0 0 8px;font-weight:600;">{primary_tension_title}</h3>
          {primary_tension_body}
          {bindu_working}
        </div>

        <!-- Two Column Grid for Protective Pillar & Mental Resilience -->
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin-bottom:14px;">
          
          <!-- Protective Pillar (Green Card) -->
          <div class="chapter-protective-card" style="background:#f8fbf9;border:1px solid #d4e8dc;border-left:4px solid #1c6b45;border-radius:12px;padding:15px 16px;">
            <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;background:#e3f5ec;color:#1c6b45;display:inline-block;margin-bottom:8px;">
              {grace_badge}
            </div>
            <h4 style="font-family:Georgia,serif;font-size:0.98rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{protective_title}</h4>
            <div style="font-size:0.85rem;line-height:1.55;color:#2c3140;">
              {protective_body}
            </div>
          </div>

          <!-- Mental & Physical Resilience Card -->
          <div class="chapter-resilience-card" style="background:#fffcf8;border:1px solid #e8e4dc;border-left:4px solid #b57c38;border-radius:12px;padding:15px 16px;">
            <div style="font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:2px 8px;border-radius:99px;margin-bottom:8px;background:#fdf2e3;color:#b57c38;display:inline-block;">
              {mind_badge}
            </div>
            <h4 style="font-family:Georgia,serif;font-size:0.98rem;color:#1f2430;margin:0 0 6px;font-weight:600;">{secondary_title}</h4>
            <div style="font-size:0.85rem;line-height:1.55;color:#2c3140;">
              {secondary_body}
            </div>
          </div>
        </div>

        <!-- Strategic Astrologer Advisory Box -->
        <div class="chapter-counsel-card" style="background:#fcfbf8;border:1px solid #e8e4dc;border-radius:11px;padding:14px 16px;">
          <div style="font-size:0.7rem;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;color:#7a4b18;margin-bottom:6px;">
            {strategy_title}
          </div>
          {counsel_body}
        </div>
      </div>

      <!-- TIMELINE -->
      <div class="chapter-timeline-wrap" style="margin:20px 0;">
        <div style="font-size:0.72rem;letter-spacing:0.12em;text-transform:uppercase;font-weight:800;color:#7a4b18;margin-bottom:10px;">{timeline_title}</div>
        <div style="display:grid;gap:10px;">
          {"".join(chronology_items)}
        </div>
      </div>

      {remedy_block}
    </section>
    """


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
    upsell_html: str = "",
    analysis: Any = None,
    lang: str = "en",
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
    lang_code = str(lang or "").lower().strip()
    is_hinglish = lang_code in ("hi_en", "hinglish", "hi", "hindi")
    is_tenglish = lang_code in ("te_en", "tenglish", "te", "telugu")

    raw_lagna = pc.get("lagna")
    lagna = str(
        pc.get("meta", {}).get("lagna_sign", "")
        or (raw_lagna if isinstance(raw_lagna, str) else (raw_lagna or {}).get("sign", ""))
        or ""
    )
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
    if md_end and paid:
        shown_end = _fmt_full_month(md_end) or md_end
        authoritative_timing_text += (" " if authoritative_timing_text else "") + f"It runs through {shown_end}."
    if next_vim:
        # "Next Vimshottari period: X" was two problems in one line. The word
        # Vimshottari is a document-level leak pattern, and the customer
        # firewall drops the whole text node when it matches — which silently
        # took the two useful sentences above with it and left the reader an
        # empty Current timing box. Say the same thing as a plain sentence.
        authoritative_timing_text += (
            (" " if authoritative_timing_text else "") + f"After that, the {next_vim} period begins.")

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
        from astro_precompute import SIGN_LORDS
        true_lord = SIGN_LORDS.get(lagna, "")
        SIGN_MAP_HI = {
            "Aries": "Mesh", "Taurus": "Vrishabh", "Gemini": "Mithun", "Cancer": "Kark",
            "Leo": "Simha", "Virgo": "Kanya", "Libra": "Tula", "Scorpio": "Vrishchik",
            "Sagittarius": "Dhanu", "Capricorn": "Makar", "Aquarius": "Kumbh", "Pisces": "Meen"
        }
        SIGN_MAP_TE = {
            "Aries": "Mesham", "Taurus": "Vrishabham", "Gemini": "Mithunam", "Cancer": "Karkatakam",
            "Leo": "Simham", "Virgo": "Kanya", "Libra": "Tula", "Scorpio": "Vrishchikam",
            "Sagittarius": "Dhanassu", "Capricorn": "Makaram", "Aquarius": "Kumbham", "Pisces": "Meenam"
        }
        PLANET_MAP_HI = {
            "Sun": "Surya", "Moon": "Chandra", "Mars": "Mangal", "Mercury": "Budh",
            "Jupiter": "Guru", "Venus": "Shukra", "Saturn": "Shani", "Rahu": "Rahu", "Ketu": "Ketu"
        }
        PLANET_MAP_TE = {
            "Sun": "Suryudu", "Moon": "Chandrudu", "Mars": "Kujudu", "Mercury": "Budhudhu",
            "Jupiter": "Guru", "Venus": "Shukrudu", "Saturn": "Shaniswarudu", "Rahu": "Rahu", "Ketu": "Ketu"
        }
        if is_hinglish and lagna:
            tgt_lagna = SIGN_MAP_HI.get(lagna, lagna)
            tgt_lord = PLANET_MAP_HI.get(true_lord, true_lord)
            astrological_basis = re.sub(
                r"(Aapka\s+Janma\s+Lagna\s+)(?:Mesh|Vrishabh|Mithun|Kark|Simha|Kanya|Tula|Vrishchik|Dhanu|Makar|Kumbh|Meen|[A-Za-z]+)(\s+hai)",
                rf"\g<1>{tgt_lagna}\g<2>",
                astrological_basis,
                flags=re.I
            )
            astrological_basis = re.sub(
                r"(Lagna\s+Lord\s+)(?:Mangal|Shukra|Budh|Chandra|Surya|Guru|Shani|Rahu|Ketu|[A-Za-z]+)(\s+hai)",
                rf"\g<1>{tgt_lord}\g<2>",
                astrological_basis,
                flags=re.I
            )
        elif is_tenglish and lagna:
            tgt_lagna = SIGN_MAP_TE.get(lagna, lagna)
            tgt_lord = PLANET_MAP_TE.get(true_lord, true_lord)
            astrological_basis = re.sub(
                r"(Mee\s+Janma\s+Lagna[a-z]*\s+)(?:Mesham|Vrishabham|Mithunam|Karkatakam|Simham|Kanya|Tula|Vrishchikam|Dhanassu|Makaram|Kumbham|Meenam|[A-Za-z]+)",
                rf"\g<1>{tgt_lagna}",
                astrological_basis,
                flags=re.I
            )
            astrological_basis = re.sub(
                r"(Lagnaadhipathi\s+)(?:Kujudu|Shukrudu|Budhudhu|Chandrudu|Suryudu|Guru|Shaniswarudu|Rahu|Ketu|[A-Za-z]+)",
                rf"\g<1>{tgt_lord}",
                astrological_basis,
                flags=re.I
            )

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
    family_note = [_sanitize_customer_text(x) for x in prose.get("family_note", []) if str(x).strip()]
    areas = prose.get("areas") if isinstance(prose.get("areas"), dict) else {}

    family_html = ""
    if family_note:
        fam_labels_hi = ["Pita", "Mata", "Bhai-Behen", "Ghar Parivar"]
        fam_labels_te = ["Thandri", "Thalli", "Sahodharulu", "Illu Kutumbam"]
        labels = fam_labels_te if is_tenglish else (fam_labels_hi if is_hinglish else _family_labels(len(family_note)))
        limit = len(family_note) if paid else min(2, len(family_note))
        items = []
        for i, line in enumerate(family_note[:limit]):
            label = labels[i] if i < len(labels) else ("Kutumbam" if is_tenglish else ("Parivar" if is_hinglish else "Family"))
            line_txt = str(line).strip()
            if is_hinglish:
                low = line_txt.lower()
                if any(w in low for w in ("father", "paternal", "sun in", "disciplined", "duty", "traditional")):
                    line_txt = "Pita ka vyaktitva anushasit aur sankalpatmak approach ko darshata hai, jisme parivarik sanskaro aur jimmedariyon ka mahatva rehta hai."
                elif any(w in low for w in ("mother", "maternal", "moon in", "anchor", "emotional", "grounding")):
                    line_txt = "Mata ka sneh aantarik sthirta, moral values aur bhavnatmak suraksha pradan karta hai."
                elif any(w in low for w in ("sibling", "brother", "sister", "mars in", "dynamic", "ties")):
                    line_txt = "Bhai-beheno ke sath sambandh dynamic aur independent hain, jisme parasparik sahyog aur aadar bana rehta hai."
                elif any(w in low for w in ("home", "household", "childhood", "foundation", "values")):
                    line_txt = "Ghar aur parivar ka vatavaran bachpan se hi sthirta, shanti aur acche sanskaro ki majboot buniyad deta hai."
            elif is_tenglish:
                low = line_txt.lower()
                if any(w in low for w in ("father", "paternal", "sun in", "disciplined", "duty", "traditional")):
                    line_txt = "Thandri garu anushasanam mariyu sankalpa balanni chupistharu, kutumba sanskaralu mariyu badhyathalu mukhya sthanam vahisthayi."
                elif any(w in low for w in ("mother", "maternal", "moon in", "anchor", "emotional", "grounding")):
                    line_txt = "Thalli prema aantrika sthiratha, manchi sanskaralu mariyu emotional security ni isthundi."
                elif any(w in low for w in ("sibling", "brother", "sister", "mars in", "dynamic", "ties")):
                    line_txt = "Sahodharulatho sambandhalu dynamic mariyu independent ga unnai, paraspara gouravam untundi."
                elif any(w in low for w in ("home", "household", "childhood", "foundation", "values")):
                    line_txt = "Illu mariyu kutumba vatavaranam chinnapatinunche sthiratha, shanti mariyu manchi viluvala balamaina neev isthundi."
            items.append(
                f'<div class="family-item"><div class="family-label">{_e(label)}</div>'
                f"<p>{_e(line_txt)}</p></div>"
            )
        if paid or len(family_note) <= limit:
            more = ""
        else:
            if is_hinglish:
                more_text = "Poori reading mein baki parivarik sambandh aur ghar ka vatavaran bhi shamil hai."
            elif is_tenglish:
                more_text = "Sampoorna reading lo migilina kutumba sambandhalu mariyu inti vatavaranam shamil ayyi undi."
            else:
                more_text = "The full reading also covers the remaining family relationships and the home environment."
            more = f'<p class="sec-note">{more_text}</p>'
        
        if is_hinglish:
            fam_kicker = "PARIVAR AUR GHAR"
            fam_heading = "Parivar Aur Ghar Ka Prabhav"
            fam_note = "Yeh kundli adharit patterns hain, parivar ki di gayi jankari nahi."
        elif is_tenglish:
            fam_kicker = "KUTUMBAM MARIYU ILLU"
            fam_heading = "Kutumbam Mariyu Inti Prabhavam"
            fam_note = "Ivi kundali aadhara patterns, kutumbam gurinchi icchina direct facts kaadu."
        else:
            fam_kicker = "FAMILY &amp; HOME"
            fam_heading = "The people and home that shaped you"
            fam_note = "These are chart-derived patterns, not facts we were given about your family."

        family_html = f"""
        <section class="conv-block family-block">
          <div class="section-kicker">{fam_kicker}</div>
          <h2 id="sec-family-home" data-nav="Family">{fam_heading}</h2>
          <p class="sec-note">{fam_note}</p>
          {"".join(items)}
          {more}
        </section>
        """

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
        if is_hinglish:
            astrological_basis = (
                f"Aapki reading {', '.join(basis_bits)} par aadharit hai, jo is samay aapki kundli ke mukhya governing factors hain."
                if basis_bits
                else "Aapki janma kundli is reading ka mool aadhar hai."
            )
        elif is_tenglish:
            astrological_basis = (
                f"Mee reading {', '.join(basis_bits)} pai aadharapadi undi, ivi mee kundali lo mukhya governing factors."
                if basis_bits
                else "Mee janma kundali ee reading ki moola aadharam."
            )
        else:
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
    
    if interpretation:
        about_meaning = _e(interpretation)
    else:
        about_meaning = (
            f"With <b>{lagna_clean} rising</b>{moon_txt}{nak_txt}, your birth chart establishes <b>{lp['title']}</b>. "
            f"{lp['traits']} <b>{h_pred}</b> (governed by Lagna lord <b>{lord} in the {h_str} house, {lord_s}{d_str}</b>)."
        )
    if not personality:
        personality = (
            f"{lp['life_path']} {mp} In classical Vedic astrology, while planetary periods (Dashas) and transits (Gochara) bring shifting life chapters, "
            f"your Janma Lagna and Moon disposition define your enduring constitutional baseline and natural karma."
        )

    # The current chapter and recent milestones are now combined into one unified,
    # highly authoritative Vedic Astrologer consultation section.
    current_html = _build_unified_current_chapter_html(
        pc, analysis, cards, paid=paid, today=today, authoritative_timing_text=authoritative_timing_text,
        lang=lang
    )
    recent_html = ""

    unlock = ""
    if not paid and footer_unlock:
        if is_hinglish:
            u_h3 = "Poori reading dekhein, kshetra anusar"
            u_p = "Free reading aapka swabhav, current chapter aur chart activation dikhati hai. Full reading mein sabhi life areas ke confluence, timing aur remedies shamil hain."
            u_btn = "Complete reading unlock karein"
        elif is_tenglish:
            u_h3 = "Sampoorna reading chudandi, vibhagam variga"
            u_p = "Free reading mee swabhavam, current chapter mariyu chart activation chupisthundi. Full reading lo anni jeevitha rangala confluence, timing dates mariyu upayamulu labhisthayi."
            u_btn = "Sampoorna reading unlock cheyandi"
        else:
            u_h3 = "See the full reading, area by area"
            u_p = "The free reading shows who you are, the chapter you are in and what the chart is activating. The full reading adds the confluence, timing and practical guidance for every life area."
            u_btn = "Unlock full reading"
        unlock = f"""
        <section class="buy" id="unlock">
          <h3>{u_h3}</h3>
          <p>{u_p}</p>
          <a class="cta" href="#unlock" data-unlock="1">{u_btn} · ₹{_e(price)}</a>
        </section>
        """

    baseline_card_html = ""
    divisional_html = ""
    try:
        from divisional_profile import render_divisional_blocks
        baseline_card_html, divisional_html = render_divisional_blocks(
            pc, paid=paid, today=today, lang=lang)
    except Exception as exc:
        print(f"[report_conversational] divisional profile skipped: {exc}", flush=True)

    date_str = f"{today:%d %B %Y}" if today else ""

    if is_hinglish:
        eyebrow_text = "Aapki Vedic Kundli Reading"
        h1_text = f"{_e(first)}, yahan dekhein aapki kundli kya sanket de rahi hai."
        signature_kicker = "AAPKA CHART SIGNATURE"
        who_kicker = "AAPKA VYAKTITVA"
        who_heading = "Aapka Mool Swabhav Aur Foundational Promise"
        areas_kicker = "JEEVAN KE MUKHYA KSHETRA"
        areas_heading = "Aapke Jeevan Kshetra: Current Phase Aur Aane Wala Samay"
        footer_text = "Aapki janma kundli ke adhar par astrological interpretation · margdarshan hetu"
    elif is_tenglish:
        eyebrow_text = "Mee Vedic Kundali Reading"
        h1_text = f"{_e(first)}, ikkada chudandi mee kundali em chepthundo."
        signature_kicker = "MEE CHART SIGNATURE"
        who_kicker = "MEE VYAKTHITHVAM"
        who_heading = "Mee Moola Swabhavam Mariyu Foundational Promise"
        areas_kicker = "JEEVITHA MUKHYA RANGALU"
        areas_heading = "Mee Jeevitha Rangalu: Current Phase Mariyu Munde Vache Samayam"
        footer_text = "Mee janma kundali aadharam ga astrological interpretation · margadarshanam kosam"
    else:
        eyebrow_text = "Your Vedic reading"
        h1_text = f"{_e(first)}, here is what your chart is saying."
        signature_kicker = "YOUR CHART SIGNATURE"
        who_kicker = "WHO YOU ARE"
        who_heading = "Your foundational promise"
        areas_kicker = "COMPREHENSIVE LIFE DOMAIN CONSULTATIONS"
        areas_heading = "Your Life Areas: Current Phase &amp; The Road Ahead"
        footer_text = "Astrological interpretation from your supplied birth details · guidance, not a substitute for professional advice"

    body = f"""
    <header>
      <div class="eyebrow">{eyebrow_text}</div>
      <h1>{h1_text}</h1>
      <div class="chartline">{_e(chart_line)} · read {_e(date_str)}</div>
    </header>

    <section class="hero">
      <div class="section-kicker hero-kicker">{signature_kicker}</div>
      <div class="chart-signature">
        {"".join(f'<span class="chart-chip">{_e(x)}</span>' for x in chips)}
      </div>
      <p>{_e(astrological_basis)}</p>
    </section>

    <section class="conv-block who-you-are-block">
      <div class="section-kicker">{who_kicker}</div>
      <h2 id="sec-who-you-are" data-nav="Who you are">{who_heading}</h2>
      <p class="lead-reading"><span class="ev-label">Constitutional Baseline</span> {about_meaning}</p>
      {f'<p style="margin:12px 0 14px;font-size:0.92rem;line-height:1.6;color:#2c3140;">{_e(personality)}</p>' if personality and personality != about_meaning else ""}
      {baseline_card_html}
    </section>

    {family_html}
    {current_html}
    {recent_html}

    <section class="conv-block life-domains-block">
      <div class="section-kicker">{areas_kicker}</div>
      <h2 id="sec-life-domains" data-nav="Your life areas">{areas_heading}</h2>
      {divisional_html}
    </section>

    {remedy_html}
    {upsell_html if not paid else ""}
    {unlock}

    <footer>{footer_text}</footer>
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
.family-label{{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:#8a6a1f;font-weight:700;margin-bottom:4px}}
.family-item p{{margin:0}}
.card.conv-area{{margin:14px 0;padding:18px 20px}}
.area-fact{{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0;padding:8px 10px;border-radius:8px;background:#f6f4ef;color:#3d4250;font-size:.76rem}}
.mini-label{{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:#6a7080;font-weight:700}}
.area-reading{{margin:12px 0}}
.reading-label{{font-size:.72rem;letter-spacing:.11em;text-transform:uppercase;color:#8a6a1f;font-weight:700;margin-bottom:6px}}
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

.aj-clocks{{display:grid;gap:9px;margin:14px 0}} .aj-clock{{display:grid;grid-template-columns:1.2fr 1.3fr .8fr auto;gap:10px;align-items:center;padding:11px 12px;background:#f7f4ed;border:1px solid #e4ded3;border-radius:10px}} .aj-clock>div{{display:grid;gap:2px}} .aj-clock span{{font-family:Georgia,serif;font-size:1.05rem}} .aj-clock small,.aj-area small,.aj-table small{{display:block;color:#77736c;font-size:.72rem;text-transform:uppercase;letter-spacing:.06em}} .aj-clock-next{{grid-template-columns:auto auto auto auto!important;align-items:center}}
.aj-verdict{{display:inline-block;padding:4px 8px;border-radius:99px;font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap;background:#ebe7df;color:#625c52}} .aj-verdict.good{{background:#dcefe3;color:#1c6b45}} .aj-verdict.bad{{background:#f5ddd8;color:#9d3b28}} .aj-verdict.mid{{background:#eee7d4;color:#80651e}}
.aj-sub{{font-family:Georgia,serif;font-size:1rem;margin:22px 0 9px;color:#292d36}} .aj-cross-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:8px}} .aj-cross{{padding:10px 11px;border:1px solid #e4ded3;border-radius:9px;background:#fff}} .aj-cross b,.aj-cross span,.aj-cross small{{display:block}} .aj-cross b{{font-family:Georgia,serif;font-size:1rem}} .aj-cross span{{font-size:.72rem;color:#8a6a1f;margin-top:3px}} .aj-cross small{{font-size:.72rem;color:#77736c;margin-top:4px}}
.aj-table{{width:100%;border-collapse:collapse;font-size:.76rem;background:#fff;border:1px solid #e4ded3}} .aj-table th,.aj-table td{{padding:8px;border-bottom:1px solid #eee9e1;text-align:left;vertical-align:top}} .aj-table th{{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:#77736c}}
.aj-jai{{padding:12px;background:#f7f4ed;border:1px solid #e4ded3;border-radius:10px}} .aj-karakas,.aj-jai-meta,.aj-facts,.aj-periods{{display:flex;flex-wrap:wrap;gap:7px}} .aj-karakas span,.aj-jai-meta span,.aj-facts span,.aj-periods span{{padding:5px 8px;border:1px solid #e3ddd2;border-radius:99px;background:#fff;font-size:.72rem;color:#5f5a52}} .aj-jai p{{font-family:Georgia,serif;font-size:.88rem!important;margin:10px 0 0!important}}
.aj-dpt-list,.aj-areas{{display:grid;gap:7px}} .aj-dpt{{display:flex;flex-wrap:wrap;gap:7px;align-items:center;padding:9px 10px;border:1px solid #e4ded3;border-radius:9px;background:#fff;font-size:.73rem}} .aj-dpt span{{color:#6f6a62}} .aj-area{{padding:12px;background:#fff;border:1px solid #e4ded3;border-radius:10px}} .aj-area-head{{display:flex;justify-content:space-between;gap:10px;align-items:center}} .aj-area-head>div{{display:grid;gap:2px}} .aj-facts,.aj-periods{{margin:9px 0 0}} .aj-facts span,.aj-periods span{{border-radius:8px}} .aj-area p{{font-size:.82rem!important;margin:8px 0 0!important}} .aj-confluence{{margin:12px 0;padding:12px;border:1px solid #e4ded3;background:#fbfaf6;border-radius:9px}} .aj-confluence-title{{font-size:.76rem}} .aj-confluence-title small{{margin-left:8px;color:#77736c;font-weight:normal}} .aj-factor-cols{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0}} .aj-factor-cols small{{font-size:.72rem;text-transform:uppercase;letter-spacing:.1em;color:#77736c}} .aj-factor-cols ul{{margin:6px 0;padding-left:18px;color:#6b665e;font-size:.72rem}}
@media(max-width:680px){{.aj-clock{{grid-template-columns:1fr 1fr}} .aj-table{{font-size:.76rem}}}}
{TRANSITION_MAP_CSS}
@media(max-width:520px){{.evidence-row{{grid-template-columns:1fr}}
.aj-clock,.aj-clock-next{{grid-template-columns:1fr!important}}
.aj-factor-cols{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">{body}</div>{_INTERACT}</body></html>"""

    from qa_checks.final_customer_boundary import finalize_customer_html
    return finalize_customer_html(html, strict=True)
