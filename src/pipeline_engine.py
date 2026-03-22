from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from .captions import generate_caption_frames
from .ffmpeg_tools import (
    concatenate_segments,
    create_intermission,
    mix_audio_tracks,
    mix_background_music,
    normalize_clip,
    overlay_caption_frames,
    overlay_frame_sequence,
    overlay_image,
)
from .models import RenderSettings
from .narration import generate_speech_hq_with_timestamps, sanitize_tts_text
from .overlays import generate_numbers_overlay, generate_title_animation_frames
from .utils import get_media_duration_seconds

ProgressCallback = Callable[[str, int], None]


def _caption_from_text(text: str) -> str:
    return " ".join(text.replace("_", " ").strip().split())


def run_render_pipeline(
    settings: RenderSettings,
    job_dir: Path,
    output_dir: Path,
    progress_callback: Optional[ProgressCallback] = None,
) -> Path:
    def emit(message: str, percent: int) -> None:
        if progress_callback:
            progress_callback(message, percent)

    emit("Preparing workspace", 2)
    temp_dir = job_dir / "temp"
    overlays_dir = job_dir / "overlays"
    title_frames_root = overlays_dir / "animated_titles"
    temp_dir.mkdir(parents=True, exist_ok=True)
    overlays_dir.mkdir(parents=True, exist_ok=True)

    clip_labels = [_caption_from_text(c.caption) for c in settings.clips]

    emit("Generating visual overlays", 8)
    for index in range(1, len(settings.clips) + 1):
        generate_numbers_overlay(
            output_path=overlays_dir / f"overlay_{index}.png",
            width=settings.output_width,
            height=settings.output_height,
            title_1=settings.title_line_1,
            title_2=settings.title_line_2,
            clip_labels=clip_labels,
            reveal_count=index,
            title_font_family=settings.title_font_family,
            title_font_size=settings.title_font_size,
            list_font_family=settings.list_font_family,
            list_font_size=settings.list_font_size,
        )
        generate_title_animation_frames(
            output_dir=title_frames_root / f"clip_{index}_frames",
            width=settings.output_width,
            height=settings.output_height,
            title_1=settings.title_line_1,
            title_2=settings.title_line_2,
            title_font_family=settings.title_font_family,
            title_font_size=settings.title_font_size,
            frame_count=120,
        )

    final_segments: list[Path] = []

    for index, clip_input in enumerate(settings.clips, start=1):
        emit(f"Normalizing clip {index}/{len(settings.clips)}", min(20 + (index * 8), 55))
        normalized_clip = temp_dir / f"clip_{index}_normalized.mp4"
        normalize_clip(
            clip_input.file_path,
            normalized_clip,
            settings.output_width,
            settings.output_height,
            settings.fps,
        )

        current_segment = normalized_clip

        is_first_clip = index == 1
        if settings.enable_narration and is_first_clip:
            emit("Generating clip 1 narration and captions", 58)
            narration_path = temp_dir / "clip_1_narration.mp3"
            narration_data = generate_speech_hq_with_timestamps(
                text=sanitize_tts_text(clip_input.caption),
                output_path=narration_path,
                voice_id=settings.elevenlabs_voice_id,
                audio_model_id=settings.audio_model_id,
                timestamp_model_id=settings.timestamp_model_id,
                voice_settings=settings.voice_settings,
                api_key=settings.elevenlabs_api_key,
            )

            mixed_path = temp_dir / "clip_1_mixed.mp4"
            mix_audio_tracks(current_segment, narration_path, mixed_path)
            current_segment = mixed_path

            caption_dir = temp_dir / "clip_1_caption_frames"
            clip_duration = get_media_duration_seconds(current_segment)
            generate_caption_frames(
                narration_data["word_timings"],
                caption_dir,
                settings.output_width,
                settings.output_height,
                settings.fps,
                clip_duration,
            )
            captioned = temp_dir / "clip_1_captioned.mp4"
            overlay_caption_frames(
                current_segment,
                str(caption_dir / "frame_%04d.png"),
                settings.fps,
                captioned,
            )
            current_segment = captioned

        emit(f"Applying animated overlays to clip {index}", min(62 + (index * 4), 78))
        with_title = temp_dir / f"clip_{index}_with_title.mp4"
        overlay_frame_sequence(
            current_segment,
            str(title_frames_root / f"clip_{index}_frames" / "frame_%04d.png"),
            settings.fps,
            with_title,
        )

        with_numbers = temp_dir / f"clip_{index}_final.mp4"
        overlay_image(with_title, overlays_dir / f"overlay_{index}.png", with_numbers)
        final_segments.append(with_numbers)

        # Intermission goes after clips 1-4 and introduces the next caption.
        if index < len(settings.clips) and settings.use_intermissions:
            emit(f"Creating intermission {index}", min(70 + (index * 4), 86))
            next_caption = sanitize_tts_text(settings.clips[index].caption)
            narration_audio = None
            intermission_duration = 1.2
            word_timings: list[tuple[str, float, float]] = []

            if settings.enable_narration:
                narration_audio = temp_dir / f"intermission_{index}.mp3"
                int_data = generate_speech_hq_with_timestamps(
                    text=next_caption,
                    output_path=narration_audio,
                    voice_id=settings.elevenlabs_voice_id,
                    audio_model_id=settings.audio_model_id,
                    timestamp_model_id=settings.timestamp_model_id,
                    voice_settings=settings.voice_settings,
                    api_key=settings.elevenlabs_api_key,
                )
                intermission_duration = max(1.0, float(int_data["duration"]))
                word_timings = int_data["word_timings"]

            intermission = temp_dir / f"intermission_{index}_raw.mp4"
            create_intermission(
                intermission,
                settings.output_width,
                settings.output_height,
                intermission_duration,
                narration_audio,
                opacity=settings.intermission_opacity,
            )

            if settings.enable_narration and word_timings:
                caption_frames_dir = temp_dir / f"intermission_{index}_caption_frames"
                generate_caption_frames(
                    word_timings,
                    caption_frames_dir,
                    settings.output_width,
                    settings.output_height,
                    settings.fps,
                    intermission_duration,
                )
                intermission_captioned = temp_dir / f"intermission_{index}_final.mp4"
                overlay_caption_frames(
                    intermission,
                    str(caption_frames_dir / "frame_%04d.png"),
                    settings.fps,
                    intermission_captioned,
                )
                intermission = intermission_captioned

            final_segments.append(intermission)

    emit("Concatenating final sequence", 90)
    concatenated = temp_dir / "final_concatenated.mp4"
    concatenate_segments(
        final_segments,
        concatenated,
        settings.output_width,
        settings.output_height,
        settings.fps,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "_".join((settings.title_line_2 or "Top5").split())
    base_output = output_dir / f"Top5_{safe_title}_{timestamp}.mp4"

    if settings.include_music and settings.background_music and settings.background_music.exists():
        emit("Mixing background music", 96)
        mix_background_music(concatenated, settings.background_music, base_output, music_volume=settings.background_music_level)
    else:
        base_output.parent.mkdir(parents=True, exist_ok=True)
        base_output.write_bytes(concatenated.read_bytes())

    emit("Render completed", 100)
    return base_output
