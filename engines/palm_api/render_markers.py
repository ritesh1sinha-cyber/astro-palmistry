#!/usr/bin/env python3
"""Render labelme palm-line markings onto the source image."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

LINE_COLORS = {
    "heart_line": (220, 40, 40),
    "head_line": (40, 170, 60),
    "fate_line": (40, 90, 220),
    "life_line": (220, 180, 30),
}

LINE_NAMES = {
    "heart_line": "Heart line",
    "head_line": "Head line",
    "fate_line": "Fate line",
    "life_line": "Life line",
}


def _pick_shapes(shapes: list[dict]) -> dict[str, list[tuple[float, float]]]:
    grouped: dict[str, list[dict]] = {}
    for shape in shapes:
        label = shape.get("label", "")
        if label not in LINE_COLORS:
            continue
        grouped.setdefault(label, []).append(shape)

    picked: dict[str, list[tuple[float, float]]] = {}
    for label, items in grouped.items():
        if label == "life_line":
            items.sort(
                key=lambda s: (
                    s.get("shape_type") != "linestrip",
                    -len(s.get("points") or []),
                )
            )
        else:
            items.sort(key=lambda s: -len(s.get("points") or []))
        pts = items[0].get("points") or []
        picked[label] = [(float(x), float(y)) for x, y in pts]
    return picked


def render_from_labelme(
    json_path: Path,
    image_path: Path | None = None,
    out_path: Path | None = None,
) -> Path:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    root = json_path.parent

    if image_path is None:
        rel = data.get("imagePath", "")
        image_path = (json_path.parent / rel).resolve()
        if not image_path.is_file():
            image_path = (root.parent / Path(rel).name).resolve()

    if out_path is None:
        stem = image_path.stem
        out_path = image_path.parent / f"{stem}_annotated.jpg"

    im = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(im)
    w, h = im.size
    lw = max(5, w // 250)
    dot_r = max(8, w // 180)

    lines = _pick_shapes(data.get("shapes", []))
    order = ["heart_line", "head_line", "life_line", "fate_line"]

    for key in order:
        pts = lines.get(key)
        if not pts or len(pts) < 2:
            continue
        color = LINE_COLORS[key]
        draw.line(pts, fill=color, width=lw, joint="curve")
        for x, y in pts:
            draw.ellipse(
                [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
                fill=color,
                outline=(255, 255, 255),
                width=max(2, dot_r // 4),
            )

    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", w // 28
        )
    except OSError:
        font = ImageFont.load_default()

    pad = w // 40
    row = w // 22
    box_w = int(w * 0.46)
    box_h = pad * 2 + row * len(order)
    draw.rectangle([pad, pad, pad + box_w, pad + box_h], fill=(0, 0, 0))
    y = pad + pad // 2
    sw = row // 2
    for key in order:
        if key not in lines:
            continue
        color = LINE_COLORS[key]
        draw.rectangle(
            [pad + pad // 2, y + sw // 3, pad + pad // 2 + sw, y + sw + sw // 3],
            fill=color,
        )
        draw.text(
            (pad + pad // 2 + sw + pad // 3, y),
            LINE_NAMES[key],
            fill=(255, 255, 255),
            font=font,
        )
        y += row

    im.save(out_path, quality=92)
    return out_path


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    json_path = Path(
        argv[0] if argv else "data/markers/01cec126c3c2_correct.json"
    )
    image_path = Path(argv[1]) if len(argv) > 1 else None
    out_path = Path(argv[2]) if len(argv) > 2 else None
    saved = render_from_labelme(json_path, image_path, out_path)
    print("Saved", saved)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
