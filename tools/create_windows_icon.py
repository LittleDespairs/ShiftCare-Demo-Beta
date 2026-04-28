from __future__ import annotations

import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ICON_PATH = ROOT / "static" / "icons" / "app-icon.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)
SCALE = 4


def blend_pixel(dst: tuple[int, int, int, int], src: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    sr, sg, sb, sa = src
    dr, dg, db, da = dst
    alpha = sa / 255
    inv_alpha = 1 - alpha
    out_alpha = int(sa + da * inv_alpha)
    if out_alpha == 0:
        return 0, 0, 0, 0
    return (
        int((sr * alpha + dr * da / 255 * inv_alpha) * 255 / out_alpha),
        int((sg * alpha + dg * da / 255 * inv_alpha) * 255 / out_alpha),
        int((sb * alpha + db * da / 255 * inv_alpha) * 255 / out_alpha),
        out_alpha,
    )


def point_in_rounded_rect(x: float, y: float, left: float, top: float, right: float, bottom: float, radius: float) -> bool:
    if not (left <= x < right and top <= y < bottom):
        return False

    corner_x = left + radius if x < left + radius else right - radius if x >= right - radius else x
    corner_y = top + radius if y < top + radius else bottom - radius if y >= bottom - radius else y
    return (x - corner_x) ** 2 + (y - corner_y) ** 2 <= radius**2


def draw_rounded_rect(
    pixels: list[list[tuple[int, int, int, int]]],
    left: float,
    top: float,
    right: float,
    bottom: float,
    radius: float,
    color: tuple[int, int, int, int],
) -> None:
    height = len(pixels)
    width = len(pixels[0])
    min_x = max(0, int(left))
    max_x = min(width, int(right) + 1)
    min_y = max(0, int(top))
    max_y = min(height, int(bottom) + 1)

    for y in range(min_y, max_y):
        for x in range(min_x, max_x):
            if point_in_rounded_rect(x + 0.5, y + 0.5, left, top, right, bottom, radius):
                pixels[y][x] = blend_pixel(pixels[y][x], color)


def draw_block_letter(
    pixels: list[list[tuple[int, int, int, int]]],
    pattern: tuple[str, ...],
    left: float,
    top: float,
    cell: float,
    color: tuple[int, int, int, int],
) -> None:
    for row_index, row in enumerate(pattern):
        for col_index, cell_value in enumerate(row):
            if cell_value == "#":
                draw_rounded_rect(
                    pixels,
                    left + col_index * cell,
                    top + row_index * cell,
                    left + (col_index + 0.82) * cell,
                    top + (row_index + 0.82) * cell,
                    cell * 0.16,
                    color,
                )


def render_icon(size: int) -> list[list[tuple[int, int, int, int]]]:
    canvas_size = size * SCALE
    unit = canvas_size / 512
    pixels = [[(0, 0, 0, 0) for _ in range(canvas_size)] for _ in range(canvas_size)]

    def sx(value: float) -> float:
        return value * unit

    blue = (37, 99, 235, 255)
    green = (22, 163, 74, 255)
    orange = (234, 88, 12, 255)
    slate = (30, 41, 59, 255)
    gray = (148, 163, 184, 255)
    light_blue = (219, 234, 254, 255)
    white = (255, 255, 255, 255)

    draw_rounded_rect(pixels, sx(0), sx(0), sx(512), sx(512), sx(112), blue)
    draw_rounded_rect(pixels, sx(88), sx(112), sx(424), sx(400), sx(38), white)
    draw_rounded_rect(pixels, sx(88), sx(112), sx(424), sx(186), sx(38), light_blue)

    for x, y, color in (
        (128, 222, blue),
        (224, 222, green),
        (320, 222, orange),
        (128, 306, gray),
        (224, 306, blue),
        (320, 306, green),
    ):
        draw_rounded_rect(pixels, sx(x), sx(y), sx(x + 64), sx(y + 54), sx(12), color)

    draw_rounded_rect(pixels, sx(140), sx(74), sx(174), sx(150), sx(17), slate)
    draw_rounded_rect(pixels, sx(338), sx(74), sx(372), sx(150), sx(17), slate)
    draw_block_letter(
        pixels,
        (
            "####",
            "#...",
            "#...",
            "####",
            "...#",
            "...#",
            "####",
        ),
        sx(150),
        sx(122),
        sx(11),
        blue,
    )
    draw_block_letter(
        pixels,
        (
            "####",
            "#...",
            "#...",
            "#...",
            "#...",
            "#...",
            "####",
        ),
        sx(276),
        sx(122),
        sx(11),
        blue,
    )

    if SCALE == 1:
        return pixels

    downsampled = []
    for y in range(size):
        row = []
        for x in range(size):
            block = [
                pixels[y * SCALE + block_y][x * SCALE + block_x]
                for block_y in range(SCALE)
                for block_x in range(SCALE)
            ]
            row.append(tuple(sum(pixel[channel] for pixel in block) // len(block) for channel in range(4)))
        downsampled.append(row)
    return downsampled


def make_dib(pixels: list[list[tuple[int, int, int, int]]]) -> bytes:
    height = len(pixels)
    width = len(pixels[0])
    pixel_data = bytearray()

    for row in reversed(pixels):
        for red, green, blue, alpha in row:
            pixel_data.extend((blue, green, red, alpha))

    mask_stride = ((width + 31) // 32) * 4
    and_mask = bytes(mask_stride * height)
    header = struct.pack(
        "<IIIHHIIIIII",
        40,
        width,
        height * 2,
        1,
        32,
        0,
        len(pixel_data),
        0,
        0,
        0,
        0,
    )
    return header + bytes(pixel_data) + and_mask


def write_ico(path: Path) -> None:
    images = [(size, make_dib(render_icon(size))) for size in SIZES]
    header_size = 6 + 16 * len(images)
    offset = header_size
    directory = bytearray()
    payload = bytearray()

    for size, data in images:
        directory.extend(
            struct.pack(
                "<BBBBHHII",
                0 if size == 256 else size,
                0 if size == 256 else size,
                0,
                0,
                1,
                32,
                len(data),
                offset,
            )
        )
        payload.extend(data)
        offset += len(data)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(struct.pack("<HHH", 0, 1, len(images)) + bytes(directory) + bytes(payload))


if __name__ == "__main__":
    write_ico(ICON_PATH)
    print(ICON_PATH)
