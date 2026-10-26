"""Per-song workspace paths and small I/O helpers shared by every analysis step."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import soxr

BEATS_PER_BAR = 4
# 30 fps gives 12 frames per beat at 150 BPM; any rate works, and every output that names
# frames records the rate it used.
DEFAULT_FPS = int(os.environ.get("SONGSCOPE_FPS", "30"))


def active_song() -> Path:
    """The song named by $SONGSCOPE_SONG; the CLI's --song takes precedence."""
    path = os.environ.get("SONGSCOPE_SONG")
    if not path:
        raise SystemExit("no song: pass --song PATH or set SONGSCOPE_SONG")
    return Path(path)


def workspace(song: Path) -> Path:
    """Everything derived from one song lives in one folder, so a song can be analyzed anywhere.

    $SONGSCOPE_DIR/<stem>/ when set, else songscope/<stem>/ beside the audio file. Several
    versions of one song (a rip and a master) sit side by side because the stem differs.
    """
    song = Path(song)
    base = Path(os.environ["SONGSCOPE_DIR"]) if os.environ.get("SONGSCOPE_DIR") else song.resolve().parent / "songscope"
    return base / song.stem


def analysis_dir(song: Path) -> Path:
    return workspace(song) / "analysis"


def stems_dir(song: Path) -> Path:
    return workspace(song) / "stems"


def lyrics_dir(song: Path) -> Path:
    """Lyric text (lyrics.txt, supplied by the user) and its timing outputs."""
    return workspace(song) / "lyrics"


def load_audio(path: Path, sr: int | None = None, mono: bool = True) -> tuple[np.ndarray, int]:
    """Read audio as float32, optionally downmixed and resampled. Shape (n,) or (n, ch)."""
    y, native_sr = sf.read(str(path), dtype="float32", always_2d=True)
    if mono:
        y = y.mean(axis=1)
    if sr is not None and sr != native_sr:
        y = soxr.resample(y, native_sr, sr, quality="HQ").astype(np.float32)
        native_sr = sr
    return y, native_sr


def _round_floats(obj: Any, ndigits: int) -> Any:
    if isinstance(obj, float):
        return round(obj, ndigits)
    if isinstance(obj, dict):
        return {k: _round_floats(v, ndigits) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v, ndigits) for v in obj]
    if isinstance(obj, np.ndarray):
        return _round_floats(obj.tolist(), ndigits)
    if isinstance(obj, np.generic):
        return _round_floats(obj.item(), ndigits)
    return obj


def write_json(path: Path, data: Any, ndigits: int = 4, indent: int | None = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_round_floats(data, ndigits), indent=indent, ensure_ascii=False) + "\n")
    return path


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text())


def frame_of(t: float, fps: int, frame_start: int = 1) -> int:
    """Video frame whose start is closest to time t (frame_start shows t = 0)."""
    return frame_start + int(round(t * fps))


def timecode(t: float, fps: int, hour_offset: int = 0) -> str:
    """Non-drop-frame SMPTE timecode, e.g. 01:00:12:07."""
    total = int(round(t * fps))
    ff = total % fps
    s = total // fps
    return f"{hour_offset + s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"
