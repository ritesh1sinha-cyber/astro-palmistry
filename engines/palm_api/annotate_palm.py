from PIL import Image, ImageDraw, ImageFont

SRC = "data/uploads/01cec126c3c2.jpg"
OUT = "data/uploads/01cec126c3c2_annotated.jpg"

im = Image.open(SRC).convert("RGB")
W, H = im.size
draw = ImageDraw.Draw(im)


def catmull_rom(points, samples=24):
    """Return a smooth polyline through the given control points."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for t in range(samples):
            s = t / samples
            s2, s3 = s * s, s * s * s
            x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * s +
                       (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2 +
                       (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3)
            y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * s +
                       (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2 +
                       (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3)
            out.append((x, y))
    out.append(points[-1])
    return out


# Control points are given in normalized (0-1) coordinates, then scaled.
lines = {
    "Heart line":  ((1.00, 0.20, 0.20), [
        (0.50, 0.345), (0.585, 0.375), (0.685, 0.405),
        (0.785, 0.430), (0.875, 0.448)]),
    "Head line":   ((0.15, 0.55, 1.00), [
        (0.395, 0.410), (0.500, 0.452), (0.610, 0.498),
        (0.710, 0.535), (0.795, 0.560)]),
    "Life line":   ((0.10, 0.80, 0.25), [
        (0.445, 0.380), (0.395, 0.445), (0.375, 0.535),
        (0.400, 0.635), (0.460, 0.725), (0.520, 0.795)]),
    "Fate line":   ((1.00, 0.75, 0.05), [
        (0.600, 0.790), (0.592, 0.660), (0.598, 0.530),
        (0.606, 0.450), (0.610, 0.400)]),
}

lw = max(6, W // 220)

for name, (color, norm_pts) in lines.items():
    rgb = tuple(int(c * 255) for c in color)
    pts = [(x * W, y * H) for x, y in norm_pts]
    smooth = catmull_rom(pts)
    draw.line(smooth, fill=rgb, width=lw, joint="curve")

# ---- Legend ----
try:
    font = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", W // 28)
except Exception:
    font = ImageFont.load_default()

pad = W // 40
row = W // 22
box_w = int(W * 0.46)
box_h = pad * 2 + row * len(lines)
draw.rectangle([pad, pad, pad + box_w, pad + box_h], fill=(0, 0, 0))
y = pad + pad // 2
sw = row // 2
for name, (color, _) in lines.items():
    rgb = tuple(int(c * 255) for c in color)
    draw.rectangle([pad + pad // 2, y + sw // 3,
                    pad + pad // 2 + sw, y + sw + sw // 3], fill=rgb)
    draw.text((pad + pad // 2 + sw + pad // 3, y), name,
              fill=(255, 255, 255), font=font)
    y += row

im.save(OUT, quality=92)
print("Saved", OUT, im.size)
