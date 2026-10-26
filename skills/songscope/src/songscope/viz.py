"""Static overview board: spectrogram, sections, bar grid, and the main control curves."""

from __future__ import annotations

from pathlib import Path

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from songscope.common import load_audio  # noqa: E402

SECTION_COLORS = {
    "intro": "#9aa5b1",
    "verse": "#4f86c6",
    "pre-chorus": "#8e6cc9",
    "chorus": "#39b5a4",
    "bridge": "#e0a030",
    "inst": "#c9677f",
    "solo": "#c9677f",
    "break": "#b0b0b0",
    "outro": "#7c8a99",
    "end": "#5a6570",
}
PITCH_CLASSES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _shade_sections(ax, cues: dict, labels: bool = False) -> None:
    for s in cues["sections"]:
        color = SECTION_COLORS.get(s["label"], "#cccccc")
        ax.axvspan(s["start"], s["end"], color=color, alpha=0.18, lw=0)
        ax.axvline(s["start"], color=color, lw=1.2, alpha=0.9)
        if labels:
            ax.text(s["start"] + 0.4, 0.97, s["name"], transform=ax.get_xaxis_transform(),
                    va="top", ha="left", fontsize=8, color="#222", clip_on=True)


def render_overview(song: Path, cues: dict, features: dict, out: Path) -> Path:
    y, sr = load_audio(song, sr=22050)
    fps = features["fps"]
    ch = features["channels"]
    t = np.arange(features["n_frames"]) / fps
    duration = features["duration"]

    fig, axes = plt.subplots(7, 1, figsize=(30, 18), sharex=True,
                             gridspec_kw={"height_ratios": [1.0, 2.2, 1.2, 1.2, 1.0, 0.8, 1.4]})
    fig.suptitle(
        f"{Path(song).name} - {cues['bpm']:.2f} BPM, {cues['frames_per_beat']:.2f} frames/beat at {fps} fps",
        fontsize=14, x=0.01, ha="left",
    )

    ax = axes[0]
    env = np.array(ch["rms"])
    ax.fill_between(t, -env, env, color="#333", lw=0)
    ax.set_ylabel("loudness")
    ax.set_yticks([])
    _shade_sections(ax, cues, labels=True)

    ax = axes[1]
    mel = librosa.power_to_db(librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, hop_length=512), ref=np.max)
    ax.imshow(mel, origin="lower", aspect="auto", cmap="magma", extent=[0, len(y) / sr, 0, 128], vmin=-80, vmax=0)
    for b in cues["bars"]:
        ax.axvline(b["t"], color="white", lw=0.35, alpha=0.35)
    for b in cues["bars"][::8]:
        ax.text(b["t"], 126, str(b["bar"]), color="white", fontsize=7, va="top", ha="center")
    ax.set_ylabel("mel spectrogram\n(bar lines, bar no.)")
    ax.set_yticks([])

    ax = axes[2]
    for name, color in [("sub", "#5b2a86"), ("bass", "#2f6fb0"), ("mid", "#2aa198"), ("high", "#d9a400")]:
        ax.plot(t, ch[name], lw=0.6, color=color, label=name)
    ax.set_ylabel("mix bands")
    ax.legend(loc="upper right", fontsize=8, ncol=4)
    _shade_sections(ax, cues)

    ax = axes[3]
    for name, color in [("stem_vocals", "#e0457b"), ("stem_drums", "#444"), ("stem_bass", "#2f6fb0"), ("stem_other", "#2aa198")]:
        if name in ch:
            ax.plot(t, ch[name], lw=0.6, color=color, label=name.removeprefix("stem_"))
    ax.set_ylabel("stems")
    ax.legend(loc="upper right", fontsize=8, ncol=4)
    _shade_sections(ax, cues)

    ax = axes[4]
    for name, color, off in [("kick", "#222", 2), ("snare", "#c0392b", 1), ("hat", "#d9a400", 0)]:
        if name in ch:
            ax.plot(t, np.array(ch[name]) * 0.9 + off, lw=0.5, color=color)
    ax.set_ylabel("drum hits")
    ax.set_yticks([0.45, 1.45, 2.45], ["hat", "snare", "kick"], fontsize=8)
    _shade_sections(ax, cues)

    ax = axes[5]
    if "vocal_midi" in ch:
        midi = np.array(ch["vocal_midi"])
        ax.scatter(t[midi > 0], midi[midi > 0], s=0.4, color="#e0457b")
        lo, hi = features["meta"]["vocal_midi_range"]
        ax.set_ylim(lo, hi)
        ticks = list(range(lo + (12 - lo % 12) % 12, hi + 1, 12))
        ax.set_yticks(ticks, [librosa.midi_to_note(m) for m in ticks], fontsize=8)
    ax.set_ylabel("vocal pitch")
    _shade_sections(ax, cues)

    ax = axes[6]
    chroma = np.array([ch[f"chroma_{i:02d}"] for i in range(12)])
    ax.imshow(chroma, origin="lower", aspect="auto", cmap="Greys", extent=[0, t[-1], -0.5, 11.5], vmin=0, vmax=1)
    ax.set_yticks(range(12), PITCH_CLASSES, fontsize=7)
    ax.set_ylabel("chroma")
    ax.set_xlabel("time (s)")
    ax.set_xlim(0, duration)
    ax.set_xticks(np.arange(0, duration, 10))

    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out


EVENT_ROWS = ["kick", "snare", "toms", "hihat", "ride", "crash", "impact"]
KIND_COLORS = {"sparkle": "#d4a017", "stab": "#2f6fb0", "note": "#6c8ebf", "noise_fx": "#888888",
               "piano": "#8e6cc9", "guitar": "#c9677f"}
SWEEP_COLORS = {"riser": "#2aa198", "swell": "#39b5a4", "downlifter": "#c0392b"}


def render_events(cues: dict, events: dict, lyrics: dict | None, out: Path) -> Path:
    """Raster of every detected sound event: one row per drum piece, one per timbre cluster."""
    evs = events["events"]
    clusters = [c["id"] for c in events["clusters"]]
    rows = EVENT_ROWS + clusters
    duration = cues["duration"]
    tag_names = [n for n in ("Jingle, tinkle", "Glockenspiel", "Zing", "Chime", "Bell", "Whoosh, swoosh, swish",
                             "Synthesizer", "Synthetic singing") if n in events["tag_tracks"]]

    fig, (ax, ax_s, ax_t) = plt.subplots(3, 1, figsize=(30, 3 + 0.32 * len(rows) + 2 + 0.3 * len(tag_names)),
                                         sharex=True, gridspec_kw={"height_ratios": [len(rows), 1.6, max(1, len(tag_names) * 0.5)]})
    fig.suptitle(f"Sound events: {sum(events['counts'].values())} hits {events['counts']}", fontsize=12, x=0.01, ha="left")
    for s in cues["sections"]:
        for a in (ax, ax_s, ax_t):
            a.axvspan(s["start"], s["end"], color=SECTION_COLORS.get(s["label"], "#ccc"), alpha=0.12, lw=0)
            a.axvline(s["start"], color=SECTION_COLORS.get(s["label"], "#ccc"), lw=1)
        ax.text(s["start"] + 0.3, len(rows) - 0.2, s["name"], fontsize=7, va="top")
    for i, row in enumerate(rows):
        y = len(rows) - 1 - i
        sel = [e for e in evs if (e.get("cluster") == row) or (row in EVENT_ROWS and e["kind"] == row)]
        if not sel:
            continue
        t = np.array([e["t"] for e in sel])
        a = np.clip(np.array([e["strength"] for e in sel]), 0.15, 1)
        colors = [KIND_COLORS.get(e["kind"], "#222") for e in sel]
        ax.vlines(t, y - 0.38, y + 0.38, colors=colors, alpha=a, lw=0.8)
    labels = []
    for row in rows:
        c = next((c for c in events["clusters"] if c["id"] == row), None)
        labels.append(f"{row} ({c['count']}, {c['median_centroid_hz']} Hz)" if c else row)
    ax.set_yticks(range(len(rows)), labels[::-1], fontsize=7)
    ax.set_ylim(-0.6, len(rows) - 0.4)

    for s in events["sweeps"]:
        y = {"riser": 2, "swell": 1, "downlifter": 0}[s["kind"]]
        ax_s.plot([s["t"], s["end"]], [y, y + (0.6 if s["kind"] != "downlifter" else -0.0)],
                  color=SWEEP_COLORS[s["kind"]], lw=2)
    if lyrics:
        for line in lyrics["lines"]:
            for w in line["words"]:
                ax_s.add_patch(plt.Rectangle((w["start"], 3.1), w["end"] - w["start"], 0.6, color="#e0457b", alpha=0.6, lw=0))
    ax_s.set_yticks([0.3, 1.3, 2.3, 3.4], ["downlifter", "swell", "riser", "lyric words"], fontsize=7)
    ax_s.set_ylim(-0.3, 3.9)

    if tag_names:
        fps = events["tag_tracks_fps"]
        mat = np.array([events["tag_tracks"][n] for n in tag_names])
        ax_t.imshow(mat, aspect="auto", origin="lower", cmap="Greys", vmin=0, vmax=0.5,
                    extent=[0, mat.shape[1] / fps, -0.5, len(tag_names) - 0.5])
        ax_t.set_yticks(range(len(tag_names)), tag_names, fontsize=7)
    ax_t.set_xlabel("time (s)")
    ax_t.set_xlim(0, duration)
    ax_t.set_xticks(np.arange(0, duration, 10))
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out
