"""Marker exports for editors: DaVinci Resolve EDL, a generic CSV, and Audacity labels."""

from __future__ import annotations

import csv
from pathlib import Path

from songscope.common import timecode

RESOLVE_COLORS = {
    "intro": "Sky",
    "verse": "Blue",
    "pre-chorus": "Purple",
    "chorus": "Green",
    "bridge": "Yellow",
    "inst": "Pink",
    "solo": "Pink",
    "break": "Cream",
    "outro": "Lavender",
    "end": "Cocoa",
}
RESOLVE_START_HOUR = 1  # Resolve timelines start at 01:00:00:00 by default


def _resolve_edl(markers: list[dict], fps: int, title: str) -> str:
    """CMX3600 marker EDL, as read by Resolve's Timeline > Import > Timeline Markers from EDL."""
    lines = [f"TITLE: {title}", "FCM: NON-DROP FRAME", ""]
    for i, m in enumerate(markers, 1):
        tc_in = timecode(m["t"], fps, RESOLVE_START_HOUR)
        tc_out = timecode(m["t"] + 1 / fps, fps, RESOLVE_START_HOUR)
        lines.append(f"{i:03d}  001      V     C        {tc_in} {tc_out} {tc_in} {tc_out}  ")
        lines.append(f" |C:ResolveColor{m['color']} |M:{m['name']} |D:{m.get('duration_frames', 1)}")
        lines.append("")
    return "\n".join(lines)


def export_markers(cues: dict, out_dir: Path, bars_every: int = 0) -> list[Path]:
    fps = cues["fps"]
    markers = [
        {
            "t": s["start"],
            "name": s["name"],
            "kind": "section",
            "color": RESOLVE_COLORS.get(s["label"], "Blue"),
            "duration_frames": max(1, s["end_frame"] - s["start_frame"]),
        }
        for s in cues["sections"]
    ]
    if bars_every:
        markers += [
            {"t": b["t"], "name": f"bar {b['bar']}", "kind": "bar", "color": "Cream"}
            for b in cues["bars"]
            if (b["bar"] - 1) % bars_every == 0
        ]
    markers.sort(key=lambda m: m["t"])

    out_dir.mkdir(parents=True, exist_ok=True)
    edl = out_dir / "markers_resolve.edl"
    edl.write_text(_resolve_edl(markers, fps, f"{cues.get('title') or Path(cues['song']).stem} markers"))

    csv_path = out_dir / "markers.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kind", "name", "time_s", "frame", "timecode", "resolve_timecode"])
        for m in markers:
            w.writerow([
                m["kind"], m["name"], f"{m['t']:.4f}", cues["frame_start"] + round(m["t"] * fps),
                timecode(m["t"], fps), timecode(m["t"], fps, RESOLVE_START_HOUR),
            ])

    # Audacity: File > Import > Labels. One label per section, spanning the section.
    labels = out_dir / "sections_audacity.txt"
    labels.write_text("".join(f"{s['start']:.4f}\t{s['end']:.4f}\t{s['name']}\n" for s in cues["sections"]))
    return [edl, csv_path, labels]
