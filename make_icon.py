"""
Generate the Offline LAN Games Helper icon.

The icon is intentionally generic: monitor, network nodes, and a small
gamepad shape. It uses no copyrighted game, launcher, or platform logos.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
PNG_PATH = ASSETS_DIR / "offline_lan_helper.png"
ICO_PATH = ASSETS_DIR / "offline_lan_helper.ico"


def rounded_rectangle(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, fill: tuple[int, int, int, int], outline=None, width: int = 1) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def draw_icon(size: int = 256) -> Image.Image:
    scale = size / 256

    def s(value: int) -> int:
        return round(value * scale)

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Background tile.
    rounded_rectangle(
        draw,
        (s(14), s(14), s(242), s(242)),
        s(38),
        (22, 78, 99, 255),
        outline=(92, 225, 230, 255),
        width=s(4),
    )

    # Subtle inner panel.
    rounded_rectangle(
        draw,
        (s(32), s(38), s(224), s(214)),
        s(24),
        (14, 116, 144, 255),
        outline=(165, 243, 252, 160),
        width=s(2),
    )

    # Monitor.
    rounded_rectangle(
        draw,
        (s(62), s(70), s(194), s(145)),
        s(12),
        (8, 47, 73, 255),
        outline=(226, 252, 255, 255),
        width=s(5),
    )
    draw.rectangle((s(113), s(146), s(143), s(165)), fill=(226, 252, 255, 255))
    rounded_rectangle(draw, (s(91), s(164), s(165), s(175)), s(5), (226, 252, 255, 255))

    # LAN nodes and links.
    node_color = (187, 247, 208, 255)
    line_color = (190, 242, 100, 255)
    center = (s(128), s(112))
    nodes = [(s(65), s(193)), (s(128), s(199)), (s(191), s(193))]
    for node in nodes:
        draw.line((center[0], center[1], node[0], node[1]), fill=line_color, width=s(5))
    for node in nodes:
        draw.ellipse((node[0] - s(13), node[1] - s(13), node[0] + s(13), node[1] + s(13)), fill=node_color, outline=(20, 83, 45, 255), width=s(3))

    # Small gamepad shape, generic and logo-free.
    rounded_rectangle(draw, (s(78), s(96), s(178), s(134)), s(18), (15, 23, 42, 255), outline=(125, 211, 252, 255), width=s(3))
    draw.rectangle((s(99), s(109), s(121), s(114)), fill=(226, 252, 255, 255))
    draw.rectangle((s(107), s(101), s(113), s(122)), fill=(226, 252, 255, 255))
    draw.ellipse((s(143), s(104), s(154), s(115)), fill=(226, 252, 255, 255))
    draw.ellipse((s(158), s(114), s(169), s(125)), fill=(226, 252, 255, 255))

    return image


def main() -> int:
    ASSETS_DIR.mkdir(exist_ok=True)
    image = draw_icon(256)
    image.save(PNG_PATH)
    image.save(ICO_PATH, sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Wrote {PNG_PATH}")
    print(f"Wrote {ICO_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
