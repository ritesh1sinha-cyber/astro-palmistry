#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse KP block from VedicReport extract - cusps, subs, significators, dasha."""
from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Optional

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
AB3 = {
    "SUN": "Sun", "MON": "Moon", "MAR": "Mars", "MER": "Mercury", "JUP": "Jupiter",
    "VEN": "Venus", "SAT": "Saturn", "RAH": "Rahu", "KET": "Ketu",
}
AB2 = {
    "SU": "Sun", "MO": "Moon", "MA": "Mars", "ME": "Mercury", "JU": "Jupiter",
    "VE": "Venus", "SA": "Saturn", "RA": "Rahu", "KE": "Ketu",
}
DASHA_PLANETS = frozenset({"Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"})

HOUSE_TOPICS = {
    1: "body, vitality, and how others read you",
    2: "wealth, speech, and family resources",
    3: "courage, skills, siblings, and short travel",
    4: "home, mother, property, and inner peace",
    5: "children, creativity, romance, and intellect",
    6: "health, service, rivals, and daily work",
    7: "marriage, partnership, and open enemies",
    8: "longevity, inheritance, and hidden change",
    9: "father, dharma, luck, and long journeys",
    10: "career, status, and public reputation",
    11: "income, gains, and fulfilled wishes",
    12: "expenses, foreign lands, and spiritual release",
}


def abbr(tok: str) -> Optional[str]:
    tok = tok.strip().upper()
    return AB3.get(tok) or AB2.get(tok)


def parse_date(raw: str, dob: date) -> Optional[date]:
    m = re.match(r"\s*(\d{1,2})/\s*(\d{1,2})/\s*(\d{2,4})\s*$", raw)
    if not m:
        return None
    d, mo, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if yy < 100:
        yy = (dob.year // 100) * 100 + yy
        if yy < dob.year:
            yy += 100
    try:
        return date(yy, mo, d)
    except ValueError:
        return None


def fmt(d: date | str | None) -> str:
    if isinstance(d, str) and d:
        try:
            d = date.fromisoformat(d[:10])
        except ValueError:
            return d
    if not isinstance(d, date):
        return "-"
    return d.strftime("%d %b %Y").lstrip('0')


class KPChart:
    def __init__(
        self,
        pc: dict,
        text: str,
        dob: date,
        client_name: str = "",
        *,
        block: dict | None = None,
    ):
        self.pc = pc
        self.name = client_name or pc["meta"]["client"]
        self.lagna = (block or {}).get("lagna_sign") or pc["meta"]["lagna_sign"]
        self.dob = dob
        self.full_text = text
        if block:
            self.region = ""
            self.praty_region = ""
            self.ruling = _normalize_ruling(block.get("ruling", {}))
            self.cusps = block.get("cusps", [])
            self.planets = block.get("planets", {})
            self.signif = _normalize_signif(block.get("significators", {}))
            self.planet_signif = block.get("planet_signification", {})
            dasha = block.get("dasha", {})
            self.maha = dasha.get("maha", {})
            self.antars = dasha.get("antars", [])
            self.pratyantars = dasha.get("pratyantars", [])
            return
        i = text.find("KP System")
        if i < 0:
            i = text.find("Cuspal Positions")
        self.region = text[i:i + 12000] if i >= 0 else text
        self.praty_region = text[text.find("Vimshottari Dasha - Pratyantar"):] if "Vimshottari Dasha - Pratyantar" in text else ""
        self.ruling = self._ruling()
        self.cusps = self._cusps()
        self.planets = self._planets()
        self.signif = self._significators()
        self.planet_signif = self._planet_signification()
        self.maha, self.antars = self._dasha(dob)
        self.pratyantars = self._pratyantars(dob)

    @classmethod
    def from_block(cls, pc: dict, block: dict, dob: date, client_name: str = "") -> "KPChart":
        return cls(pc, "", dob, client_name, block=block)

    def _seg(self, a: str, b: str) -> str:
        i = self.region.find(a)
        j = self.region.find(b, i + 1) if i >= 0 else -1
        if i < 0:
            return ""
        return self.region[i:j] if j > 0 else self.region[i:]

    def _ruling(self) -> dict:
        seg = self._seg("Ruling Planet", "Cuspal Positions")
        out = {}
        for ref in ("Lagna", "Moon", "Day Lord"):
            m = re.search(rf"{ref}\s+([A-Z]{{3}})(?:\s+([A-Z]{{3}})\s+([A-Z]{{3}}))?", seg)
            if m:
                out[ref] = [abbr(g) for g in m.groups() if g]
        return out

    def _cusps(self) -> list[dict]:
        seg = self._seg("Cuspal Positions", "Planetary Positions")
        out = []
        for m in re.finditer(
            r"\b(\d{1,2})\s+(\d{3}-\d{2}-\d{2})\s+([A-Z]{3})\s+([A-Z]{3})\s+([A-Z]{3})\s+([A-Z]{3})",
            seg,
        ):
            cusp, deg, rash, nak, sub, ss = m.groups()
            d = int(deg[:3])
            out.append({
                "cusp": int(cusp), "degree": deg, "sign": SIGNS[(d // 30) % 12],
                "rasi_lord": abbr(rash), "nak": abbr(nak), "sub": abbr(sub), "ss": abbr(ss),
            })
        seen, uniq = set(), []
        for c in sorted(out, key=lambda x: x["cusp"]):
            if 1 <= c["cusp"] <= 12 and c["cusp"] not in seen:
                seen.add(c["cusp"])
                uniq.append(c)
        return uniq

    def _planets(self) -> dict:
        seg = self._seg("Planetary Positions", "Significators of Houses")
        out = {}
        for m in re.finditer(
            r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)(?:\[R\])?\s+"
            r"(\d{3}-\d{2}-\d{2})\s+([A-Z]{3})\s+([A-Z]{3})\s+([A-Z]{3})\s+([A-Z]{3})",
            seg,
        ):
            nm, deg, rash, nak, sub, ss = m.groups()
            d = int(deg[:3])
            out[nm] = {
                "degree": deg, "sign": SIGNS[(d // 30) % 12], "rasi_lord": abbr(rash),
                "nak": abbr(nak), "sub": abbr(sub), "ss": abbr(ss),
            }
        return out

    def _significators(self) -> dict:
        seg = self._seg("Significators of Houses", "Planet Signification")
        out = {}
        for line in seg.splitlines():
            m = re.search(r"(?:^|\s)(\d{1,2})\s+((?:[A-Z]{2}\s+)*[A-Z]{2})\s*$", line)
            if m:
                h = int(m.group(1))
                pls = [abbr(t) for t in m.group(2).split() if abbr(t)]
                if 1 <= h <= 12 and pls:
                    out[h] = pls
        return out

    def _planet_signification(self) -> dict:
        seg = self._seg("Planet Signification", "Vimshottari Dasha - Pratyantar")
        if not seg:
            seg = self.region[self.region.find("Planet Signification"):]
        out = {}
        for line in seg.splitlines():
            m = re.search(
                r"\b(Sun|Moon|Mars|Mercury|Jupiter|Venus|Saturn|Rahu|Ketu)\s+((?:\d{1,2}\s*)+)\s*$",
                line,
            )
            if m:
                houses = [int(x) for x in m.group(2).split()]
                if all(1 <= h <= 12 for h in houses):
                    out[m.group(1)] = houses
        return out

    def _dasha(self, dob: date) -> tuple[dict, list[dict]]:
        region = self.region
        i = region.find("Planetary Positions")
        if i >= 0:
            region = region[i:]
        e = region.find("Vimshottari Dasha - Pratyantar")
        if e > 0:
            region = region[:e]
        lines = region.splitlines()
        mahas = []
        for li, line in enumerate(lines):
            for hm in re.finditer(r"\b([A-Z]{3})\s+-(\d+)\s+Years", line):
                lord = abbr(hm.group(1))
                off = hm.start()
                rng = None
                for k in (li, li + 1, li + 2):
                    if k < len(lines):
                        for rm in re.finditer(
                            r"(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})\s*-\s*(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})",
                            lines[k],
                        ):
                            if abs(rm.start() - off) < 22:
                                rng = (parse_date(rm.group(1), dob), parse_date(rm.group(2), dob))
                                break
                    if rng:
                        break
                if lord and rng and rng[0] and rng[1]:
                    mahas.append({
                        "lord": lord, "years": int(hm.group(2)),
                        "start": rng[0], "end": rng[1], "line": li, "off": off,
                    })
        today = date.today()
        cur = next((m for m in mahas if m["start"] <= today < m["end"]), None)
        if not cur and mahas:
            cur = min(mahas, key=lambda m: abs((m["start"] - today).days))
        antars = []
        if cur:
            raw: list[tuple[str, date]] = []
            for li in range(cur["line"], min(cur["line"] + 30, len(lines))):
                for am in re.finditer(r"\b([A-Z]{3})\s+(\d{1,2}/\s*\d{1,2}/\s*\d{2,4})", lines[li]):
                    lord = abbr(am.group(1))
                    d = parse_date(am.group(2), dob)
                    if lord in DASHA_PLANETS and d and cur["start"] < d <= cur["end"]:
                        raw.append((lord, d))
            raw.sort(key=lambda x: x[1])
            seen: set[str] = set()
            for lord, d in raw:
                if lord not in seen:
                    seen.add(lord)
                    antars.append({"lord": lord, "end": d})
        return (cur or {}), antars

    def _pratyantars(self, dob: date) -> list[dict]:
        """Parse pratyantar column for current maha+antar from pratyantar grid."""
        if not self.maha or not self.praty_region:
            return []
        cur_antar = self.current_antar()
        if not cur_antar:
            return []
        m_abbr = {v: k for k, v in AB3.items()}[self.maha["lord"]]
        a_abbr = {v: k for k, v in AB3.items()}[cur_antar["lord"]]
        block_pat = rf"{m_abbr}\s*--\s*{a_abbr}"
        col_idx = None
        data_start = 0
        lines = self.praty_region.splitlines()
        for li, line in enumerate(lines):
            if re.search(block_pat, line) and line.count("--") >= 2:
                parts = re.split(r"\s{2,}", line.strip())
                for i, p in enumerate(parts):
                    if re.search(rf"^{block_pat}$", p.strip()):
                        col_idx = i
                        data_start = li + 2
                        break
            if col_idx is not None:
                break
        if col_idx is None:
            return []
        raw: list[tuple[str, date]] = []
        for line in lines[data_start:data_start + 12]:
            cells = re.split(r"\s{2,}", line.strip())
            pi = col_idx * 2
            if len(cells) <= pi + 1:
                continue
            lord = abbr(cells[pi].strip())
            d = parse_date(cells[pi + 1].strip(), dob)
            if lord and d:
                raw.append((lord, d))
        raw.sort(key=lambda x: x[1])
        out = []
        start = cur_antar["start"]
        for lord, end in raw:
            if end <= start:
                continue
            if end > cur_antar["end"]:
                break
            out.append({"lord": lord, "start": start, "end": end})
            start = end
        return out

    def cusp(self, h: int) -> dict:
        return next((c for c in self.cusps if c["cusp"] == h), {})

    def csl(self, h: int) -> str:
        return self.cusp(h).get("sub", "") or ""

    def links(self, planet: str) -> set[int]:
        return set(self.planet_signif.get(planet, []))

    def _coerce_date(self, val) -> date | None:
        if isinstance(val, date):
            return val
        if isinstance(val, str) and val:
            try:
                return date.fromisoformat(val[:10])
            except ValueError:
                return parse_date(val, self.dob)
        return None

    def current_antar(self) -> dict:
        today = date.today()
        for a in self.antars:
            start = self._coerce_date(a.get("start")) or self._coerce_date(self.maha.get("start"))
            end = self._coerce_date(a.get("end"))
            if start and end and start <= today < end:
                return {"lord": a["lord"], "start": start, "end": end}
        if self.antars:
            prev_end = self._coerce_date(self.maha.get("start"))
            for a in self.antars:
                end = self._coerce_date(a.get("end"))
                if prev_end and end and prev_end <= today < end:
                    return {"lord": a["lord"], "start": prev_end, "end": end}
                prev_end = end
        return {}

    def current_pratyantar(self) -> dict:
        today = date.today()
        for p in self.pratyantars:
            start = self._coerce_date(p.get("start"))
            end = self._coerce_date(p.get("end"))
            if start and end and start <= today < end:
                return {"lord": p["lord"], "start": start, "end": end}
        return {}

    def antar_windows(self) -> list[dict]:
        if not self.maha or not self.antars:
            return []
        windows = []
        start = self._coerce_date(self.maha.get("start"))
        for a in self.antars:
            end = self._coerce_date(a.get("end"))
            a_start = self._coerce_date(a.get("start")) or start
            windows.append({"lord": a["lord"], "start": a_start, "end": end})
            start = end
        return windows


def _normalize_ruling(raw: dict) -> dict:
    out = {}
    for ref, vals in raw.items():
        if isinstance(vals, list):
            out[ref] = [abbr(v) or v for v in vals if v]
    return out


def _normalize_signif(raw: dict) -> dict:
    out: dict[int, list] = {}
    for k, vals in raw.items():
        try:
            h = int(k)
        except (TypeError, ValueError):
            continue
        if 1 <= h <= 12 and vals:
            out[h] = [abbr(v) or v for v in vals]
    return out


def _parse_dob(dob: str) -> date:
    if "-" in dob:
        return date.fromisoformat(dob)
    from datetime import datetime
    return datetime.strptime(dob, "%Y-%m-%d").date()


def load_kp_chart(
    extracted_path: str = "",
    client_name: str = "",
    dob: str = "",
    pc: dict | None = None,
) -> KPChart:
    """Load KP chart from precomputed kp block or legacy extract text."""
    d = _parse_dob(dob)
    if pc and pc.get("kp"):
        return KPChart.from_block(pc, pc["kp"], d, client_name)
    from astro_precompute import precompute
    if pc is None:
        if not extracted_path:
            raise ValueError("load_kp_chart needs precomputed kp block or extracted_path")
        pc = precompute(extracted_path, client_name, dob)
    if pc.get("kp"):
        return KPChart.from_block(pc, pc["kp"], d, client_name)
    if not extracted_path:
        raise ValueError("No kp block in precompute and no extract path given")
    text = Path(extracted_path).read_text(encoding="utf-8", errors="ignore")
    return KPChart(pc, text, d, client_name)
