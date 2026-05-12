"""
Generate the Offline LAN Games Helper kiwi icon.

The icon is original and logo-free: a green kiwi slice with LAN nodes.
It uses no copyrighted game, launcher, platform, or store logos.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
KIWI_PNG_PATH = ASSETS_DIR / "kiwi_logo.png"
PNG_PATH = ASSETS_DIR / "offline_lan_helper.png"
ICO_PATH = ASSETS_DIR / "offline_lan_helper.ico"


def draw_kiwi_icon(size: int = 256) -> Image.Image:
    scale = size / 256

    def s(value: int) -> int:
        return round(value * scale)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Rounded app tile.
    draw.rounded_rectangle(
        (s(14), s(14), s(242), s(242)),
        radius=s(44),
        fill=(235, 250, 226, 255),
        outline=(76, 145, 43, 255),
        width=s(5),
    )

    # Kiwi skin and flesh.
    draw.ellipse((s(42), s(40), s(214), s(212)), fill=(92, 124, 42, 255))
    draw.ellipse((s(54), s(52), s(202), s(200)), fill=(106, 190, 54, 255))
    draw.ellipse((s(80), s(78), s(176), s(174)), fill=(205, 244, 118, 255))
    draw.ellipse((s(113), s(111), s(143), s(141)), fill=(244, 255, 209, 255))

    # Kiwi seeds.
    center = (s(128), s(126))
    seed_color = (25, 42, 20, 255)
    for angle_index in range(18):
        angle = (angle_index / 18) * 6.2831853
        radius_x = s(55)
        radius_y = s(49)
        x = int(center[0] + radius_x * math.cos(angle))
        y = int(center[1] + radius_y * math.sin(angle))
        draw.ellipse((x - s(3), y - s(4), x + s(3), y + s(4)), fill=seed_color)

    # LAN nodes and links.
    node_color = (240, 253, 244, 255)
    line_color = (32, 105, 42, 255)
    nodes = [(s(78), s(192)), (s(128), s(210)), (s(178), s(192))]
    for node in nodes:
        draw.line((center[0], center[1], node[0], node[1]), fill=line_color, width=s(4))
    for node in nodes:
        draw.ellipse((node[0] - s(10), node[1] - s(10), node[0] + s(10), node[1] + s(10)), fill=node_color, outline=line_color, width=s(3))

    # Simple leaf.
    draw.ellipse((s(152), s(28), s(208), s(70)), fill=(68, 160, 52, 255), outline=(34, 94, 34, 255), width=s(3))
    draw.line((s(158), s(64), s(195), s(38)), fill=(34, 94, 34, 255), width=s(3))

    return image


def main() -> int:
    ASSETS_DIR.mkdir(exist_ok=True)
    image = draw_kiwi_icon(256)
    image.save(KIWI_PNG_PATH)
    image.save(PNG_PATH)
    image.save(ICO_PATH, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Wrote {KIWI_PNG_PATH}")
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
