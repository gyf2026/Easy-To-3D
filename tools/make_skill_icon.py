"""Draw the skill's market icon, so the artwork is rebuildable like everything else.

The upload form wants a square PNG under 500 KB. This draws one with the standard
library only: an L-bracket in section, a marked point on its surface and a dimension
line, which is what the skill actually does. Shapes are rasterised at four times the
target size and box-filtered down, so the edges are clean without a graphics
dependency.

Usage:
    python3 tools/make_skill_icon.py [--output dist/structural-design-icon.png]
"""
import argparse
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZE = 512
SUPERSAMPLE = 4

BACKGROUND = (0x16, 0x22, 0x2E, 255)
PANEL = (0x1B, 0x2C, 0x3C, 255)
SOLID = (0xE9, 0xEF, 0xF6, 255)
SHADE = (0xC3, 0xD2, 0xE2, 255)
ACCENT = (0x56, 0xC7, 0xF2, 255)
MARK = (0xF5, 0xA6, 0x23, 255)


def new_canvas(width, height):
    return bytearray(bytes(BACKGROUND) * (width * height))


def blend(canvas, width, height, x, y, color):
    """Source-over one pixel. Everything here is opaque, so alpha is a soft edge only."""
    if not (0 <= x < width and 0 <= y < height):
        return
    index = (y * width + x) * 4
    canvas[index:index + 4] = bytes(color)


def fill_polygon(canvas, width, height, points, color):
    ys = [point[1] for point in points]
    top, bottom = int(min(ys)), int(max(ys)) + 1
    for y in range(max(0, top), min(height, bottom)):
        middle = y + 0.5
        crossings = []
        for index in range(len(points)):
            x0, y0 = points[index]
            x1, y1 = points[(index + 1) % len(points)]
            if (y0 <= middle < y1) or (y1 <= middle < y0):
                crossings.append(x0 + (middle - y0) / (y1 - y0) * (x1 - x0))
        crossings.sort()
        for pair in range(0, len(crossings) - 1, 2):
            left = max(0, int(round(crossings[pair])))
            right = min(width, int(round(crossings[pair + 1])))
            for x in range(left, right):
                blend(canvas, width, height, x, y, color)


def fill_circle(canvas, width, height, cx, cy, radius, color):
    radius = float(radius)
    for y in range(int(cy - radius) - 1, int(cy + radius) + 2):
        for x in range(int(cx - radius) - 1, int(cx + radius) + 2):
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius * radius:
                blend(canvas, width, height, x, y, color)


def fill_ring(canvas, width, height, cx, cy, outer, inner, color, underneath):
    """A target mark: filled disc, then the surface colour punched back through it."""
    fill_circle(canvas, width, height, cx, cy, outer, color)
    fill_circle(canvas, width, height, cx, cy, inner, underneath)


def fill_round_rect(canvas, width, height, x0, y0, x1, y1, radius, color):
    radius = float(radius)
    for y in range(int(y0), int(y1)):
        for x in range(int(x0), int(x1)):
            cx = min(max(x + 0.5, x0 + radius), x1 - radius)
            cy = min(max(y + 0.5, y0 + radius), y1 - radius)
            if (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius * radius:
                blend(canvas, width, height, x, y, color)


def stroke(canvas, width, height, p0, p1, thickness, color, cap=True):
    x0, y0 = p0
    x1, y1 = p1
    length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
    if length == 0:
        fill_circle(canvas, width, height, x0, y0, thickness / 2, color)
        return
    nx, ny = -(y1 - y0) / length * thickness / 2, (x1 - x0) / length * thickness / 2
    fill_polygon(canvas, width, height,
                 [(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)], color)
    if cap:
        radius = thickness / 2
        fill_circle(canvas, width, height, x0, y0, radius, color)
        fill_circle(canvas, width, height, x1, y1, radius, color)


def draw(size):
    """All coordinates are authored against a 512 grid and scaled up."""
    scale = size / 512.0

    def place(points):
        return [(x * scale, y * scale) for x, y in points]

    canvas = new_canvas(size, size)
    fill_round_rect(canvas, size, size, 0, 0, size, size, 104 * scale, PANEL)

    # Bracket in section: upright on the left, base plate along the bottom.
    outline = [(126, 330), (126, 122), (222, 122), (222, 250), (386, 250), (386, 330)]
    fill_polygon(canvas, size, size, place(outline), SOLID)
    # A darker face on the inside of the upright reads as thickness, not a flat icon.
    fill_polygon(canvas, size, size,
                 place([(222, 122), (222, 250), (386, 250), (386, 232), (240, 232), (240, 122)]), SHADE)

    fill_circle(canvas, size, size, 322 * scale, 290 * scale, 20 * scale, PANEL)

    # Dimension line under the base plate.
    stroke(canvas, size, size, (126 * scale, 380 * scale), (386 * scale, 380 * scale), 5 * scale, ACCENT)
    for x in (126, 386):
        stroke(canvas, size, size, (x * scale, 362 * scale), (x * scale, 398 * scale), 5 * scale, ACCENT)

    # Marked point on the upright: the review annotation users actually place.
    fill_ring(canvas, size, size, 174 * scale, 180 * scale, 25 * scale, 16 * scale, MARK, SOLID)
    return canvas


def downsample(canvas, size, factor):
    rows = []
    block = factor * factor
    for y in range(0, size, factor):
        row = bytearray()
        for x in range(0, size, factor):
            totals = [0, 0, 0, 0]
            for dy in range(factor):
                base = ((y + dy) * size + x) * 4
                for dx in range(factor):
                    offset = base + dx * 4
                    for channel in range(4):
                        totals[channel] += canvas[offset + channel]
            row.extend(total // block for total in totals)
        rows.append(bytes(row))
    return rows


def write_png(path, width, height, rows):
    def chunk(tag, payload):
        return (struct.pack('>I', len(payload)) + tag + payload
                + struct.pack('>I', zlib.crc32(tag + payload) & 0xFFFFFFFF))

    raw = b''.join(b'\x00' + row for row in rows)
    header = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header)
                     + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', default=str(ROOT / 'dist' / 'structural-design-icon.png'))
    parser.add_argument('--size', type=int, default=SIZE)
    args = parser.parse_args()
    large = args.size * SUPERSAMPLE
    canvas = draw(large)
    rows = downsample(canvas, large, SUPERSAMPLE)
    output = Path(args.output)
    write_png(output, args.size, args.size, rows)
    limit = 500 * 1024
    size = output.stat().st_size
    verdict = 'ok' if size <= limit else 'OVER the 500 KB limit'
    print(f'{output} {args.size}x{args.size} {size / 1024:.1f} KB ({verdict})')
    return 0 if size <= limit else 1


if __name__ == '__main__':
    raise SystemExit(main())
