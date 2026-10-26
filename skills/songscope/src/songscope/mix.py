"""Mix and production fingerprint: spectrum, stereo width, loudness, sidechain pump, groove, key.

Everything is measured per section (from cues.json) and for the whole song, so a style
claim ("future bass", "half-time", "wide supersaws") can be checked against numbers:

    spectrum   1/3-octave long-term average spectrum of mid and side, and the energy share
               and side/mid ratio of eight named bands
    loudness   integrated LUFS (BS.1770 via pyloudnorm), sample peak, crest factor
    pump       level of the "other" and "bass" stems across one beat, folded over every
               beat of the section; a sidechain-ducked pad dips right after the kick and
               recovers before the next beat
    groove     kick (30-120 Hz) and snare/clap (1.5-6 kHz) onset strength of the drum stem
               on each sixteenth of the bar; half-time puts the backbeat on beat 3 only
    harmony    Krumhansl-Schmuckler key estimate from the chroma
    tempo      median beat interval inside the section, from the beats themselves, so a
               medley or a tempo change shows up instead of being averaged away

Phases are taken between consecutive beats (and consecutive downbeats for the groove),
never from one global grid, for the same reason. A platform rip is often normalized and
re-encoded: treat loudness and the top octave as properties of the file, not the master.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from scipy import signal

from songscope.common import load_audio, write_json

SR = 44100
HOP = 256
BANDS = {
    "sub 20-60": (20, 60), "bass 60-150": (60, 150), "low-mid 150-400": (150, 400), "mid 400-2k": (400, 2000),
    "upper-mid 2-5k": (2000, 5000), "presence 5-10k": (5000, 10000), "air 10-16k": (10000, 16000), "top 16k+": (16000, SR / 2),
}
PUMP_BINS = 24
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Krumhansl-Kessler key profiles.
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _db(x: float) -> float:
    return float(10 * np.log10(max(x, 1e-20)))


def _band_envelope(y: np.ndarray, lo: float, hi: float) -> np.ndarray:
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=2048)
    return np.sqrt((S[(f >= lo) & (f < hi)] ** 2).sum(0))


def _key(chroma: np.ndarray) -> list[tuple[str, float]]:
    prof = chroma.mean(1)
    scores = [(float(np.corrcoef(np.roll(MAJOR, k), prof)[0, 1]), f"{NOTE_NAMES[k]} major") for k in range(12)]
    scores += [(float(np.corrcoef(np.roll(MINOR, k), prof)[0, 1]), f"{NOTE_NAMES[k]} minor") for k in range(12)]
    return [(name, round(score, 3)) for score, name in sorted(scores, reverse=True)[:3]]


def _spectrum(mid: np.ndarray, side: np.ndarray) -> dict:
    f, pm = signal.welch(mid, SR, nperseg=8192)
    _, ps = signal.welch(side, SR, nperseg=8192)
    total = pm.sum() + ps.sum()
    bands = {}
    for name, (lo, hi) in BANDS.items():
        m = (f >= lo) & (f < hi)
        bands[name] = {"share_pct": 100 * (pm[m].sum() + ps[m].sum()) / total,
                       "side_to_mid_db": _db(ps[m].sum()) - _db(pm[m].sum())}
    thirds = []
    for c in 1000 * 2 ** (np.arange(-17, 14) / 3):
        m = (f >= c / 2 ** (1 / 6)) & (f < c * 2 ** (1 / 6))
        if c < SR / 2 and m.any():
            thirds.append({"hz": float(c), "mid_db": _db(pm[m].sum()), "side_db": _db(ps[m].sum())})
    ref = max(b["mid_db"] for b in thirds)
    for b in thirds:
        b["mid_db"] -= ref
        b["side_db"] -= ref
    return {"bands": bands, "third_octave": thirds}


def _fold_beats(env: np.ndarray, t: np.ndarray, beats: np.ndarray) -> list[float] | None:
    """Median level per phase bin across one beat, in dB below the loudest bin."""
    rows = []
    for b0, b1 in zip(beats, beats[1:]):
        m = (t >= b0) & (t < b1)
        if m.sum() < PUMP_BINS:
            continue
        ph = ((t[m] - b0) / (b1 - b0) * PUMP_BINS).astype(int).clip(0, PUMP_BINS - 1)
        rows.append([np.median(env[m][ph == k]) if (ph == k).any() else np.nan for k in range(PUMP_BINS)])
    if len(rows) < 4:
        return None
    prof = np.nanmedian(np.array(rows), axis=0)
    return (20 * np.log10(prof / prof.max() + 1e-12)).tolist()


def _fold_bars(onset: np.ndarray, t: np.ndarray, downbeats: np.ndarray) -> list[float] | None:
    """Mean peak onset strength on each sixteenth of the bar."""
    acc, n = np.zeros(16), 0
    for b0, b1 in zip(downbeats, downbeats[1:]):
        m = (t >= b0) & (t < b1)
        if m.sum() < 16:
            continue
        ph = ((t[m] - b0) / (b1 - b0) * 16).astype(int).clip(0, 15)
        acc += [onset[m][ph == k].max() if (ph == k).any() else 0.0 for k in range(16)]
        n += 1
    return (acc / n).tolist() if n >= 2 else None


def _pump_summary(prof: list[float] | None) -> dict | None:
    if prof is None:
        return None
    p = np.array(prof)
    return {"depth_db": float(-p.min()), "trough_phase": float(p.argmin() / PUMP_BINS),
            "peak_phase": float(p.argmax() / PUMP_BINS), "profile_db": prof}


def _groove_summary(kick: list[float] | None, snare: list[float] | None) -> dict | None:
    if kick is None or snare is None:
        return None
    s = np.array(snare)
    backbeat_2_4, backbeat_3 = (s[4] + s[12]) / 2, s[8]
    return {
        "kick_16ths": kick, "snare_16ths": snare,
        # Above 1 the snare lands on 3 more than on 2 and 4: a half-time feel.
        "halftime_ratio": float(backbeat_3 / max(backbeat_2_4, 1e-9)),
        "offbeat_16th_share": float(s[[1, 3, 5, 7, 9, 11, 13, 15]].sum() / max(s.sum(), 1e-9)),
    }


def analyze_mix(song: Path, beats: dict, cues: dict, stems_dir: Path, out: Path) -> dict:
    import pyloudnorm

    stereo, _ = load_audio(song, sr=SR, mono=False)
    if stereo.shape[1] == 1:
        stereo = np.repeat(stereo, 2, axis=1)
    left, right = stereo[:, 0], stereo[:, 1]
    mid, side = (left + right) / 2, (left - right) / 2
    meter = pyloudnorm.Meter(SR)

    stems = {}
    for name in ("drums", "bass", "other", "vocals"):
        path = Path(stems_dir) / f"{name}.wav"
        if path.exists():
            stems[name] = load_audio(path, sr=SR)[0]
    t = librosa.frames_to_time(np.arange(len(mid) // HOP + 1), sr=SR, hop_length=HOP)

    def env(name: str, lo: float, hi: float) -> np.ndarray | None:
        return _band_envelope(stems[name], lo, hi)[: len(t)] if name in stems else None

    def onset(e: np.ndarray | None) -> np.ndarray | None:
        if e is None:
            return None
        d = np.maximum(np.diff(e, prepend=e[0]), 0)
        return d / (d.max() + 1e-12)

    envs = {"other": env("other", 200, 8000), "bass": env("bass", 30, 250), "vocals": env("vocals", 200, 8000)}
    kick_on, snare_on = onset(env("drums", 30, 120)), onset(env("drums", 1500, 6000))
    t = t[: min(len(e) for e in envs.values() if e is not None)] if any(e is not None for e in envs.values()) else t
    beat_t = np.array([b["t"] for b in beats["beats"]])
    down_t = np.array(beats["downbeats"])
    chroma = librosa.feature.chroma_cqt(y=librosa.resample(mid, orig_sr=SR, target_sr=22050), sr=22050, hop_length=2048)
    chroma_t = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=22050, hop_length=2048)
    centroid = librosa.feature.spectral_centroid(y=mid, sr=SR, hop_length=2048)[0]
    centroid_t = librosa.frames_to_time(np.arange(len(centroid)), sr=SR, hop_length=2048)

    def measure(a: float, z: float) -> dict:
        i0, i1 = int(a * SR), int(z * SR)
        seg = stereo[i0:i1]
        r: dict = {"start": a, "end": z}
        if len(seg) < SR:
            return r
        inside = beat_t[(beat_t >= a) & (beat_t < z)]
        r["bpm"] = float(60 / np.median(np.diff(inside))) if len(inside) > 2 else None
        try:
            r["lufs"] = float(meter.integrated_loudness(seg))
        except ValueError:
            r["lufs"] = None
        m = mid[i0:i1]
        r["peak_dbfs"] = float(20 * np.log10(np.abs(seg).max() + 1e-12))
        r["crest_db"] = float(20 * np.log10(np.abs(m).max() / (np.sqrt((m ** 2).mean()) + 1e-12) + 1e-12))
        r["stereo_correlation"] = float(np.corrcoef(left[i0:i1], right[i0:i1])[0, 1])
        r["centroid_hz"] = float(np.median(centroid[(centroid_t >= a) & (centroid_t < z)]))
        r["spectrum"] = _spectrum(m, side[i0:i1])["bands"]
        r["key"] = _key(chroma[:, (chroma_t >= a) & (chroma_t < z)])
        mt = (t >= a) & (t < z)
        r["pump_other"] = _pump_summary(_fold_beats(envs["other"], t, inside)) if envs["other"] is not None else None
        r["pump_bass"] = _pump_summary(_fold_beats(envs["bass"], t, inside)) if envs["bass"] is not None else None
        downs = down_t[(down_t >= a - 0.01) & (down_t < z)]
        r["groove"] = _groove_summary(_fold_bars(kick_on, t, downs), _fold_bars(snare_on, t, downs)) if kick_on is not None else None
        if envs["vocals"] is not None and envs["other"] is not None and mt.any():
            r["vocal_to_music_db"] = float(20 * np.log10(np.median(envs["vocals"][mt]) / (np.median(envs["other"][mt]) + 1e-12) + 1e-12))
        return r

    duration = len(mid) / SR
    whole = measure(0.0, duration)
    whole["third_octave"] = _spectrum(mid, side)["third_octave"]
    data = {
        "song": str(song),
        "stems_dir": str(stems_dir),
        "whole": whole,
        "sections": [{"name": s["name"], "label": s["label"], **measure(s["start"], s["end"])} for s in cues["sections"]],
    }
    write_json(out, data)
    render_mix(data, out.with_name("mix.png"))
    return data


def render_mix(data: dict, out: Path) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    secs = [s for s in data["sections"] if s.get("spectrum")]
    fig, ax = plt.subplots(2, 2, figsize=(16, 9))
    third = data["whole"]["third_octave"]
    ax[0, 0].semilogx([b["hz"] for b in third], [b["mid_db"] for b in third], "o-", label="mid")
    ax[0, 0].semilogx([b["hz"] for b in third], [b["side_db"] for b in third], "o-", label="side")
    ax[0, 0].set_title("Long-term average spectrum, 1/3 octave (dB re loudest mid band)")
    ax[0, 0].legend()
    ax[0, 0].grid(alpha=0.3, which="both")

    names = list(BANDS)
    bottom = np.zeros(len(secs))
    for i, band in enumerate(names):
        vals = np.array([s["spectrum"][band]["share_pct"] for s in secs])
        ax[0, 1].bar(range(len(secs)), vals, bottom=bottom, label=band, color=plt.cm.viridis(i / len(names)))
        bottom += vals
    ax[0, 1].set_xticks(range(len(secs)), [s["name"] for s in secs], rotation=45, ha="right", fontsize=8)
    ax[0, 1].set_title("Energy share per band and section (%)")
    ax[0, 1].legend(fontsize=7, ncol=2)

    phase = np.arange(PUMP_BINS) / PUMP_BINS
    for s in secs:
        if s.get("pump_other"):
            ax[1, 0].plot(phase, s["pump_other"]["profile_db"], lw=1, label=f"{s['name']} ({s['pump_other']['depth_db']:.1f} dB)")
    ax[1, 0].set_title('Sidechain pump: "other" stem level across one beat')
    ax[1, 0].set_xlabel("beat phase")
    ax[1, 0].legend(fontsize=6, ncol=2)
    ax[1, 0].grid(alpha=0.3)

    grooves = [s for s in secs if s.get("groove")]
    if grooves:
        k = np.mean([g["groove"]["kick_16ths"] for g in grooves], axis=0)
        sn = np.mean([g["groove"]["snare_16ths"] for g in grooves], axis=0)
        x = np.arange(16)
        ax[1, 1].bar(x - 0.2, k, 0.4, label="kick 30-120 Hz")
        ax[1, 1].bar(x + 0.2, sn, 0.4, label="snare/clap 1.5-6 kHz")
        ax[1, 1].set_xticks(x, [f"{i // 4 + 1}.{i % 4 + 1}" for i in x], fontsize=7)
        ax[1, 1].legend()
    ax[1, 1].set_title("Drum onsets per sixteenth (mean over sections)")
    plt.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=110)
    plt.close(fig)
    return out
