"""Generate local palm fixtures when Wikimedia/CDN downloads are blocked."""
from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

OUT = Path(__file__).resolve().parent


def make_palm(path: Path, seed: int = 1, mirror: bool = False) -> None:
    rnd = random.Random(seed)
    W, H = 900, 1200
    img = Image.new("RGB", (W, H), (236, 214, 190))
    d = ImageDraw.Draw(img)
    for y in range(H):
        shade = int(20 * (abs(y - H / 2) / (H / 2)))
        d.line([(0, y), (W, y)], fill=(236 - shade, 214 - shade, 190 - shade))

    cx, cy = W // 2, int(H * 0.58)
    palm = [
        (cx - 210, cy - 40), (cx - 230, cy + 80), (cx - 180, cy + 260),
        (cx - 40, cy + 310), (cx + 80, cy + 300), (cx + 200, cy + 240),
        (cx + 240, cy + 60), (cx + 210, cy - 50),
    ]
    d.polygon(palm, fill=(214, 168, 132))

    fingers = [
        (cx - 170, cy - 360, 70, 320),
        (cx - 70, cy - 420, 72, 380),
        (cx + 30, cy - 400, 68, 360),
        (cx + 125, cy - 320, 60, 280),
        (cx - 260, cy - 80, 90, 220),
    ]
    for x, y, w, h in fingers:
        d.ellipse([x, y, x + w, y + h], fill=(210, 160, 125))
        d.arc([x + 8, y + h * 0.35, x + w - 8, y + h * 0.55],
              200, 340, fill=(170, 120, 90), width=3)

    life = [(cx - 160, cy - 20), (cx - 190, cy + 40),
            (cx - 200, cy + 140), (cx - 160, cy + 240)]
    head = [(cx - 150, cy + 10), (cx - 40, cy + 40),
            (cx + 80, cy + 55), (cx + 170, cy + 40)]
    heart = [(cx - 140, cy - 50), (cx - 20, cy - 70),
             (cx + 90, cy - 65), (cx + 180, cy - 40)]
    fate = [(cx + 10, cy + 260), (cx + 5, cy + 160),
            (cx + 15, cy + 60), (cx + 25, cy - 40)]
    for pts, w in ((life, 5), (head, 4), (heart, 4), (fate, 3)):
        d.line(pts, fill=(120, 70, 50), width=w, joint="curve")
    for _ in range(18):
        x0 = cx + rnd.randint(-160, 160)
        y0 = cy + rnd.randint(-80, 220)
        d.line([(x0, y0), (x0 + rnd.randint(-40, 40), y0 + rnd.randint(-20, 20))],
               fill=(150, 100, 75), width=1)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.8))
    img = ImageEnhance.Contrast(img).enhance(1.08)
    if mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    img.save(path, "JPEG", quality=90)
    print(path.name, path.stat().st_size)


if __name__ == "__main__":
    make_palm(OUT / "palm_left.jpg", seed=11, mirror=False)
    make_palm(OUT / "palm_right.jpg", seed=22, mirror=True)
    for name in ("palm_a.jpg", "palm_b.jpg", "unsplash_hand.jpg", "picsum.jpg"):
        p = OUT / name
        if p.exists() and p.stat().st_size < 10000:
            p.unlink(missing_ok=True)
    (OUT / "README.txt").write_text(
        "Palm fixtures for local e2e.\n"
        "Network blocked Wikimedia/CDN downloads (corporate gateway HTML stubs).\n"
        "Generated synthetic open-palm JPEGs via make_palms.py for pipeline testing.\n"
        "Sample chart (from project e2e scripts):\n"
        "  Sample — 1990-01-15 12:00 New Delhi (28.6139, 77.2090, tz 5.5)\n"
        "  Partner — 1992-06-20 08:30 New Delhi (matching)\n",
        encoding="utf-8",
    )
    print("done")
