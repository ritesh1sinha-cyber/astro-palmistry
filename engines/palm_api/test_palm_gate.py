"""No palm, no reading: the gate must refuse anything that is not a readable palm."""
import pytest

from palm_api.palm_gate import PalmNotReadable, palm_problem, require_readable_palm


def _line(cov, detected=True):
    return {"detected": detected, "ridge_coverage": cov}


def _good():
    return {
        "landmark_status": "ok",
        "landmark_detail": "ok",
        "hand_frame_fraction": 0.4,
        "lines": {"life": _line(0.6), "head": _line(0.55), "heart": _line(0.5), "fate": _line(0.1, False)},
    }


def test_clear_palm_is_readable():
    assert palm_problem(_good(), "right") is None
    require_readable_palm(_good(), "right")


def test_no_hand_found_is_refused():
    f = _good()
    f.update(landmark_status="fallback_skin_mask", landmark_detail="no_hand_detected",
             hand_frame_fraction=None, lines={})
    with pytest.raises(PalmNotReadable, match="could not find a hand"):
        require_readable_palm(f, "left")


def test_tiny_hand_in_frame_is_refused():
    f = _good()
    f["hand_frame_fraction"] = 0.01
    with pytest.raises(PalmNotReadable, match="too small"):
        require_readable_palm(f, "right")


def test_lines_only_guessed_from_template_is_refused():
    f = _good()
    f["lines"] = {"life": _line(0.1), "head": _line(0.12), "heart": _line(0.9)}
    with pytest.raises(PalmNotReadable, match="main lines"):
        require_readable_palm(f, "right")


def test_two_of_three_major_lines_is_enough():
    f = _good()
    f["lines"]["heart"] = _line(0.05)
    assert palm_problem(f) is None


def test_missing_model_is_our_error_not_the_customers():
    f = {"landmark_status": "fallback_skin_mask", "landmark_detail": "mediapipe_not_installed"}
    with pytest.raises(RuntimeError, match="hand_landmarker unavailable"):
        palm_problem(f)
