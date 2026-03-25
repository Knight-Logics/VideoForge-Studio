from __future__ import annotations

import base64
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

import requests

from .utils import resolve_command

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"


def sanitize_tts_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = cleaned.replace("—", ", ").replace("–", ", ")
    cleaned = cleaned.replace("...", ".")
    cleaned = re.sub(r"([!?.,])\1+", r"\1", cleaned)
    cleaned = re.sub(r"[\"“”`]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or text.strip()


def _probe_duration(audio_path: Path) -> float:
    result = subprocess.run(
        [
            resolve_command("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 0.0
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def parse_word_timings(
    text: str,
    characters: list[str],
    start_times: list[float],
    end_times: list[float],
) -> list[tuple[str, float, float]]:
    words = text.split()
    timings: list[tuple[str, float, float]] = []
    char_index = 0

    for word in words:
        while char_index < len(characters) and characters[char_index] in {" ", "\n", "\t"}:
            char_index += 1

        if char_index >= len(characters):
            break

        word_start = start_times[char_index]
        word_end = word_start
        for _ in word:
            if char_index < len(characters):
                word_end = end_times[char_index]
                char_index += 1

        timings.append((word, word_start, word_end))

    return timings


def _generate_audio_only(
    text: str,
    output_path: Path,
    api_key: str,
    voice_id: str,
    model_id: str,
    voice_settings: Optional[dict] = None,
) -> dict:
    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": "mp3_44100_128",
        "voice_settings": voice_settings
        or {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.05,
            "speed": 1.08,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(
        url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs audio endpoint error: {response.status_code} {response.text}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)

    return {
        "audio_path": output_path,
        "duration": _probe_duration(output_path),
    }


def _generate_timestamps(
    text: str,
    api_key: str,
    voice_id: str,
    model_id: str,
    voice_settings: Optional[dict] = None,
) -> dict:
    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}/with-timestamps"
    payload = {
        "text": text,
        "model_id": model_id,
        "output_format": "mp3_44100_128",
        "voice_settings": voice_settings
        or {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.05,
            "speed": 1.08,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(
        url,
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs timestamp endpoint error: {response.status_code} {response.text}")

    result = response.json()
    word_timings = parse_word_timings(
        text,
        result["alignment"]["characters"],
        result["alignment"]["character_start_times_seconds"],
        result["alignment"]["character_end_times_seconds"],
    )

    audio_data = base64.b64decode(result["audio_base64"])
    timestamp_duration = word_timings[-1][2] if word_timings else 0.0
    return {"word_timings": word_timings, "timestamp_duration": timestamp_duration, "audio_data": audio_data}


def generate_speech_hq_with_timestamps(
    text: str,
    output_path: Path,
    voice_id: Optional[str],
    audio_model_id: str,
    timestamp_model_id: str,
    voice_settings: dict,
    api_key: Optional[str] = None,
) -> dict:
    resolved_api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    resolved_voice = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "")

    if not resolved_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    if not resolved_voice:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not set")

    cleaned_text = sanitize_tts_text(text)

    audio_result = _generate_audio_only(
        cleaned_text,
        output_path,
        resolved_api_key,
        resolved_voice,
        audio_model_id,
        voice_settings,
    )
    timing_result = _generate_timestamps(
        cleaned_text,
        resolved_api_key,
        resolved_voice,
        timestamp_model_id,
        voice_settings,
    )

    hq_duration = audio_result.get("duration", 0.0)
    ts_duration = timing_result.get("timestamp_duration", 0.0)
    word_timings = timing_result.get("word_timings", [])

    if hq_duration > 0 and ts_duration > 0 and word_timings:
        scale = hq_duration / ts_duration
        word_timings = [
            (word, start * scale, end * scale) for word, start, end in word_timings
        ]

    return {
        "audio_path": output_path,
        "duration": hq_duration if hq_duration > 0 else ts_duration,
        "word_timings": word_timings,
    }


def generate_voice_preview(text: str, voice_id: str, api_key: Optional[str] = None) -> tuple[bytes, str]:
    """
    Generate a voice preview sample without writing to disk.
    Returns (audio_bytes, content_type) for immediate streaming.
    Used for UI previews — does NOT charge credits.
    """
    resolved_api_key = api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    resolved_voice = voice_id or os.environ.get("ELEVENLABS_VOICE_ID", "")

    if not resolved_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")
    if not resolved_voice:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not set")

    cleaned_text = sanitize_tts_text(text)
    if not cleaned_text:
        cleaned_text = "This is a voice preview sample."

    url = f"{ELEVENLABS_API_URL}/text-to-speech/{resolved_voice}"
    payload = {
        "text": cleaned_text,
        "model_id": "eleven_monolingual_v1",
        "output_format": "mp3_44100_128",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.05,
            "speed": 1.08,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(
        url,
        headers={"xi-api-key": resolved_api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ElevenLabs preview endpoint error: {response.status_code} {response.text}")

    return response.content, "audio/mpeg"
