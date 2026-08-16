"""Generate the Android launcher icons from the website logo.

The logo is a wide banner on a dark ground with no alpha channel, so it cannot
simply be cropped square. It is letterboxed onto a square of its own background
colour, which is sampled from the logo rather than hard-coded so a redrawn logo
keeps matching its own icon.

    python mobile/android/tools/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
LOGO = ROOT / "site" / "img" / "logo.png"
RES = Path(__file__).resolve().parents[1] / "app" / "src" / "main" / "res"

# Launcher icon edge in px per density bucket, and the 108dp adaptive foreground
# at the same buckets.
LEGACY = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
FOREGROUND = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

# A 108dp adaptive icon is masked down to a 66dp circle, so artwork outside that
# fraction of the canvas is liable to be cut off on some launchers.
SAFE_FRACTION = 66 / 108
LEGACY_FRACTION = 0.86


def fitted(logo: Image.Image, box: int, fraction: float) -> Image.Image:
    """The logo scaled to sit inside ``fraction`` of a ``box``-wide square."""
    limit = box * fraction
    scale = min(limit / logo.width, limit / logo.height)
    size = (max(1, round(logo.width * scale)), max(1, round(logo.height * scale)))
    return logo.resize(size, Image.LANCZOS)


def centred(canvas: Image.Image, art: Image.Image) -> Image.Image:
    canvas.paste(
        art,
        ((canvas.width - art.width) // 2, (canvas.height - art.height) // 2),
        art if art.mode == "RGBA" else None,
    )
    return canvas


def circular(image: Image.Image) -> Image.Image:
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, image.width - 1, image.height - 1), fill=255)
    out = Image.new("RGBA", image.size, (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    return out


def write(image: Image.Image, density: str, name: str) -> None:
    target = RES / f"mipmap-{density}"
    target.mkdir(parents=True, exist_ok=True)
    image.save(target / f"{name}.png", optimize=True)


def main() -> None:
    logo = Image.open(LOGO).convert("RGBA")
    ground = Image.open(LOGO).convert("RGB").getpixel((0, 0))
    hex_ground = "#%02X%02X%02X" % ground

    for density, edge in LEGACY.items():
        square = Image.new("RGBA", (edge, edge), ground + (255,))
        icon = centred(square, fitted(logo, edge, LEGACY_FRACTION))
        write(icon, density, "ic_launcher")
        write(circular(icon), density, "ic_launcher_round")

    for density, edge in FOREGROUND.items():
        clear = Image.new("RGBA", (edge, edge), (0, 0, 0, 0))
        write(centred(clear, fitted(logo, edge, SAFE_FRACTION)), density,
              "ic_launcher_foreground")

    values = RES / "values"
    values.mkdir(parents=True, exist_ok=True)
    (values / "ic_launcher_background.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<resources>\n"
        f'    <color name="ic_launcher_background">{hex_ground}</color>\n'
        "</resources>\n",
        encoding="utf-8",
    )

    adaptive = RES / "mipmap-anydpi-v26"
    adaptive.mkdir(parents=True, exist_ok=True)
    for name in ("ic_launcher", "ic_launcher_round"):
        (adaptive / f"{name}.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '    <background android:drawable="@color/ic_launcher_background" />\n'
            '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
            "</adaptive-icon>\n",
            encoding="utf-8",
        )

    print(f"icons written under {RES} on ground {hex_ground}")


if __name__ == "__main__":
    main()
