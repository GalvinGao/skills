"""Cue sheet: sections snapped to bar lines, plus every bar and beat with its video frame.

This is the file to plan shots against: cut on ``sections[*].start_frame`` or on
``bars[*].frame``, and hit accents on ``beats[*].frame``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from songscope.common import frame_of, timecode, write_json

FRAME_START = 1
# Section boundaries within one beat of a downbeat move onto it; others stay put.
SNAP_BARS = 0.25


def build_cues(song: Path, structure: dict, beats: dict, fps: int, duration: float, out: Path) -> dict:
    down = np.array(beats["downbeats"])
    bar_len = beats["period"] * beats["beats_per_bar"]
    bar_of_downbeat = {round(b["t"], 4): b["bar"] for b in beats["beats"] if b["beat"] == 1 and b["bar"]}
    beat_t = np.array([b["t"] for b in beats["beats"]])

    def snap(t: float) -> float:
        if len(down) == 0 or t <= 0 or t >= duration:
            return t
        i = int(np.argmin(np.abs(down - t)))
        return float(down[i]) if abs(down[i] - t) <= SNAP_BARS * bar_len else t

    sections = []
    for s in structure["sections"]:
        start, end = snap(s["start"]), snap(s["end"])
        if s is structure["sections"][-1]:
            end = duration
        entry = {
            "name": s["name"],
            "label": s["label"],
            "start": start,
            "end": end,
            "start_frame": frame_of(start, fps, FRAME_START),
            "end_frame": frame_of(end, fps, FRAME_START),
            "start_tc": timecode(start, fps),
            "raw_start": s["start"],
        }
        # First downbeat of the section: where a cut usually goes, even when the section
        # starts on a pickup a couple of beats earlier.
        later = down[down >= start - beats["period"] / 2] if len(down) else down
        if len(later) and later[0] - start < bar_len and start > 0:
            entry["downbeat"] = float(later[0])
            entry["downbeat_frame"] = frame_of(float(later[0]), fps, FRAME_START)
            entry["downbeat_bar"] = bar_of_downbeat.get(round(float(later[0]), 4))
        bar = bar_of_downbeat.get(round(start, 4))
        if bar is not None:
            entry["start_bar"] = bar
            entry["bars"] = int(round((end - start) / bar_len))
        elif len(beat_t) and start > 0:
            # Off the bar line (e.g. a pickup into a verse): record which beat it sits on.
            i = int(np.argmin(np.abs(beat_t - start)))
            if abs(beat_t[i] - start) <= beats["period"] / 2 and beats["beats"][i]["bar"]:
                entry["start_bar_beat"] = f"{beats['beats'][i]['bar']}.{beats['beats'][i]['beat']}"
        sections.append(entry)

    data = {
        "song": str(song),
        "fps": fps,
        "frame_start": FRAME_START,
        "frame_end": frame_of(duration, fps, FRAME_START),
        "duration": duration,
        "bpm": beats["bpm"],
        "beats_per_bar": beats["beats_per_bar"],
        "frames_per_beat": beats["period"] * fps,
        "sections": sections,
        "bars": [
            {"bar": b["bar"], "t": b["t"], "frame": frame_of(b["t"], fps, FRAME_START)}
            for b in beats["beats"]
            if b["beat"] == 1 and b["bar"]
        ],
        "beats": [
            {"t": b["t"], "frame": frame_of(b["t"], fps, FRAME_START), "bar": b["bar"], "beat": b["beat"]}
            for b in beats["beats"]
        ],
    }
    write_json(out, data)
    return data
