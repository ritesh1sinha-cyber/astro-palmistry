"""Structured evidence bundles from existing timing rows — no new astrology math."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import re
from typing import Any, Optional


@dataclass
class EvidenceBundle:
    area: str
    direction: str
    age_band: str
    age_at_period: int = 0
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    primary_dasha: str = ""
    sub_dasha: str = ""
    transit_planet: str = ""
    transit_house: int = 0
    birth_house: int = 0
    house_strength: str = "mixed"
    divisional_chart: str = ""
    divisional_support: str = "mixed"
    secondary_confirmation: bool = False
    support_factors: list[str] = field(default_factory=list)
    pressure_factors: list[str] = field(default_factory=list)
    manifestation_candidates: list[str] = field(default_factory=list)
    bav: int = 0
    promise: str = "mixed"
    dasha_direction: str = "mixed"
    confidence: str = "moderate"

    def signature(self) -> tuple:
        return (
            self.area,
            self.age_band,
            self.direction,
            self.primary_dasha,
            self.sub_dasha,
            self.transit_planet,
            self.transit_house,
            self.divisional_chart,
            self.divisional_support,
            tuple(sorted(self.manifestation_candidates)),
            tuple(sorted(self.support_factors)),
            tuple(sorted(self.pressure_factors)),
        )


def _varga_for_area(area: str) -> tuple[str, str]:
    try:
        from report_confluence import AREA_VARGA
        code, _name = AREA_VARGA.get(area, ("", ""))
        return code, _name
    except Exception:  # noqa: BLE001
        return "", ""


def _varga_strength(pc: dict, area: str) -> str:
    try:
        import deep_evidence as DE
        varga = (DE.for_area(area) or {}).get("varga") or {}
        return str(varga.get("strength") or "mixed")
    except Exception:  # noqa: BLE001
        return "mixed"


def _as_date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def build_evidence(
    pc: dict,
    *,
    area: str,
    house: int,
    direction: str,
    row: Optional[dict] = None,
    dasha: Optional[dict] = None,
    age_band: str = "",
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
) -> EvidenceBundle:
    """Build evidence from a timing row + dasha snapshot already computed."""
    from interpretation.life_stage import age_at_period, age_band_at

    row = row or {}
    dasha = dasha or {}
    vim = dasha.get("vim") or {}
    md = str(vim.get("md") or row.get("md") or "")
    ad = str(vim.get("ad") or row.get("ad") or "")

    start = period_start or _as_date(row.get("start"))
    end = period_end or _as_date(row.get("end"))
    if not age_band:
        age_band = age_band_at(pc, start or date.today())
    age_n = age_at_period(pc, start)

    bav = int(row.get("bav", 0) or 0)
    promise = str(row.get("promise") or row.get("direction") or "mixed")
    dasha_dir = str(row.get("dasha") or dasha.get("direction") or "mixed")
    planet = str(row.get("planet") or "")
    thouse = int(row.get("house") or house or 0)

    div_code, _ = _varga_for_area(area)
    div_support = _varga_strength(pc, area)

    support: list[str] = []
    pressure: list[str] = []
    if bav >= 5:
        support.append(f"{planet or 'Transit'} well supported")
    elif bav <= 3 and planet:
        pressure.append(f"{planet} with limited support")

    if promise == "up":
        support.append("birth chart supportive on this area")
    elif promise == "down":
        pressure.append("birth chart strained on this area")

    if div_support == "strong":
        support.append(f"{div_code} confirmation")
    elif div_support == "weak":
        pressure.append(f"{div_code} caution")

    if md in ("Saturn",) or ad in ("Saturn",):
        pressure.append("Saturn timing")
    if md in ("Jupiter",) or ad in ("Jupiter",):
        support.append("Jupiter timing")
    if thouse == 10 and area == "career":
        support.append("10th-house activation")
    if thouse == 11 and area == "career":
        support.append("11th-house activation")
    if thouse == 7 and area == "love":
        support.append("7th-house activation")
    if thouse == 12 and area == "inner":
        pressure.append("12th-house activation")

    agreement_raw = dasha.get("agreement")
    agreement_n = 0
    if isinstance(agreement_raw, int):
        agreement_n = agreement_raw
    elif isinstance(agreement_raw, str):
        m = re.search(r"(\d+)", agreement_raw)
        if m:
            agreement_n = int(m.group(1))

    secondary = bool(dasha.get("unanimous") or agreement_n >= 2)

    house_strength = "strong" if bav >= 5 and promise != "down" else (
        "weak" if bav <= 3 or promise == "down" else "mixed"
    )
    confidence = (
        "strong" if secondary and bav >= 5
        else "cautious" if bav <= 3 or promise == "down"
        else "moderate"
    )

    return EvidenceBundle(
        area=area,
        direction=direction,
        age_band=age_band,
        age_at_period=age_n,
        period_start=start,
        period_end=end,
        primary_dasha=md,
        sub_dasha=ad,
        transit_planet=planet,
        transit_house=thouse,
        birth_house=house,
        house_strength=house_strength,
        divisional_chart=div_code,
        divisional_support=div_support,
        secondary_confirmation=secondary,
        support_factors=support,
        pressure_factors=pressure,
        bav=bav,
        promise=promise,
        dasha_direction=dasha_dir,
        confidence=confidence,
    )
