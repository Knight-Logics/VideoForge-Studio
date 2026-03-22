from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FRAME_COLORS = [
    (255, 255, 255),
    (255, 255, 0),
    (50, 255, 0),
    (255, 70, 70),
    (0, 255, 200),
]


def _find_font(size: int):
    candidates = [
        "C:/Windows/Fonts/GILLUBCD.TTF",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for candidate in candidates:
        font_path = Path(candidate)
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def _word_color(index: int) -> tuple[int, int, int]:
    if index < 2:
        return FRAME_COLORS[index]
    return FRAME_COLORS[2 + ((index - 2) % (len(FRAME_COLORS) - 2))]


def generate_caption_frames(
    word_timings: list[tuple[str, float, float]],
    output_dir: Path,
    width: int,
    height: int,
    fps: int,
    duration: float,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    font = _find_font(120)
    total_frames = max(1, int(duration * fps))

    for frame_index in range(total_frames):
        current_time = frame_index / fps
        current_word = None
        word_index = 0
        for index, (word, start_time, end_time) in enumerate(word_timings):
            if start_time <= current_time < end_time:
                current_word = word
                word_index = index
                break

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if current_word:
            draw = ImageDraw.Draw(image)
            fill = _word_color(word_index)
            bbox = draw.textbbox((0, 0), current_word, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2
            y = (height // 2) - (text_height // 2)

            stroke = 8
            for dx in range(-stroke, stroke + 1):
                for dy in range(-stroke, stroke + 1):
                    if dx == 0 and dy == 0:
                        continue
                    draw.text((x + dx, y + dy), current_word, font=font, fill=(0, 0, 0, 255))

            draw.text((x, y), current_word, font=font, fill=fill)

        image.save(output_dir / f"frame_{frame_index:04d}.png")
