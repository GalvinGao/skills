"""Higher-quality stem separation with mlx-audio-separator (runs on the Apple GPU).

allin1 already leaves htdemucs stems behind, which are fine for driving animation.
These presets give cleaner or finer stems:

    vocals   Mel-Band Roformer vocals / other      -> lyric alignment, vocal pitch
    4stem    htdemucs_ft vocals/drums/bass/other   -> better per-stem curves
    6stem    htdemucs_6s, adds guitar/piano        -> "other" left with synths and FX
    drumsep  MDX23C DrumSep on the 4stem drums     -> kick/snare/toms/hihat/ride/crash hits

Each preset writes plain names (vocals.wav, drums.wav, ...) into stems/<song>/<model>/.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from songscope.common import stems_dir

PRESETS = {
    "vocals": "vocals_mel_band_roformer.ckpt",  # vocals SDR 12.6
    "4stem": "htdemucs_ft.yaml",
    "6stem": "htdemucs_6s.yaml",
    "drumsep": "MDX23C-DrumSep-aufr33-jarredou.ckpt",
}
# DrumSep must see a drums-only signal, not the full mix: (preset, file) it reads by default.
DEFAULT_INPUTS = {"drumsep": ("4stem", "drums.wav")}
# mlx-audio-separator stem names (matched case-insensitively) -> our file names.
OUTPUT_NAMES = {
    "vocals": "vocals", "instrumental": "instrumental", "other": "other",
    "drums": "drums", "bass": "bass", "guitar": "guitar", "piano": "piano",
    "kick": "kick", "snare": "snare", "toms": "toms", "hh": "hihat", "ride": "ride", "crash": "crash",
}


def stems_dir_for(song: Path, preset: str) -> Path:
    return stems_dir(song) / Path(PRESETS.get(preset, preset)).stem


def separate(song: Path, preset: str, source: Path | None = None) -> Path:
    model = PRESETS.get(preset, preset)
    if source is None:
        dep = DEFAULT_INPUTS.get(preset)
        source = stems_dir_for(song, dep[0]) / dep[1] if dep else song
    if not Path(source).exists():
        raise FileNotFoundError(f"{source} not found (drumsep needs `songscope separate --preset 4stem` first)")
    out_dir = stems_dir_for(song, preset)
    out_dir.mkdir(parents=True, exist_ok=True)
    exe = Path(sys.executable).with_name("mlx-audio-separator")
    subprocess.run(
        [
            str(exe), str(source),
            "-m", model,
            "--output_dir", str(out_dir),
            "--output_format", "WAV",
            "--custom_output_names", json.dumps(OUTPUT_NAMES),
        ],
        check=True,
    )
    return out_dir
