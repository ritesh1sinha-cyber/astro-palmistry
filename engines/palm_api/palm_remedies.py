"""Palm remedies — only actions backed by corpus / coded mark rules.

Sources (no freehand tips):
  * `rules_corpus.json` / palmistry_how_to_master pp.130–136, 149 —
    gems for under-developed mounts, chinmudra, iron for high Mars
  * `special_marks.MARK_READING` actionable tails (grille, island, cross, triangle)
  * `life_aspects` rule for star on Moon (travel care)

Anything auspicious with no practice attached (trident, fish, plain star) is
a *reading*, not a remedy — it already appears in the marks section.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PalmRemedy:
    bucket: str  # "do" | "dont"
    action: str
    reason: str
    source: str


# Under-developed mount → gem (palmistry_how_to_master p.133).
# Saturn omitted on purpose: corpus says a depressed Saturn with a long middle
# finger is usually treated as *developed*, so we do not invent an emerald.
_FLAT_GEM: dict[str, tuple[str, str]] = {
    "jupiter": ("topaz", "Try wearing a topaz in a ring on your active hand."),
    "mercury": ("emerald", "Try wearing an emerald in a ring on your active hand."),
    "mars": ("coral", "Try wearing coral in a ring on your active hand."),
    "venus": ("coral", "Try wearing coral in a ring on your active hand."),
    "apollo": ("ruby", "Try wearing a ruby in a ring on your active hand."),
    "sun": ("ruby", "Try wearing a ruby in a ring on your active hand."),
    "moon": ("pearl", "Try wearing a pearl in a ring on your active hand."),
    "luna": ("pearl", "Try wearing a pearl in a ring on your active hand."),
}

_HOT_GEMS = frozenset({"topaz", "ruby", "coral"})
_COLD_GEMS = frozenset({"emerald", "pearl"})

# Mark types whose MARK_READING tail is a real practice (not praise).
_MARK_ACTION_TYPES = frozenset({"cross", "grille", "island", "triangle"})

_MAX_GEMS = 2  # palmistry_how_to_master p.133–135

_MOUNT_LIFE = {
    "jupiter": "career and ambition",
    "saturn": "duty and long work",
    "apollo": "public recognition and creative work",
    "sun": "public recognition and creative work",
    "mercury": "talks, deals, and business",
    "mars": "courage and temper",
    "venus": "love, comfort, and vitality",
    "moon": "mood, travel, and imagination",
    "luna": "mood, travel, and imagination",
}


def _mount_level(mounts: dict, key: str) -> str:
    return str(mounts.get(key) or "").lower()


def _life(zone: str) -> str:
    z = (zone or "").lower()
    if z in _MOUNT_LIFE:
        return _MOUNT_LIFE[z]
    try:
        from palm_api.special_marks import MOUNT_DOMAIN
        return MOUNT_DOMAIN.get(z, "this part of life")
    except Exception:  # noqa: BLE001
        return "this part of life"


def _headline_quality(feats: dict) -> str:
    line = (feats.get("lines") or {}).get("head") or {}
    return str(line.get("quality") or line.get("depth") or "").lower()


def _head_looks_weak(feats: dict) -> bool:
    q = _headline_quality(feats)
    return q in ("broken", "islanded", "weak", "thin", "chained", "poor", "faint")


def build_palm_remedies(feats: dict[str, Any]) -> list[PalmRemedy]:
    """Return rule-backed do/don't items for one hand's features."""
    from palm_api.special_marks import MARK_READING, ZONE_OVERRIDE

    feats = feats or {}
    mounts = feats.get("mounts") or {}
    marks = feats.get("special_marks") or []
    out: list[PalmRemedy] = []
    seen: set[str] = set()

    def add(bucket: str, action: str, reason: str, source: str) -> None:
        key = " ".join((bucket, action)).lower()
        if not action or key in seen:
            return
        seen.add(key)
        out.append(PalmRemedy(bucket=bucket, action=action, reason=reason, source=source))

    # --- gems for flat / under-developed mounts (corpus) -------------------
    gem_picks: list[tuple[str, str, str, str]] = []
    for mount, (gem, action) in _FLAT_GEM.items():
        if _mount_level(mounts, mount) != "flat":
            continue
        # Avoid double-picking moon/luna
        if mount == "luna" and any(m == "moon" for m, *_ in gem_picks):
            continue
        if mount == "sun" and any(m == "apollo" for m, *_ in gem_picks):
            continue
        life = _life(mount)
        reason = (
            f"Your {life} pad ({mount.title()} mount) reads under-developed on the palm."
        )
        gem_picks.append((mount, gem, action, reason))

    gem_picks = gem_picks[:_MAX_GEMS]
    n_gems = len(gem_picks)
    for mount, gem, action, reason in gem_picks:
        place = ""
        if n_gems == 1:
            place = " Wear it on the ring finger of your active hand."
        elif gem in _HOT_GEMS:
            place = (" With two stones indicated, wear this hot stone on the "
                     "middle finger of the active hand.")
        elif gem in _COLD_GEMS:
            place = (" With two stones indicated, wear this cool stone on the "
                     "ring finger of the active hand.")
        add("do", action + place, reason, "palmistry_how_to_master p.133–135")

    # --- iron for high Aggressive Mars (corpus case) ----------------------
    if _mount_level(mounts, "mars") == "prominent":
        add(
            "do",
            "Wear a plain iron ring to help cool a hot temper.",
            "A full Mars pad on the palm is classically linked with high vitality and anger.",
            "palmistry_how_to_master p.149",
        )
        add(
            "dont",
            "Don’t start fights — cool down before you speak.",
            "Same high-Mars reading: the metal is to settle temper, not to win arguments.",
            "palmistry_how_to_master p.149",
        )

    # --- chinmudra when Jupiter mount is off-balance or head line weak ----
    jup = _mount_level(mounts, "jupiter")
    if jup in ("flat", "prominent") or _head_looks_weak(feats):
        add(
            "do",
            "Practise Chinmudra daily: gently join the tips of your thumb and index finger.",
            "Classical palm upaya when the Jupiter mount is too flat or too full, "
            "or the head line is weak.",
            "palmistry_how_to_master p.130",
        )

    # --- mark practices from coded MARK_READING tails only ----------------
    for mark in marks:
        kind = str(mark.get("type") or mark.get("kind") or "").lower()
        zone = str(mark.get("zone") or mark.get("mount") or "palm").lower()
        if kind not in _MARK_ACTION_TYPES:
            continue
        # Cross on Jupiter is a fortunate exception — not a burden remedy.
        if kind == "cross" and ZONE_OVERRIDE.get((kind, zone)):
            continue
        _name, _clause, tail = MARK_READING.get(kind, ("", "", ""))
        tail = (tail or "").strip()
        if not tail:
            continue
        action = tail.lstrip(". ").rstrip(".")
        if action and not action[:1].isupper():
            action = action[:1].upper() + action[1:]
        add(
            "do",
            f"{action} (about {_life(zone)}).",
            f"Coded mark rule for a {kind} near the {zone} mount.",
            "special_marks.MARK_READING",
        )

    # --- star on Moon: only life_aspects-backed travel caution ------------
    for mark in marks:
        kind = str(mark.get("type") or "").lower()
        zone = str(mark.get("zone") or "").lower()
        if kind == "star" and zone in ("moon", "luna"):
            add(
                "dont",
                "Take extra care on long trips and around water — don’t travel impulsively.",
                "A star on the Moon mount is classically read as travel risk "
                "plus strong intuition.",
                "life_aspects / succinct_palmistry (star on Moon)",
            )

    return out


def format_remedy_line(r: PalmRemedy) -> str:
    """One readable line: action first, then short reason + source."""
    return f"{r.action} Why: {r.reason} [{r.source}]"
