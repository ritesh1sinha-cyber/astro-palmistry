"""Hard stop: no palm in the photo, no reading.

`extract_features` is deliberately forgiving: when no hand is found it falls
back to a skin mask on the whole picture and carries on, and the quality score
for that picture can still land on "fair". Everything downstream (rule
matching, confluence, the LLM prose layer) then wrote a full reading about a
hand nobody photographed. A full-body photo is enough to trigger it.

This gate runs on the raw measurements, before any rule or sentence is built.
A photo must show (1) a hand, (2) large enough in the frame to trace creases
on, and (3) at least two of the three major lines actually seen in the image
(ridge coverage, not a template guess). Otherwise the reading is refused with
a retake instruction, and nothing is saved or sold.
"""
from __future__ import annotations

from typing import Any


class PalmNotReadable(ValueError):
    """The photo cannot support a palm reading. The message is written for the
    customer and says how to retake it."""


# Hand bounding box as a share of the whole photo. Phone palm shots sit well
# above this; a person photographed head to toe sits far below it.
MIN_HAND_FRAME_FRACTION = 0.05
# A crease counts as seen only when this much of its path is backed by real
# ridge evidence in the image (same threshold the photo guidance already uses
# to call a line "faint").
MIN_LINE_COVERAGE = 0.30
MAJOR_LINES = ("life", "head", "heart")
MIN_MAJOR_LINES_SEEN = 2

_INFRA_STATUS = ("mediapipe_not_installed", "hand_model_error")


def _retake(which: str) -> str:
    return (f"Please retake your {which} palm photo: palm facing the camera, "
            "fingers spread, the whole hand filling most of the frame, in "
            "bright even light.")


def palm_problem(feats: dict[str, Any], hand: str = "") -> str | None:
    """None when the photo can support a reading, else a customer message."""
    which = f"{hand} " if hand in ("left", "right") else ""
    status = str(feats.get("landmark_status") or "")
    detail = str(feats.get("landmark_detail") or status)

    if status != "ok":
        if detail.startswith(_INFRA_STATUS):
            # Our fault, not the customer's; surfaced as an infrastructure
            # error so we neither blame the photo nor invent a reading.
            raise RuntimeError(f"hand_landmarker unavailable: {detail}")
        return ("We could not find a hand in your " + which + "photo. "
                + _retake(which.strip() or "right"))

    frac = feats.get("hand_frame_fraction")
    if frac is not None and float(frac) < MIN_HAND_FRAME_FRACTION:
        return ("The hand in your " + which + "photo is too small in the frame "
                "to read. " + _retake(which.strip() or "right"))

    lines = feats.get("lines") or {}
    seen = [
        k for k in MAJOR_LINES
        if (lines.get(k) or {}).get("detected")
        and float((lines.get(k) or {}).get("ridge_coverage") or 0.0) >= MIN_LINE_COVERAGE
    ]
    if len(seen) < MIN_MAJOR_LINES_SEEN:
        return ("The main lines of your " + which + "palm could not be seen "
                "clearly enough to read. " + _retake(which.strip() or "right"))
    return None


def require_readable_palm(feats: dict[str, Any], hand: str = "") -> None:
    msg = palm_problem(feats, hand)
    if msg:
        raise PalmNotReadable(msg)
