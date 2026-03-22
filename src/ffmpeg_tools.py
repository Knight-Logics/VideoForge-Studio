from __future__ import annotations

from pathlib import Path

from .utils import run_command


def normalize_clip(
    input_path: Path,
    output_path: Path,
    width: int,
    height: int,
    fps: int,
) -> None:
    filter_chain = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1"
    )
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vf",
        filter_chain,
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-ac",
        "2",
        str(output_path),
    ]
    run_command(cmd, f"Normalize clip {input_path.name}")


def overlay_image(video_path: Path, overlay_png: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(overlay_png),
        "-filter_complex",
        "[0:v][1:v]overlay=0:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        str(output_path),
    ]
    run_command(cmd, f"Overlay image on {video_path.name}")


def overlay_frame_sequence(
    video_path: Path,
    frames_pattern: str,
    fps: int,
    output_path: Path,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-framerate",
        str(fps),
        "-i",
        frames_pattern,
        "-filter_complex",
        "[1:v]format=rgba[ov];[0:v][ov]overlay=0:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    run_command(cmd, f"Overlay animation on {video_path.name}")


def mix_audio_tracks(video_path: Path, narration_mp3: Path, output_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(narration_mp3),
        "-filter_complex",
        "[0:a]volume=0.7[a0];[1:a]volume=0.9[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
        "-map",
        "0:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        str(output_path),
    ]
    run_command(cmd, f"Mix narration with {video_path.name}")


def overlay_caption_frames(
    video_path: Path,
    caption_frames_pattern: str,
    fps: int,
    output_path: Path,
) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-framerate",
        str(fps),
        "-i",
        caption_frames_pattern,
        "-filter_complex",
        "[1:v]format=rgba[cv];[0:v][cv]overlay=0:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    run_command(cmd, f"Overlay captions on {video_path.name}")


def create_intermission(
    output_path: Path,
    width: int,
    height: int,
    duration: float,
    audio_path: Path | None,
    opacity: float = 100.0,
) -> None:
    # Convert opacity (0-100) to alpha value (0-255)
    # opacity=100 means fully opaque (alpha=255), opacity=0 means fully transparent (alpha=0)
    alpha_value = int((opacity / 100.0) * 255)
    
    if audio_path is None:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=white@{alpha_value/255:.2f}:s={width}x{height}:d={duration}",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-shortest",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(output_path),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=white@{alpha_value/255:.2f}:s={width}x{height}:d={duration}",
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    run_command(cmd, "Create intermission")


def concatenate_segments(segments: list[Path], output_path: Path, width: int, height: int, fps: int) -> None:
    inputs: list[str] = []
    normalize_parts: list[str] = []
    concat_parts: list[str] = []

    for index, segment in enumerate(segments):
        inputs.extend(["-i", str(segment)])
        normalize_parts.append(
            f"[{index}:v:0]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={fps},setsar=1[v{index}]"
        )
        concat_parts.append(f"[v{index}][{index}:a:0]")

    filter_complex = (
        ";".join(normalize_parts)
        + ";"
        + "".join(concat_parts)
        + f"concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        *inputs,
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output_path),
    ]
    run_command(cmd, "Concatenate all segments")


def mix_background_music(video_path: Path, music_path: Path, output_path: Path, music_volume: float = 0.15) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(music_path),
        "-i",
        str(video_path),
        "-filter_complex",
        f"[0:a]volume={music_volume}[music];[1:a]volume=1.0[main];[main][music]amix=inputs=2:duration=first[aout]",
        "-map",
        "1:v",
        "-map",
        "[aout]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        str(output_path),
    ]
    run_command(cmd, "Mix background music")
