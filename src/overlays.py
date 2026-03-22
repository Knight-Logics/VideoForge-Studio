from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FONT_CANDIDATES = {
    "gill-sans-ultra-bold": ["C:/Windows/Fonts/GILLUBCD.TTF", "C:/Windows/Fonts/arialbd.ttf"],
    "arial-bold": ["C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ARIAL.TTF"],
    "impact": ["C:/Windows/Fonts/impact.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "bahnschrift-semi": ["C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "segoe-ui-bold": ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
}


def _font(size: int, family: str):
    candidates = FONT_CANDIDATES.get(family, FONT_CANDIDATES["gill-sans-ultra-bold"])
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_stroke_text(draw: ImageDraw.ImageDraw, position: tuple[int, int], text: str, font, fill: tuple[int, int, int], stroke_width: int) -> None:
    x, y = position
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0))
    draw.text(position, text, font=font, fill=fill)


def generate_numbers_overlay(
    output_path: Path,
    width: int,
    height: int,
    title_1: str,
    title_2: str,
    clip_labels: list[str],
    reveal_count: int,
    title_font_family: str,
    title_font_size: int,
    list_font_family: str,
    list_font_size: int,
) -> None:
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    title_font = _font(title_font_size, title_font_family)
    item_font = _font(list_font_size, list_font_family)

    title_texts = [title_1.strip(), title_2.strip()]
    y = int(height * 0.05)
    for line in title_texts:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        x = int((width - line_w) // 2)
        _draw_stroke_text(draw, (x, y), line, title_font, (255, 255, 255), 5)
        y += 110

    top = int(height * 0.33)
    spacing = int((height * 0.45) / max(1, len(clip_labels) - 1))

    for index, label in enumerate(clip_labels):
        rank = len(clip_labels) - index
        y_pos = top + index * spacing
        rank_color = [(255, 60, 60), (255, 150, 0), (70, 120, 255), (180, 60, 220), (70, 190, 70)][index % 5]

        _draw_stroke_text(draw, (72, y_pos), f"{rank}.", item_font, rank_color, 4)

        if index < reveal_count:
            _draw_stroke_text(draw, (180, y_pos), label, item_font, (255, 255, 255), 4)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def generate_title_animation_frames(
    output_dir: Path,
    width: int,
    height: int,
    title_1: str,
    title_2: str,
    title_font_family: str,
    title_font_size: int,
    frame_count: int = 120,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    title_font = _font(title_font_size, title_font_family)

    # Build the title layer once.
    title_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    title_draw = ImageDraw.Draw(title_layer)

    title_lines = [title_1.strip(), title_2.strip()]
    y = int(height * 0.05)
    for line in title_lines:
        bbox = title_draw.textbbox((0, 0), line, font=title_font)
        line_w = bbox[2] - bbox[0]
        x = int((width - line_w) // 2)
        _draw_stroke_text(title_draw, (x, y), line, title_font, (255, 255, 255), 5)
        y += 110

    alpha = title_layer.split()[3]
    scan_height = int(height * 0.2)
    top = int(height * 0.04)
    bottom = top + scan_height

    for frame_index in range(frame_count):
        progress = frame_index / max(1, frame_count - 1)
        frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        if progress < 0.3:
            reveal_width = int(width * (progress / 0.3))
            reveal_mask = Image.new("L", (width, height), 0)
            reveal_draw = ImageDraw.Draw(reveal_mask)
            reveal_draw.rectangle((0, top, reveal_width, bottom), fill=255)
            revealed = Image.composite(title_layer, Image.new("RGBA", (width, height), (0, 0, 0, 0)), reveal_mask)
            frame.paste(revealed, (0, 0), revealed)
        else:
            frame.paste(title_layer, (0, 0), title_layer)
            slash_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            slash_draw = ImageDraw.Draw(slash_layer)
            slash_progress = (progress - 0.3) / 0.7
            slash_x = int((-scan_height) + slash_progress * (width + scan_height * 2))
            points = [
                (slash_x + scan_height, top),
                (slash_x, bottom),
                (slash_x + 36, bottom),
                (slash_x + 36 + scan_height, top),
            ]
            slash_draw.polygon(points, fill=(255, 255, 255, 255))

            masked_slash = Image.composite(
                slash_layer,
                Image.new("RGBA", (width, height), (0, 0, 0, 0)),
                alpha,
            )
            frame.paste(masked_slash, (0, 0), masked_slash)

        frame.save(output_dir / f"frame_{frame_index:04d}.png")
