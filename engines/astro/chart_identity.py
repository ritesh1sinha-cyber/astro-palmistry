#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chart identity validation — fail closed when precompute meta disagrees with UI inputs."""
from __future__ import annotations

import re
from typing import Any


class ChartIdentityError(ValueError):
    """Precompute chart does not match the client name / slug / DOB supplied by the UI."""


def _norm_dob(dob: str) -> str:
    if not dob:
        return ""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", dob)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})", dob)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return dob.strip()[:10]


def _name_tokens(name: str) -> set[str]:
    if not name:
        return set()
    parts = re.split(r"[\s_\-]+", name.strip().lower())
    tokens = {p for p in parts if len(p) >= 2}
    # Also include alpha-only tokens (e.g. 'ishu1' -> 'ishu')
    alpha_parts = re.split(r"[^a-zA-Z]+", name.strip().lower())
    tokens |= {p for p in alpha_parts if len(p) >= 2}
    return tokens


def names_compatible(expected: str, meta_client: str, slug: str = "") -> bool:
    """True when expected client / slug shares a name token with precompute meta.client."""
    e_clean = (expected or "").strip().lower()
    m_clean = (meta_client or "").strip().lower()
    if not m_clean or not e_clean:
        return True
    if e_clean == m_clean or e_clean.startswith(m_clean) or m_clean.startswith(e_clean):
        return True
    et = _name_tokens(expected) | _name_tokens(slug)
    mt = _name_tokens(meta_client)
    if not mt or not et:
        return True
    return bool(et & mt)


def validate_chart_identity(
    pc: dict[str, Any],
    *,
    client_name: str = "",
    dob: str = "",
    slug: str = "",
) -> dict[str, Any]:
    """
    Validate precompute meta against UI inputs.
    Returns {ok, issues, meta_client, lagna_sign, dob}.
    """
    meta = pc.get("meta") or {}
    issues: list[str] = []

    exp_dob = _norm_dob(dob)
    meta_dob = _norm_dob(str(meta.get("dob", "")))
    if exp_dob and meta_dob and exp_dob != meta_dob:
        issues.append(f"DOB mismatch: UI {exp_dob} vs precompute {meta_dob}")

    meta_client = str(meta.get("client", "")).strip()
    exp_name = (client_name or slug or "").strip()
    if exp_name and meta_client and not names_compatible(exp_name, meta_client, slug):
        issues.append(
            f"Client name mismatch: UI '{exp_name}' / slug '{slug}' "
            f"vs precompute meta.client '{meta_client}'"
        )

    return {
        "ok": not issues,
        "issues": issues,
        "meta_client": meta_client,
        "lagna_sign": meta.get("lagna_sign", ""),
        "dob": meta_dob or exp_dob,
    }


def assert_chart_identity(
    pc: dict[str, Any],
    *,
    client_name: str = "",
    dob: str = "",
    slug: str = "",
) -> dict[str, Any]:
    """Raise ChartIdentityError when validation fails."""
    result = validate_chart_identity(pc, client_name=client_name, dob=dob, slug=slug)
    if not result["ok"]:
        raise ChartIdentityError("; ".join(result["issues"]))
    return result


def sync_display_name(pc: dict[str, Any], client_name: str) -> None:
    """Use UI client name in meta for HTML headers after identity passes."""
    name = (client_name or "").strip()
    if not name:
        return
    meta = pc.setdefault("meta", {})
    meta["client"] = name
