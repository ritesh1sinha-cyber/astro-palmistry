"""North Indian (diamond) D1 chart as inline SVG for report HTML/PDF."""
from __future__ import annotations

import html as _html
from typing import Any, Optional


SIGNS = (
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
    "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
)

# House polygons in unit square [0,1]² — house 1 = top diamond (lagna).
# Classical North Indian: lagna at top, houses rise anti-clockwise
# (1 → top-left → left → bottom-left → bottom → … → top-right → 1).
_NI_HOUSES: dict[int, list[tuple[float, float]]] = {
    1:  [(0.50, 0.00), (0.75, 0.25), (0.50, 0.50), (0.25, 0.25)],
    2:  [(0.00, 0.00), (0.50, 0.00), (0.25, 0.25)],
    3:  [(0.00, 0.00), (0.00, 0.50), (0.25, 0.25)],
    4:  [(0.00, 0.50), (0.25, 0.25), (0.50, 0.50), (0.25, 0.75)],
    5:  [(0.00, 0.50), (0.00, 1.00), (0.25, 0.75)],
    6:  [(0.00, 1.00), (0.50, 1.00), (0.25, 0.75)],
    7:  [(0.50, 0.50), (0.75, 0.75), (0.50, 1.00), (0.25, 0.75)],
    8:  [(0.50, 1.00), (1.00, 1.00), (0.75, 0.75)],
    9:  [(1.00, 0.50), (1.00, 1.00), (0.75, 0.75)],
    10: [(1.00, 0.50), (0.75, 0.75), (0.50, 0.50), (0.75, 0.25)],
    11: [(1.00, 0.00), (1.00, 0.50), (0.75, 0.25)],
    12: [(0.50, 0.00), (1.00, 0.00), (0.75, 0.25)],
}

# Reading-friendly label anchors (slightly inset from geometric centroids
# of the thin corner triangles so glyphs are not clipped).
_LABEL_ANCHOR: dict[int, tuple[float, float]] = {
    1: (0.50, 0.28),
    2: (0.22, 0.10),
    3: (0.10, 0.28),
    4: (0.28, 0.50),
    5: (0.10, 0.72),
    6: (0.22, 0.90),
    7: (0.50, 0.72),
    8: (0.78, 0.90),
    9: (0.90, 0.72),
    10: (0.72, 0.50),
    11: (0.90, 0.28),
    12: (0.78, 0.10),
}

_ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke",
}

_ORDER = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn",
          "Rahu", "Ketu")


def _e(t: Any) -> str:
    return _html.escape(str(t or ""))


def _lagna_sign(pc: dict) -> str:
    return str(
        ((pc.get("lagna") or {}).get("sign"))
        or ((pc.get("meta") or {}).get("lagna_sign"))
        or ""
    ).strip()


def _house_from_sign(sign: str, lagna: str) -> Optional[int]:
    if not sign or not lagna or sign not in SIGNS or lagna not in SIGNS:
        return None
    return (SIGNS.index(sign) - SIGNS.index(lagna)) % 12 + 1


def _planet_house(info: dict, lagna: str) -> Optional[int]:
    try:
        h = int(info.get("house") or 0)
        if 1 <= h <= 12:
            return h
    except (TypeError, ValueError):
        pass
    sign = str(info.get("sign") or info.get("rashi") or "").strip()
    return _house_from_sign(sign, lagna)


def _planets_by_house(pc: dict) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {h: [] for h in range(1, 13)}
    lagna = _lagna_sign(pc)
    planets = pc.get("planets") or {}
    for name in _ORDER:
        info = planets.get(name) or {}
        if not isinstance(info, dict):
            continue
        h = _planet_house(info, lagna)
        if not h:
            continue
        abbr = _ABBR.get(name, name[:2])
        if info.get("retrograde") or info.get("retro"):
            abbr += "\u02b3"  # modifier letter r — not "Jur"
        out[h].append(abbr)
    for name, info in planets.items():
        if name in _ORDER or not isinstance(info, dict):
            continue
        h = _planet_house(info, lagna)
        if h:
            out[h].append(_ABBR.get(name, (name or "?")[:2]))
    return out


def _chunk_planets(bodies: list[str], *, per_line: int = 3) -> list[str]:
    if not bodies:
        return []
    return [" ".join(bodies[i:i + per_line])
            for i in range(0, len(bodies), per_line)]


def svg_d1(pc: dict, *, size: int = 340) -> str:
    """Return a self-contained North Indian D1 SVG (house no. + planet abbr)."""
    by_h = _planets_by_house(pc)
    lagna = _lagna_sign(pc)
    margin = 10
    inner = size - 2 * margin

    def xy(u: float, v: float) -> tuple[float, float]:
        return margin + u * inner, margin + v * inner

    # Structural skeleton — outer square + both diagonals + mid diamond edges
    # so empty houses still read as a North Indian chart.
    skeleton = [
        f'<rect class="ni-frame" x="{margin}" y="{margin}" '
        f'width="{inner}" height="{inner}"/>',
        f'<line class="ni-grid" x1="{xy(0,0)[0]:.1f}" y1="{xy(0,0)[1]:.1f}" '
        f'x2="{xy(1,1)[0]:.1f}" y2="{xy(1,1)[1]:.1f}"/>',
        f'<line class="ni-grid" x1="{xy(1,0)[0]:.1f}" y1="{xy(1,0)[1]:.1f}" '
        f'x2="{xy(0,1)[0]:.1f}" y2="{xy(0,1)[1]:.1f}"/>',
        f'<polygon class="ni-grid" fill="none" points="'
        f'{xy(0.5,0)[0]:.1f},{xy(0.5,0)[1]:.1f} '
        f'{xy(1,0.5)[0]:.1f},{xy(1,0.5)[1]:.1f} '
        f'{xy(0.5,1)[0]:.1f},{xy(0.5,1)[1]:.1f} '
        f'{xy(0,0.5)[0]:.1f},{xy(0,0.5)[1]:.1f}"/>',
    ]

    polys = []
    labels = []
    for h, unit_poly in _NI_HOUSES.items():
        pts = " ".join(f"{xy(u, v)[0]:.1f},{xy(u, v)[1]:.1f}" for u, v in unit_poly)
        polys.append(
            f'<polygon class="ni-house" data-house="{h}" points="{pts}"/>'
        )
        ax, ay = _LABEL_ANCHOR.get(h, (0.5, 0.5))
        px, py = xy(ax, ay)
        bodies = by_h.get(h) or []
        lines = _chunk_planets(bodies)
        # House number above planet lines
        num_y = py - (7 if lines else 0)
        labels.append(
            f'<text class="ni-num" x="{px:.1f}" y="{num_y:.1f}" '
            f'text-anchor="middle" dominant-baseline="middle">{h}</text>'
        )
        for i, line in enumerate(lines):
            labels.append(
                f'<text class="ni-pl" x="{px:.1f}" y="{py + 4 + i * 11:.1f}" '
                f'text-anchor="middle" dominant-baseline="middle">'
                f'{_e(line)}</text>'
            )

    title = "Birth chart (D1) · North Indian"
    if lagna:
        title = f"{title} · {_e(lagna)} rising"

    placed = sum(1 for h in range(1, 13) if by_h.get(h))
    note = ""
    if placed == 0:
        note = ('<p class="fine ni-warn">Planet houses were not available on this '
                'chart file — regenerate the reading after precompute.</p>')

    return f"""
<figure class="ni-chart">
  <figcaption class="ev-label">{title}</figcaption>
  <div class="ni-chart-box">
  <svg class="ni-svg" viewBox="0 0 {size} {size}" width="100%" height="100%"
       preserveAspectRatio="xMidYMid meet" role="img"
       aria-label="North Indian birth chart with house numbers and planets">
    {''.join(skeleton)}
    {''.join(polys)}
    {''.join(labels)}
  </svg>
  </div>
  <p class="fine ni-legend">Su Sun · Mo Moon · Ma Mars · Me Mercury · Ju Jupiter ·
  Ve Venus · Sa Saturn · Ra Rahu · Ke Ketu · ʳ = retrograde</p>
  {note}
</figure>"""
