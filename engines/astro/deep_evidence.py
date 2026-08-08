"""Shared deep-dive evidence — computed once per report, reused everywhere.

Ports the logic of question_house_deepdive into structured data (not HTML):
divisional chart diagnosis, house lords/karakas, 108 classical rules,
dasha/transit confluence windows, and slow-planet transits over each area.
"""

from __future__ import annotations

import datetime as _dt
from datetime import date
from typing import Any, Optional

# Product area → (varga, field-key, plain name, houses, karakas)
AREA_DEEP: dict[str, tuple] = {
    "career": ("D10", "profession", "career & profession", (10, 6, 11),
               ("Sun", "Saturn", "Mercury")),
    "money": ("D2", "wealth", "wealth & finances", (2, 11),
              ("Jupiter", "Venus")),
    "love": ("D9", "spouse", "marriage & your partner", (7, 5),
             ("Venus", "Jupiter")),
    "home": ("D4", "home", "home & property", (4, 2),
             ("Mars", "Moon", "Venus")),
    "children": ("D7", "children", "children & progeny", (5, 9),
                 ("Jupiter",)),
    "health": ("D30", "troubles", "health & vitality", (1, 6, 8),
               ("Sun", "Mars", "Saturn")),
    "learning": ("D24", "education", "education & learning", (9, 5),
                 ("Mercury", "Jupiter")),
    "inner": ("D20", "spiritual", "faith & inner growth", (12, 9),
              ("Jupiter", "Ketu")),
}

_DOMAIN_KW: dict[str, tuple[str, ...]] = {
    "career": ("career", "profession", "job", "10th", "tenth", "status",
               "government", "raj"),
    "money": ("wealth", "money", "rich", "income", "gain", "2nd", "11th",
              "second", "eleventh", "dhana"),
    "love": ("marri", "spouse", "wife", "husband", "partner", "7th",
             "seventh", "venus"),
    "home": ("home", "property", "house", "land", "vehicle", "4th", "mother"),
    "children": ("child", "children", "progeny", "5th", "fifth", "putra"),
    "health": ("health", "disease", "illness", "vital", "6th", "8th",
               "sixth", "eighth"),
    "learning": ("educat", "learn", "study", "intellig", "knowledge", "4th", "5th"),
    "inner": ("spiritual", "moksha", "dharma", "12th", "9th", "ketu", "mind"),
}

_RATE_NAME = {
    "love": "Marriage", "health": "Health", "inner": "Spirituality/Mind",
}
_RATEWORD = {
    "fav": "favourable and opening up",
    "mix": "mixed — good and testing patches",
    "chal": "demanding patience and care",
}
_VLABEL = {
    "strong": "strong and well-built",
    "mixed": "workable but mixed",
    "weak": "under strain",
}

_active: Optional["DeepEvidence"] = None


def begin(pc: dict, *, lat: Optional[float] = None, lon: Optional[float] = None,
          tz: float = 5.5, today: Optional[date] = None) -> "DeepEvidence":
    """Start a report-scoped evidence cache (call once per full_report)."""
    global _active
    _active = DeepEvidence(pc, lat=lat, lon=lon, tz=tz, today=today)
    return _active


def end() -> None:
    global _active
    _active = None


def current() -> Optional["DeepEvidence"]:
    return _active


def for_area(area_key: str, *, house: Optional[int] = None) -> dict:
    ctx = current()
    if ctx is None:
        return {}
    return ctx.for_area(area_key, house=house)


def _ord(n: Any) -> str:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return ""
    return f"{n}" + ("th" if 10 <= n % 100 <= 20
                     else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def _fmt(d: Any) -> str:
    if isinstance(d, date):
        return d.strftime("%b %Y")
    return "—"


class DeepEvidence:
    def __init__(self, pc: dict, *, lat: Optional[float] = None,
                 lon: Optional[float] = None, tz: float = 5.5,
                 today: Optional[date] = None):
        self.pc = pc
        self.lat = lat
        self.lon = lon
        self.tz = tz
        self.today = today or date.today()
        self._verdicts: Optional[list] = None
        self._windows: Optional[list] = None
        self._caches: Optional[dict] = None
        self._transit_positions: Optional[dict] = None
        self._area: dict[str, dict] = {}
        self._palm_bridge: Optional[dict] = None
        self._palm_bridge_loaded: bool = False

    def palm_bridge(self) -> Optional[dict]:
        """Memoised astro-palmistry bridge — one build() per report, not per area."""
        if not self._palm_bridge_loaded:
            self._palm_bridge_loaded = True
            try:
                from palm_astro_bridge import build  # noqa: PLC0415
                self._palm_bridge = build(self.pc, None)
            except Exception:  # noqa: BLE001
                self._palm_bridge = {}
        return self._palm_bridge

    def _ensure_base(self) -> None:
        if self._verdicts is not None:
            return
        self._verdicts = []
        try:
            from prediction108_rules import evaluate_all  # noqa: PLC0415
            self._verdicts = list(evaluate_all(self.pc))
        except Exception:  # noqa: BLE001
            self._verdicts = []

        self._windows, self._caches = [], {}
        try:
            from dasha_confluence_report import compute_windows  # noqa: PLC0415
            self._windows, self._caches = compute_windows(
                self.pc, self.lat, self.lon, self.tz, years=3)
        except Exception:  # noqa: BLE001
            self._windows, self._caches = [], {}

        self._transit_positions = {}
        try:
            from prediction108_transit import build_transit_context  # noqa: PLC0415
            tx = build_transit_context(self.pc, on=self.today)
            self._transit_positions = (tx.get("positions") or {}) if tx else {}
        except Exception:  # noqa: BLE001
            self._transit_positions = {}

    def rules_for_area(self, area_key: str, houses: tuple,
                       *, limit: int = 4) -> tuple[list[str], list[str]]:
        """Forward-looking 108-rule lines (pos, neg) for this area."""
        self._ensure_base()
        kws = list(_DOMAIN_KW.get(area_key, ()))
        kws += [f"{_ord(h)}" for h in houses]
        kws = [k.lower() for k in kws]
        pos, neg, seen = [], [], set()
        try:
            from final_user_report import _classify_rule, _compose_rule_line  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return [], []

        for v in self._verdicts or []:
            if v.verdict not in ("HIT", "PARTIAL"):
                continue
            blob = f"{v.title} {v.finding} {v.prediction}".lower()
            if not any(k in blob for k in kws):
                continue
            line = _compose_rule_line(v)
            if not line or len(line) < 20:
                continue
            sig = line[:45].lower()
            if sig in seen:
                continue
            seen.add(sig)
            pol = _classify_rule(v)
            (neg if pol == "neg" else pos).append(line)
        return pos[:limit], neg[:limit]

    def _house_facts(self, houses: tuple, karakas: tuple) -> list[str]:
        try:
            from prediction108_rules import hlord, phouse, pdig  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return []
        out, seen = [], set()
        for h in houses:
            L = hlord(self.pc, h)
            if not L or L in seen:
                continue
            seen.add(L)
            out.append(
                f"the {_ord(h)} house (its ruler {L} sits in the "
                f"{_ord(phouse(self.pc, L))}, {pdig(self.pc, L) or 'neutral'})")
        for k in karakas:
            if k and k not in seen:
                seen.add(k)
                out.append(
                    f"{k} (the natural significator) in the "
                    f"{_ord(phouse(self.pc, k))} ({pdig(self.pc, k) or 'neutral'})")
        return out

    def _transit_note(self, houses: tuple) -> dict:
        pos = self._transit_positions or {}
        support, pressure = [], []
        for p in ("Jupiter", "Saturn", "Mars", "Rahu", "Ketu"):
            h = (pos.get(p, {}) or {}).get("house_natal", 0)
            if h not in houses:
                continue
            if p == "Jupiter":
                support.append(
                    f"Jupiter is transiting your {_ord(h)} house (a blessing on this area)")
            else:
                pressure.append(f"{p} is transiting your {_ord(h)} house")
        note = ""
        if support:
            note = "; ".join(support)
        if pressure:
            extra = "pressure from " + ", ".join(pressure) + " — go steady and avoid haste"
            note = f"{note}. {extra}" if note else extra
        return {"support": support, "pressure": pressure, "note": note}

    def _varga_field_facts(self, varga: str, key: str,
                          karakas: tuple) -> dict:
        """Field-specific divisional facts (house lord, karaka) — not prose."""
        try:
            from chart_summary_report import SIGN_LORDS, NAT_BENEFIC, NAT_MALEFIC  # noqa: PLC0415
            from final_user_report import (  # noqa: PLC0415
                VARGA_FOCUS, _DIG_GOOD, _dig, _v_house_of, _v_occupants,
                _v_sign_of_house, _varga_lagna, _varga_sign,
            )
        except Exception:  # noqa: BLE001
            return {}

        vl = _varga_lagna(self.pc, varga)
        if not vl:
            return {}
        H, plain, _sec = VARGA_FOCUS.get(key, (1, "this area", None))
        hsign = _v_sign_of_house(vl, H)
        hlord = SIGN_LORDS.get(hsign, "")
        hlordsign = _varga_sign(self.pc, varga, hlord)
        hldig = _dig(hlord, hlordsign)
        hlhouse = _v_house_of(vl, hlordsign)
        occ = _v_occupants(self.pc, varga, hsign)
        if H in (3, 6, 10, 11):
            mal = []
        else:
            mal = [m for m in occ if m in NAT_MALEFIC and m != hlord
                   and _dig(m, hsign) not in _DIG_GOOD]
        ben = [b for b in occ if b in NAT_BENEFIC and b != hlord]
        kar = next((k for k in karakas if k), "")
        karsign = _varga_sign(self.pc, varga, kar) if kar else ""
        kardig = _dig(kar, karsign)
        karhouse = _v_house_of(vl, karsign) if karsign else 0
        return {
            "field_house": H,
            "field_plain": plain,
            "field_lord": hlord,
            "field_lord_dignity": hldig,
            "field_lord_house": hlhouse,
            "benefics_in_field": ben,
            "malefics_in_field": mal,
            "karaka": kar,
            "karaka_dignity": kardig,
            "karaka_house": karhouse,
        }

    def _varga_block(self, varga: str, key: str, karakas: tuple) -> dict:
        out = {"code": varga, "name": varga, "gov": "", "strength": "mixed",
               "diagnosis": "", "ruler": "", "ruler_dignity": "",
               "ruler_house": 0, "strong_planets": []}
        try:
            from chart_summary_report import VARGA_GOV, _varga_data  # noqa: PLC0415
            from final_user_report import _varga_diagnosis  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return out

        vmeta = {c: (n, g) for c, n, g in VARGA_GOV}
        vname, vgov = vmeta.get(varga, (varga, ""))
        out["name"] = vname
        out["gov"] = vgov
        if varga != "D1":
            vd = _varga_data(self.pc, varga, vname, vgov) or {}
            out["strength"] = vd.get("vcls", "mixed")
            out["ruler"] = vd.get("lord", "")
            out["ruler_dignity"] = vd.get("ldig", "")
            out["ruler_house"] = vd.get("lhouse", 0)
            out["strong_planets"] = list(vd.get("strong_list") or [])
            out["diagnosis"] = _varga_diagnosis(self.pc, varga, key, list(karakas))
            out.update(self._varga_field_facts(varga, key, karakas))
        return out

    def _windows_for_field(self, area_key: str, varga: str, key: str,
                           houses: tuple, karakas: tuple) -> tuple[list, Optional[str], Optional[dict]]:
        self._ensure_base()
        name = _RATE_NAME.get(area_key, key.title())
        field = (name, key, varga, list(houses), list(karakas))
        rows, cur_rating, cur_win = [], None, None
        try:
            from dasha_confluence_report import rate_field  # noqa: PLC0415
        except Exception:  # noqa: BLE001
            return [], None, None

        for w in (self._windows or [])[:5]:
            r = rate_field(self.pc, field, w, self._caches or {})
            if w.get("is_now") and cur_rating is None:
                cur_rating = r["rating"]
                cur_win = w
            rows.append({
                "period": f"{_fmt(w['row']['start'])} – {_fmt(w['row']['end'])}",
                "now": w.get("is_now"),
                "md": w["row"].get("md", ""),
                "ad": w["row"].get("ad", ""),
                "jai": w["ov"].get("chara_sign", ""),
                "yog": w["ov"].get("yogini", ""),
                "rating": r["rating"],
                "word": _RATEWORD.get(r["rating"], r["rating"]),
                "reason": r.get("reason", ""),
            })
        if cur_rating is None and rows:
            cur_rating = rows[0]["rating"]
            cur_win = next((w for w in (self._windows or []) if w.get("is_now")),
                           (self._windows or [None])[0])
        return rows, cur_rating, cur_win

    def vote_triplet(self, area_key: str, house: int) -> list[tuple[str, float, str]]:
        """Three extra votes: classical rules, sky now, period clock."""
        cfg = AREA_DEEP.get(area_key)
        if not cfg:
            return []
        varga, key, _area, houses, karakas = cfg
        hs = tuple(sorted(set((house,) + tuple(houses))))
        pos, neg = self.rules_for_area(area_key, hs)
        votes: list[tuple[str, float, str]] = []

        rule_score = min(2.0, max(-2.0, 0.5 * (len(pos) - len(neg))))
        if pos or neg:
            sample = (pos or neg)[0][:120]
            votes.append((
                "the classical rule-book",
                rule_score,
                f"{len(pos)} classical rule{'s' if len(pos) != 1 else ''} support this area"
                + (f"; watch: {neg[0][:80]}" if neg else "")
                + (f" — e.g. {sample[:90]}" if sample else ""),
            ))

        tr = self._transit_note(hs)
        if tr["support"]:
            votes.append(("the sky right now", 1.2, tr["support"][0]))
        elif tr["pressure"]:
            votes.append(("the sky right now", -1.0, tr["pressure"][0] + " — go steady"))

        _rows, cur_rating, cur_win = self._windows_for_field(
            area_key, varga, key, hs, karakas)
        if cur_rating:
            val = {"fav": 1.5, "mix": 0.0, "chal": -1.5}.get(cur_rating, 0.0)
            reason = ""
            if _rows and _rows[0].get("reason"):
                reason = _rows[0]["reason"][:100]
            elif _rows:
                reason = _rows[0].get("word", "")
            votes.append((
                "the period clock",
                val,
                f"The running period reads {_RATEWORD.get(cur_rating, cur_rating)} "
                f"for this area"
                + (f" — {reason}" if reason else ""),
            ))
        return votes

    def for_area(self, area_key: str, *, house: Optional[int] = None) -> dict:
        if area_key in self._area:
            return self._area[area_key]
        cfg = AREA_DEEP.get(area_key)
        if not cfg:
            return {}
        varga, key, area_name, houses, karakas = cfg
        if house is None:
            house = houses[0]
        hs = tuple(sorted(set((house,) + tuple(houses))))

        self._ensure_base()
        varga_blk = self._varga_block(varga, key, karakas)
        facts = self._house_facts(hs, karakas)
        pos, neg = self.rules_for_area(area_key, hs)
        win_rows, cur_rating, cur_win = self._windows_for_field(
            area_key, varga, key, hs, karakas)
        transit = self._transit_note(hs)

        try:
            from final_user_report import _strength_of, _label  # noqa: PLC0415
            sc = _strength_of(self.pc, list(hs), list(karakas), self._caches or {}, key=key)
            house_label = _label(sc)
        except Exception:  # noqa: BLE001
            house_label = "mixed"

        vcls = varga_blk.get("strength", "mixed")
        score = 0.0
        score += {"strong": 1, "mixed": 0, "weak": -1}.get(vcls, 0)
        score += {"strong": 1, "mixed": 0, "weak": -1}.get(house_label, 0)
        score += 0.4 * (len(pos) - len(neg))
        score += {"fav": 1, "mix": 0, "chal": -1}.get(cur_rating or "mix", 0)
        if transit.get("pressure"):
            score -= 0.4
        if score >= 1.0:
            overall, overall_txt = "fav", "Broadly favourable — the chart supports this area."
        elif score <= -1.0:
            overall, overall_txt = ("chal",
                                    "This area needs patience, effort and remedy — "
                                    "the chart flags real friction here.")
        else:
            overall, overall_txt = ("mix",
                                    "A mixed picture — workable with the right timing "
                                    "and steady effort.")

        out = {
            "area_key": area_key,
            "area_name": area_name,
            "houses": hs,
            "varga": varga_blk,
            "house_facts": facts,
            "house_strength": house_label,
            "rules_pos": pos,
            "rules_neg": neg,
            "windows": win_rows,
            "current_rating": cur_rating or "mix",
            "current_window": win_rows[0] if win_rows else {},
            "transit": transit,
            "overall": {"rating": overall, "text": overall_txt},
            "evidence_lines": self._evidence_lines(varga_blk, facts, pos, neg, transit, win_rows),
        }
        self._area[area_key] = out
        return out

    def _evidence_lines(self, varga_blk, facts, pos, neg, transit, win_rows) -> list[str]:
        lines = []
        diag = (varga_blk.get("diagnosis") or "").strip()
        if diag:
            lines.append(diag)
        for f in facts[:2]:
            lines.append(f)
        if pos:
            lines.append(pos[0])
        if neg:
            lines.append(f"Watch: {neg[0]}")
        if transit.get("note"):
            lines.append(transit["note"])
        if win_rows and win_rows[0].get("word"):
            w0 = win_rows[0]
            tag = " (now)" if w0.get("now") else ""
            lines.append(
                f"Period {w0['period']}{tag}: {w0['word']}"
                + (f" — {w0['reason'][:80]}" if w0.get("reason") else ""))
        return lines[:6]

    def natal_rule_hits(self) -> dict[int, Any]:
        """Rule number → RuleVerdict for natal HITs (for report_recognition)."""
        self._ensure_base()
        hits = {}
        for v in self._verdicts or []:
            if v.verdict == "HIT" and getattr(v, "category", "") == "natal":
                hits[v.no] = v
        return hits
