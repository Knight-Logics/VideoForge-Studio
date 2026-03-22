from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class ClipInput:
    file_path: Path
    caption: str


@dataclass
class RenderSettings:
    title_line_1: str
    title_line_2: str
    clips: list[ClipInput]
    output_width: int = 1440
    output_height: int = 2560
    title_font_family: str = "gill-sans-ultra-bold"
    list_font_family: str = "gill-sans-ultra-bold"
    title_font_size: int = 96
    list_font_size: int = 56
    fps: int = 30
    include_music: bool = False
    background_music: Optional[Path] = None
    background_music_level: float = 0.15
    enable_narration: bool = False
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    audio_model_id: str = "eleven_v3"
    timestamp_model_id: str = "eleven_flash_v2_5"
    voice_settings: dict = field(
        default_factory=lambda: {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.05,
            "speed": 1.08,
            "use_speaker_boost": True,
        }
    )
    use_intermissions: bool = True
    intermission_opacity: float = 100.0

    @property
    def output_label(self) -> str:
        return f"{self.output_width}x{self.output_height}"


@dataclass
class WorkspacePaths:
    root: Path
    uploads: Path
    jobs: Path
    outputs: Path
    cache: Path

    @classmethod
    def from_root(cls, root: Path) -> "WorkspacePaths":
        return cls(
            root=root,
            uploads=root / "uploads",
            jobs=root / "jobs",
            outputs=root / "outputs",
            cache=root / "cache",
        )

