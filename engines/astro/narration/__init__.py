"""Narration layer — human prose from PredictionMeaning."""

from narration.area_labels import area_label, area_name
from narration.human_renderer import (
    render_current_scene,
    render_headline,
    render_manifest_bullets,
)

__all__ = [
    "area_label",
    "area_name",
    "render_current_scene",
    "render_headline",
    "render_manifest_bullets",
]
