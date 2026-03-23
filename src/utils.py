from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{description} failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def ensure_dirs(paths: list[Path]) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def get_resource_root() -> Path:
    override = os.environ.get("VIDEOFORGE_RESOURCE_ROOT")
    if override:
        return Path(override)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def get_runtime_root() -> Path:
    override = os.environ.get("VIDEOFORGE_RUNTIME_ROOT")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return get_resource_root()


def resolve_command(binary_name: str) -> str:
    runtime_root = get_runtime_root()
    candidate_names = [binary_name]
    if os.name == "nt" and not binary_name.lower().endswith(".exe"):
        candidate_names.insert(0, f"{binary_name}.exe")

    candidate_paths: list[Path] = []
    for candidate_name in candidate_names:
        candidate_paths.extend(
            [
                runtime_root / candidate_name,
                runtime_root / "bin" / candidate_name,
                runtime_root / "ffmpeg" / candidate_name,
                runtime_root / "ffmpeg" / "bin" / candidate_name,
            ]
        )

    for candidate in candidate_paths:
        if candidate.exists():
            return str(candidate)

    resolved = shutil.which(binary_name)
    if resolved:
        return resolved

    return binary_name


def get_media_duration_seconds(path: Path) -> float:
    cmd = [
        resolve_command("ffprobe"),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe could not read duration for {path}")
    return float(result.stdout.strip())


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
