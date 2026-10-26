"""Per-frame control curves for animation, sampled exactly at the video frame rate.

Sample i is the audio at t = i / fps, which a video or 3D timeline shows on frame ``frame_start + i``.
Every channel is a flat list of floats, mostly normalized to 0..1, so that it can be
baked to an F-curve or read by a driver without further scaling.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from songscope.common import load_audio, read_json, write_json

ANALYSIS_SR = 48000  # divisible by 24, 25, 30, 48, 50 and 60, so the hop is an integer
N_FFT = 4096  # ~11.7 Hz bins at 48 kHz: enough to split sub from bass

BANDS = {  # Hz
    "sub": (20, 60),
    "bass": (60, 250),
    "lowmid": (250, 1000),
    "mid": (1000, 4000),
    "high": (4000, 10000),
    "air": (10000, 20000),
}
VOCAL_MIDI_RANGE = (52, 88)  # E3..E6, generous for a Vocaloid lead
BEAT_PULSE_TAU = 0.10
DOWNBEAT_PULSE_TAU = 0.25

CHANNEL_DOCS = {
    "rms": "full-mix loudness, dB mapped to 0..1 over a 45 dB range",
    "sub/bass/lowmid/mid/high/air": "band energy of the mix, dB mapped to 0..1",
    "onset": "spectral-flux onset strength of the mix, 0..1",
    "centroid": "spectral centroid (brightness), log-mapped 100 Hz..10 kHz to 0..1",
    "stem_vocals/drums/bass/other": "loudness of each separated stem, 0..1",
    "kick/snare/hat": "onset strength of the drum stem in low/mid/high bands, 0..1",
    "vocal_pitch": "lead vocal pitch mapped over MIDI 52..88 to 0..1, 0 when unvoiced",
    "vocal_midi": "lead vocal pitch as a MIDI note number, 0 when unvoiced",
    "vocal_voiced": "1 when the lead vocal is singing a pitched note",
    "chroma_00..11": "pitch-class energy C..B of the mix, 0..1 per frame, 0 in silence",
    "beat_phase/bar_phase": "0 -> 1 sawtooth across each beat / bar",
    "beat_pulse/downbeat_pulse": "1 on each beat / downbeat, exponential decay after it",
    "beat_index/bar_index/beat_in_bar": "integer counters (bar 1 = first downbeat of the grid)",
    "section_index/section_phase": "index into cues.sections, 0 -> 1 progress through it",
    "section_label": "index into meta.labels",
    "is_chorus": "1 inside chorus sections",
    "evt_<kind>": "strength-weighted decaying pulse per sound-event kind from events.json "
                  "(kick, snare, toms, hihat, ride, crash, sparkle, noise_fx, stab, note, piano, guitar, impact)",
    "evt_riser/evt_swell": "0 -> 1 ramp across each detected riser / level swell",
    "evt_downlifter": "1 -> 0 ramp across each detected downlifter",
    "lyric_active": "1 while a lyric word is being sung (lyrics/alignment.json, else the ASR draft)",
    "lyric_word_pulse": "1 at each word onset, fast decay",
    "lyric_line/lyric_line_phase": "current lyric line number (1-based, 0 between lines) and 0 -> 1 progress",
}


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)), mode="edge")


def _norm_db(power: np.ndarray, range_db: float = 45.0) -> np.ndarray:
    db = 10 * np.log10(power + 1e-12)
    hi = np.percentile(db, 99.5)
    return np.clip((db - (hi - range_db)) / range_db, 0, 1)


def _norm_peak(x: np.ndarray, pct: float = 99.5) -> np.ndarray:
    ref = np.percentile(x, pct)
    return np.clip(x / ref, 0, 1) if ref > 0 else np.zeros_like(x)


def _frame_rms(y: np.ndarray, hop: int, n: int) -> np.ndarray:
    rms = librosa.feature.rms(y=y, frame_length=hop * 2, hop_length=hop, center=True)[0]
    return _fit(rms, n)


def _pulse(times: np.ndarray, events: np.ndarray, tau: float) -> np.ndarray:
    idx = np.searchsorted(events, times, side="right") - 1
    out = np.zeros_like(times)
    ok = idx >= 0
    out[ok] = np.exp(-(times[ok] - events[idx[ok]]) / tau)
    return out


def _phase(times: np.ndarray, events: np.ndarray) -> np.ndarray:
    idx = np.searchsorted(events, times, side="right") - 1
    out = np.zeros_like(times)
    ok = (idx >= 0) & (idx < len(events) - 1)
    lo, hi = events[idx[ok]], events[idx[ok] + 1]
    out[ok] = (times[ok] - lo) / (hi - lo)
    return out


def _stem_features(stems_dir: Path, hop: int, n: int) -> dict[str, np.ndarray]:
    ch: dict[str, np.ndarray] = {}
    for stem in ("vocals", "drums", "bass", "other"):
        path = stems_dir / f"{stem}.wav"
        if path.exists():
            y, _ = load_audio(path, sr=ANALYSIS_SR)
            ch[f"stem_{stem}"] = _norm_db(_frame_rms(y, hop, n) ** 2)

    drums = stems_dir / "drums.wav"
    if drums.exists():
        y, _ = load_audio(drums, sr=ANALYSIS_SR)
        mel = librosa.feature.melspectrogram(y=y, sr=ANALYSIS_SR, n_fft=2048, hop_length=hop, n_mels=96, fmax=16000)
        mel_f = librosa.mel_frequencies(n_mels=96, fmax=16000)
        edges = [0, int(np.searchsorted(mel_f, 150)), int(np.searchsorted(mel_f, 5000)), 96]
        multi = librosa.onset.onset_strength_multi(
            S=librosa.power_to_db(mel), sr=ANALYSIS_SR, hop_length=hop, channels=edges
        )
        for name, row in zip(("kick", "snare", "hat"), multi):
            ch[name] = _norm_peak(_fit(row, n))

    vocals = stems_dir / "vocals.wav"
    if vocals.exists():
        sr_v = 24000
        y, _ = load_audio(vocals, sr=sr_v)
        f0, voiced, _prob = librosa.pyin(
            y,
            fmin=librosa.midi_to_hz(VOCAL_MIDI_RANGE[0]),
            fmax=librosa.midi_to_hz(VOCAL_MIDI_RANGE[1]),
            sr=sr_v,
            frame_length=2048,
            hop_length=hop * sr_v // ANALYSIS_SR,
        )
        # pyin also "hears" bleed in near-silent stems; require some vocal energy too.
        voiced = _fit(voiced.astype(float), n) * (ch.get("stem_vocals", np.ones(n)) > 0.3)
        midi = np.nan_to_num(librosa.hz_to_midi(_fit(np.nan_to_num(f0, nan=0.0), n).clip(1e-3)), nan=0.0)
        midi = np.where(voiced > 0, midi, 0.0)
        lo, hi = VOCAL_MIDI_RANGE
        ch["vocal_pitch"] = np.where(voiced > 0, np.clip((midi - lo) / (hi - lo), 0, 1), 0.0)
        ch["vocal_midi"] = midi
        ch["vocal_voiced"] = voiced
    return ch


def compute_features(song: Path, beats: dict, cues: dict, stems_dir: Path | None, fps: int, out: Path) -> dict:
    y, sr = load_audio(song, sr=ANALYSIS_SR)
    hop = sr // fps
    if hop * fps != sr:
        raise ValueError(f"{fps} fps does not divide {sr} Hz; pick 24/25/30/48/50/60")
    duration = len(y) / sr
    n = int(np.floor(duration * fps)) + 1
    times = np.arange(n) / fps

    power = np.abs(librosa.stft(y, n_fft=N_FFT, hop_length=hop, center=True)) ** 2
    power = power[:, :n] if power.shape[1] >= n else np.pad(power, ((0, 0), (0, n - power.shape[1])), mode="edge")
    freqs = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)

    ch: dict[str, np.ndarray] = {}
    rms = _frame_rms(y, hop, n)
    ch["rms"] = _norm_db(rms**2)
    for name, (lo, hi) in BANDS.items():
        ch[name] = _norm_db(power[(freqs >= lo) & (freqs < hi)].sum(axis=0))
    ch["onset"] = _norm_peak(_fit(librosa.onset.onset_strength(S=librosa.power_to_db(power), sr=sr, hop_length=hop), n))
    centroid = librosa.feature.spectral_centroid(S=np.sqrt(power), sr=sr)[0]
    ch["centroid"] = np.clip(np.log(np.maximum(centroid, 100) / 100) / np.log(100), 0, 1)

    if stems_dir is not None and stems_dir.is_dir():
        ch.update(_stem_features(stems_dir, hop, n))

    harmonic = librosa.effects.harmonic(y, margin=2.0)
    chroma = librosa.feature.chroma_stft(y=harmonic, sr=sr, n_fft=8192, hop_length=hop)
    chroma = chroma[:, :n] if chroma.shape[1] >= n else np.pad(chroma, ((0, 0), (0, n - chroma.shape[1])), mode="edge")
    audible = ch["rms"] > 0.1
    for pc in range(12):
        ch[f"chroma_{pc:02d}"] = chroma[pc] * audible

    # Snap events to their nearest frame so a pulse peaks (and counters tick) on the frame
    # that shows the beat, not on the next one when the beat falls just after a frame start.
    beat_t = np.round(np.array([b["t"] for b in beats["beats"]]) * fps) / fps
    down_t = np.round(np.array(beats["downbeats"]) * fps) / fps
    ch["beat_phase"] = _phase(times, beat_t)
    ch["bar_phase"] = _phase(times, down_t)
    ch["beat_pulse"] = _pulse(times, beat_t, BEAT_PULSE_TAU)
    ch["downbeat_pulse"] = _pulse(times, down_t, DOWNBEAT_PULSE_TAU)
    last_beat = np.searchsorted(beat_t, times, side="right") - 1
    ch["beat_index"] = np.maximum(last_beat, -1).astype(float) + 1  # 0 before the first beat
    bars = np.array([b["bar"] or 0 for b in beats["beats"]], dtype=float)
    beat_in_bar = np.array([b["beat"] for b in beats["beats"]], dtype=float)
    ch["bar_index"] = np.where(last_beat >= 0, bars[np.maximum(last_beat, 0)], 0.0)
    ch["beat_in_bar"] = np.where(last_beat >= 0, beat_in_bar[np.maximum(last_beat, 0)], 0.0)

    labels = sorted({s["label"] for s in cues["sections"]})
    starts = np.array([s["start"] for s in cues["sections"]])
    ends = np.array([s["end"] for s in cues["sections"]])
    sec = np.clip(np.searchsorted(starts, times, side="right") - 1, 0, len(starts) - 1)
    ch["section_index"] = sec.astype(float)
    ch["section_phase"] = np.clip((times - starts[sec]) / (ends[sec] - starts[sec]), 0, 1)
    ch["section_label"] = np.array([labels.index(cues["sections"][i]["label"]) for i in sec], dtype=float)
    ch["is_chorus"] = np.array([cues["sections"][i]["label"] == "chorus" for i in sec], dtype=float)

    events_path = out.parent / "events.json"
    if events_path.exists():
        from songscope.events import event_channels

        ch.update(event_channels(read_json(events_path), n, fps))

    from songscope.lyrics import best_alignment, lyric_channels

    lyrics_path = best_alignment(song)
    if lyrics_path is not None:
        ch.update(lyric_channels(lyrics_path, n, fps))

    data = {
        "song": str(song),
        "fps": fps,
        "frame_start": cues["frame_start"],
        "n_frames": n,
        "duration": duration,
        "meta": {
            "labels": labels,
            "vocal_midi_range": list(VOCAL_MIDI_RANGE),
            "stems_dir": str(stems_dir) if stems_dir else None,
            "events": str(events_path) if events_path.exists() else None,
            "lyrics": str(lyrics_path) if lyrics_path else None,
            "channel_docs": CHANNEL_DOCS,
        },
        "channels": {k: v.astype(float) for k, v in ch.items()},
    }
    write_json(out, data, ndigits=4, indent=None)
    return data
