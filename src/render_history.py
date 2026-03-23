"""Render history storage linked to access codes for recovery and protection."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class RenderHistory:
    """Stores completed renders by access code for safe recovery."""

    def __init__(self, history_file: Path):
        self.history_file = history_file
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self.history_file.write_text("{}")

    def save_render(
        self,
        access_code: str,
        output_filename: str,
        title_line_1: str,
        title_line_2: str,
        used_narration: bool,
        output_width: int,
        output_height: int,
    ) -> None:
        """Save completed render metadata to history linked to access code."""
        data = self._load()
        if access_code not in data:
            data[access_code] = []

        render_record = {
            "filename": output_filename,
            "title_line_1": title_line_1,
            "title_line_2": title_line_2,
            "used_narration": used_narration,
            "output_width": output_width,
            "output_height": output_height,
            "completed_at": datetime.now().isoformat(),
        }
        data[access_code].append(render_record)

        # Keep only last 20 renders per token to avoid unbounded growth
        if len(data[access_code]) > 20:
            data[access_code] = data[access_code][-20:]

        self._save(data)

    def get_renders(self, access_code: str) -> list[dict[str, Any]]:
        """Retrieve all renders for an access code, newest first."""
        data = self._load()
        renders = data.get(access_code, [])
        return list(reversed(renders))

    def _load(self) -> dict[str, list[dict[str, Any]]]:
        """Load history from disk."""
        try:
            content = self.history_file.read_text(encoding="utf-8")
            return json.loads(content) if content.strip() else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self, data: dict[str, list[dict[str, Any]]]) -> None:
        """Save history to disk."""
        self.history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
