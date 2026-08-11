"""Palm report QA linter."""

from __future__ import annotations

import re
from typing import Any


def validate_palm_result(reading_result: dict[str, Any], html: str = "") -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    text = html or ""

    measurements = reading_result.get("measurements") or {}
    for hand, meas in measurements.items():
        ivr = (meas.get("finger_ratios") or {}).get("index_vs_ring")
        if ivr == "index_longer" and re.search(
            r"ring.*longer than.*index|apollo.*longer than.*index",
            text, re.I,
        ):
            failures.append(f"{hand}: finger ratio contradiction (index_longer)")
        if ivr == "ring_longer" and re.search(
            r"index.*longer than.*ring|jupiter.*longer than.*ring",
            text, re.I,
        ):
            failures.append(f"{hand}: finger ratio contradiction (ring_longer)")

    if re.search(r"\byou are a risk[- ]taker\b", text, re.I):
        warnings.append("absolute personality claim: risk-taker")

    if re.search(r"\ba a\b|\ban an\b", text, re.I):
        failures.append("grammar defect in palm HTML")

    for conf in reading_result.get("confluences") or []:
        if not conf.get("evidence"):
            warnings.append(f"missing evidence for {conf.get('id')}")

    return {"ok": not failures, "failures": failures, "warnings": warnings}
