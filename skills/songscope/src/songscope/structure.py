"""Metrical and functional structure (beats, downbeats, labelled sections) via allin1-mlx."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from songscope.common import stems_dir, write_json

ALLIN1_STEMS = ("vocals", "drums", "bass", "other")


def allin1_stems_dir(song: Path) -> Path:
    """Where allin1 leaves its htdemucs stems when byproducts are kept."""
    return stems_dir(song) / "allin1_demix" / "htdemucs" / Path(song).stem


def analyze_structure(song: Path, out: Path) -> dict:
    # Imported lazily: MLX/model setup is slow and most subcommands never need it.
    from allin1_mlx import analyze

    song = Path(song)
    result = analyze(
        song,
        out_dir=out.parent / "allin1",
        demix_dir=stems_dir(song) / "allin1_demix",
        spec_dir=out.parent / "allin1" / "spec",
        keep_byproducts=True,  # keep the htdemucs stems; features.py reuses them
        multiprocess=False,
        demix_seed=0,  # Demucs applies a random time shift; fix it so section times are reproducible
    )

    counts: Counter[str] = Counter()
    sections = []
    for seg in result.segments:
        counts[seg.label] += 1
        sections.append({
            "name": f"{seg.label}_{counts[seg.label]}",
            "label": seg.label,
            "start": float(seg.start),
            "end": float(seg.end),
        })

    data = {
        "source": "allin1-mlx (harmonix-all)",
        "song": str(song),
        "bpm": float(result.bpm),
        "beats": [float(b) for b in result.beats],
        "downbeats": [float(b) for b in result.downbeats],
        "beat_positions": [int(p) for p in result.beat_positions],
        "sections": sections,
        "stems_dir": str(allin1_stems_dir(song)),
    }
    write_json(out, data)
    return data
