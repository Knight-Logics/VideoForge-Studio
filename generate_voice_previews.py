"""
Run this script once to generate static voice preview MP3 files.
Output: static/voice-previews/<voice_id>.mp3

These files are served directly by the app - no ElevenLabs API call at runtime.

Usage:
    .venv\\Scripts\\python.exe generate_voice_previews.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1"
PREVIEW_TEXT = "Welcome to VideoForge Studio. I'm your selected narration voice."
OUTPUT_DIR = Path(__file__).parent / "static" / "voice-previews"

VOICE_OPTIONS = [
    {"id": "JBFqnCBsd6RMkjVDRZzb", "label": "George"},
    {"id": "9BWtsMINqrJLrRacOk9x", "label": "Aria"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "label": "Sarah"},
    {"id": "TX3LPaxmHKxFdv7VOQHJ", "label": "Liam"},
]


def generate_preview(api_key: str, voice_id: str, label: str, output_path: Path) -> None:
    print(f"Generating preview for {label} ({voice_id})...")
    url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
    payload = {
        "text": PREVIEW_TEXT,
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
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )

    if response.status_code != 200:
        print(f"  ERROR: {response.status_code} {response.text}")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    print(f"  Saved to {output_path}")


def main() -> None:
    api_key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        print("ERROR: ELEVENLABS_API_KEY not set in .env")
        sys.exit(1)

    for voice in VOICE_OPTIONS:
        output_path = OUTPUT_DIR / f"{voice['id']}.mp3"
        if output_path.exists():
            print(f"Skipping {voice['label']} — already exists at {output_path}")
            continue
        generate_preview(api_key, voice["id"], voice["label"], output_path)

    print("\nDone. All preview files saved to:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
