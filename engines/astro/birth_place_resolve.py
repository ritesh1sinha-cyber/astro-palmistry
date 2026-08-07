#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve birth place name to coordinates + timezone via PyJHora world cities DB."""
from __future__ import annotations

import csv
import re
from typing import Any

from natal_from_pyjhora import DEFAULT_PYJHORA_SRC, _ensure_pyjhora

_CITIES: list[tuple[str, str, float, float, str, float]] | None = None


def normalize_birth_time(raw: str) -> str:
    """Accept HH:MM or HH:MM:SS and return HH:MM:SS."""
    raw = (raw or "").strip().replace(".", ":")
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", raw)
    if not m:
        raise ValueError(
            f"Invalid birth time {raw!r} - use HH:MM or HH:MM:SS (24-hour)."
        )
    h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
    if not (0 <= h <= 23 and 0 <= mi <= 59 and 0 <= s <= 59):
        raise ValueError(f"Birth time out of range: {raw!r}")
    return f"{h:02d}:{mi:02d}:{s:02d}"


def normalize_dob(raw: str) -> str:
    """Return YYYY-MM-DD."""
    raw = (raw or "").strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if not m:
        raise ValueError(f"Invalid DOB {raw!r} - use YYYY-MM-DD.")
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return f"{y:04d}-{mo:02d}-{d:02d}"


def normalize_place_query(raw: str) -> str:
    """Collapse whitespace around commas: 'New Delhi,India' -> 'New Delhi, India'."""
    parts = [p.strip() for p in (raw or "").split(",") if p.strip()]
    return ", ".join(parts)


def _csv_path(pyjhora_src=None) -> str:
    # Pass None through, NOT the default: _ensure_pyjhora resolves
    # PYJHORA_SRC -> DEFAULT itself, and handing it the default explicitly
    # bypassed the env var. That made every place lookup raise
    # "PyJHora source not found" anywhere the package is not at the default
    # path -- which includes our own Docker image, where PYJHORA_SRC points at
    # site-packages. Place resolution was broken in production, not just locally.
    _ensure_pyjhora(pyjhora_src)
    from jhora import const
    return const._world_city_csv_file


def _load_cities(pyjhora_src=None) -> list[tuple[str, str, float, float, str, float]]:
    global _CITIES
    if _CITIES is not None:
        return _CITIES
    path = _csv_path(pyjhora_src)
    rows: list[tuple[str, str, float, float, str, float]] = []
    with open(path, encoding="ISO-8859-1", errors="replace") as fh:
        for row in csv.reader(fh):
            if len(row) < 6:
                continue
            try:
                lat = float(row[2])
                lon = float(row[3])
                tz = float(row[5])
            except (TypeError, ValueError):
                continue
            label = str(row[1]).strip()
            if not label:
                continue
            rows.append((str(row[0]).strip(), label, lat, lon, str(row[4]).strip(), tz))
    _CITIES = rows
    return rows


def _place_score(query: str, country: str, label: str, tz_name: str) -> int:
    q = query.lower().strip()
    if not q:
        return 0
    label_l = label.lower()
    country_l = country.lower()
    variants = {q, normalize_place_query(q).lower()}
    score = 0
    for v in variants:
        if label_l == v:
            score = max(score, 120)
        elif label_l.startswith(v):
            score = max(score, 95)
        elif f", {v}" in label_l or label_l.startswith(v + ","):
            score = max(score, 90)
        elif v in label_l:
            score = max(score, 70)
        if country_l and v in country_l:
            score = max(score, 40)
        parts = [p.strip() for p in v.split(",") if p.strip()]
        if parts and parts[0] in label_l:
            score = max(score, 75 if len(parts) == 1 else 85)
    # Prefer well-formed CSV rows over scraped junk (empty IANA tz name).
    if tz_name and "/" in tz_name:
        score += 12
    if ", " in label:
        score += 6
    else:
        score -= 28
    if not tz_name or "/" not in tz_name:
        score -= 22
    return max(score, 0)


def search_places(
    query: str,
    *,
    limit: int = 12,
    pyjhora_src=None,
) -> list[dict[str, Any]]:
    """Substring search in world_cities_with_tz.csv (no Google)."""
    query = (query or "").strip()
    if len(query) < 2:
        return []
    cities = _load_cities(pyjhora_src)
    scored: list[tuple[int, str, str, float, float, float]] = []
    for country, label, lat, lon, tz_name, tz in cities:
        s = _place_score(query, country, label, tz_name)
        if s >= 40:
            scored.append((s, country, label, lat, lon, tz))
    scored.sort(key=lambda x: (-x[0], x[2].lower()))
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for s, country, label, lat, lon, tz in scored:
        key = f"{label}|{lat}|{lon}"
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "label": label,
            "country": country,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "timezone": tz,
            "score": s,
        })
        if len(out) >= limit:
            break
    return out


def nearest_places(
    latitude: float,
    longitude: float,
    *,
    limit: int = 5,
    pyjhora_src=None,
) -> list[dict[str, Any]]:
    """Return closest cities from the world-cities DB (for geolocation pick)."""
    cities = _load_cities(pyjhora_src)
    ranked: list[tuple[float, str, str, float, float, float]] = []
    for country, label, lat, lon, _tz_name, tz in cities:
        dlat = lat - latitude
        dlon = lon - longitude
        dist = dlat * dlat + dlon * dlon
        ranked.append((dist, country, label, lat, lon, tz))
    ranked.sort(key=lambda x: x[0])
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for _dist, country, label, lat, lon, tz in ranked:
        key = f"{label}|{lat}|{lon}"
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "label": label,
            "country": country,
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "timezone": tz,
        })
        if len(out) >= limit:
            break
    return out


def _lookup_csv_exact(place_name: str, *, pyjhora_src=None) -> dict[str, Any] | None:
    key = normalize_place_query(place_name).lower()
    for country, label, lat, lon, _tz_name, tz in _load_cities(pyjhora_src):
        if label.lower() == key:
            return {
                "place": label,
                "latitude": lat,
                "longitude": lon,
                "timezone": tz,
            }
    return None


def resolve_birth_place(
    place_name: str,
    *,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: float | None = None,
    pyjhora_src=None,
) -> dict[str, Any]:
    """Geocode place label to {place, latitude, longitude, timezone}."""
    place_name = normalize_place_query(place_name)
    if not place_name:
        raise ValueError("Place of birth is required.")

    if latitude is not None and longitude is not None and timezone is not None:
        return {
            "place": place_name,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "timezone": float(timezone),
        }

    exact = _lookup_csv_exact(place_name, pyjhora_src=pyjhora_src)
    if exact:
        return exact

    matches = search_places(place_name, limit=8, pyjhora_src=pyjhora_src)
    if matches:
        top = matches[0]
        q = place_name.lower()
        if top["score"] >= 90 or top["label"].lower() == q:
            return {
                "place": top["label"],
                "latitude": top["latitude"],
                "longitude": top["longitude"],
                "timezone": top["timezone"],
            }
        if len(matches) == 1 and top["score"] >= 75:
            return {
                "place": top["label"],
                "latitude": top["latitude"],
                "longitude": top["longitude"],
                "timezone": top["timezone"],
            }

    # Pass None through, NOT the default: _ensure_pyjhora resolves
    # PYJHORA_SRC -> DEFAULT itself, and handing it the default explicitly
    # bypassed the env var. That made every place lookup raise
    # "PyJHora source not found" anywhere the package is not at the default
    # path -- which includes our own Docker image, where PYJHORA_SRC points at
    # site-packages. Place resolution was broken in production, not just locally.
    _ensure_pyjhora(pyjhora_src)
    from jhora import utils

    utils.use_database_for_world_cities(True)
    for candidate in {place_name, normalize_place_query(place_name)}:
        result = utils.get_location(candidate)
        if result and len(result) >= 4:
            name, lat, lon, tz = (
                result[0], float(result[1]), float(result[2]), float(result[3])
            )
            # Reject scraped rows with empty tz name when CSV has a better match.
            if matches and matches[0]["score"] >= 70:
                best = matches[0]
                if abs(lat - best["latitude"]) > 1.0 or abs(lon - best["longitude"]) > 1.0:
                    return {
                        "place": best["label"],
                        "latitude": best["latitude"],
                        "longitude": best["longitude"],
                        "timezone": best["timezone"],
                    }
            return {
                "place": str(name),
                "latitude": lat,
                "longitude": lon,
                "timezone": tz,
            }

    if matches:
        top = matches[0]
        return {
            "place": top["label"],
            "latitude": top["latitude"],
            "longitude": top["longitude"],
            "timezone": top["timezone"],
        }

    raise ValueError(
        f"Could not resolve {place_name!r}. "
        "Pick a city from the dropdown (e.g. New Delhi, India)."
    )
