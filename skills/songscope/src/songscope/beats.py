"""Beat grid: cross-check two trackers, then fit a constant-tempo grid to the steady part.

A DAW-produced track usually runs at a fixed tempo, so a least-squares grid
(t = t_ref + k * period) is more accurate than any tracker's frame-quantized, jittery
output. Tracker beats are kept only outside the steady region (e.g. a free-tempo intro).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from songscope.common import BEATS_PER_BAR, load_audio, write_json

# Standard beat-tracking evaluation tolerance (mir_eval uses 70 ms).
MATCH_WINDOW = 0.07
# A beat counts as on-grid when within this distance of its grid position.
INLIER_TOL = 0.05
# The grid region starts/ends where at least MIN_SUPPORT of MIN_RUN consecutive grid
# positions (2 bars) have a tracker beat on them.
MIN_RUN = 2 * BEATS_PER_BAR
MIN_SUPPORT = 6
# Share of grid positions inside the region that some tracker must confirm.
MIN_SUPPORTED_FRACTION = 0.8
# Below this 95th-percentile residual the track is treated as constant tempo.
CONSTANT_TEMPO_P95 = 0.025


def track_beat_this(song: Path) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from beat_this.inference import Audio2Beats

    signal, sr = load_audio(song, mono=True)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    try:
        beats, downbeats = Audio2Beats(checkpoint_path="final0", device=device, dbn=False)(signal, sr)
    except (RuntimeError, NotImplementedError):
        # Some torch releases miss MPS kernels that the model needs; CPU is fast enough for one song.
        beats, downbeats = Audio2Beats(checkpoint_path="final0", device="cpu", dbn=False)(signal, sr)
    return np.asarray(beats, dtype=float), np.asarray(downbeats, dtype=float)


def f_measure(ref: np.ndarray, est: np.ndarray, window: float = MATCH_WINDOW) -> float:
    """One-to-one greedy matching F-measure, as in beat-tracking evaluations."""
    ref, est = np.sort(ref), np.sort(est)
    if len(ref) == 0 or len(est) == 0:
        return 0.0
    used = np.zeros(len(est), dtype=bool)
    hits = 0
    for r in ref:
        i = np.searchsorted(est, r)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(est) and not used[j] and abs(est[j] - r) <= window:
                if best is None or abs(est[j] - r) < abs(est[best] - r):
                    best = j
        if best is not None:
            used[best] = True
            hits += 1
    precision, recall = hits / len(est), hits / len(ref)
    return 0.0 if hits == 0 else 2 * precision * recall / (precision + recall)


def _lstsq_grid(times: np.ndarray, t_ref: float, period: float) -> tuple[float, float, np.ndarray, np.ndarray]:
    """One least-squares refinement; returns (t_ref, period, k, residual) for all times."""
    k = np.round((times - t_ref) / period)
    A = np.stack([np.ones(len(times)), k], axis=1)
    (t_ref, period), *_ = np.linalg.lstsq(A, times, rcond=None)
    k = np.round((times - t_ref) / period)
    return float(t_ref), float(period), k, times - (t_ref + k * period)


def fit_grid(tracks: list[np.ndarray], downbeat_tracks: list[np.ndarray], bpm_hint: float, duration: float) -> dict:
    """Fit t = t_ref + k * period to the steady region supported by any of the trackers.

    The first track seeds the fit. A grid position counts as supported when any
    tracker has a beat within INLIER_TOL of it, so one tracker locking onto the
    off-beat for a while (allin1 does this in syncopated intros) does not cut the
    region short. Returns the period, the region as grid indices and times, the
    downbeat phase, and residual statistics that say whether the fit is trustworthy.
    """
    seed = np.sort(np.asarray(tracks[0], dtype=float))
    t_ref, period = float(seed[len(seed) // 2]), 60.0 / bpm_hint  # anchor mid-song
    inliers = np.ones(len(seed), dtype=bool)
    for _ in range(8):
        t_ref, period, _, _ = _lstsq_grid(seed[inliers], t_ref, period)
        residual = seed - (t_ref + np.round((seed - t_ref) / period) * period)
        new_inliers = np.abs(residual) < INLIER_TOL
        if np.array_equal(new_inliers, inliers):
            break
        inliers = new_inliers

    all_beats = np.sort(np.concatenate([np.asarray(t, dtype=float) for t in tracks]))
    k_lo, k_hi = int(np.ceil(-t_ref / period)), int(np.floor((duration - t_ref) / period))
    ks = np.arange(k_lo, k_hi + 1)
    grid_t = t_ref + ks * period
    nearest = np.clip(np.searchsorted(all_beats, grid_t), 1, len(all_beats) - 1)
    dist = np.minimum(np.abs(all_beats[nearest] - grid_t), np.abs(all_beats[nearest - 1] - grid_t))
    supported = dist < INLIER_TOL

    # A region edge needs most of the next (or previous) two bars supported, so a few
    # beats that neither tracker caught in a sparse intro do not end the region.
    window = np.convolve(supported.astype(int), np.ones(MIN_RUN, dtype=int), mode="valid")
    dense = window >= MIN_SUPPORT
    if not dense.any():
        raise ValueError("no steady region of on-grid beats found")
    i0 = int(np.argmax(dense))
    i1 = len(dense) - 1 - int(np.argmax(dense[::-1]))
    first = i0 + int(np.argmax(supported[i0:i0 + MIN_RUN]))
    last = i1 + MIN_RUN - 1 - int(np.argmax(supported[i1:i1 + MIN_RUN][::-1]))
    k_start, k_end = int(ks[first]), int(ks[last])

    # Precision comes from the seed tracker alone (finer time resolution than beat_this's
    # 20 ms frames); the other trackers only vouch for where the grid applies.
    lo, hi = t_ref + (k_start - 0.5) * period, t_ref + (k_end + 0.5) * period
    fit = inliers & (seed > lo) & (seed < hi)
    # t_ref only moves by a few ms here, so k = 0 stays on the same beat and k_start/k_end stay valid.
    t_ref, period, _, residual = _lstsq_grid(seed[fit], t_ref, period)
    res = np.abs(residual)

    downs = np.concatenate([np.asarray(d, dtype=float) for d in downbeat_tracks])
    downs = downs[(downs > lo) & (downs < hi)]
    k_down = np.round((downs - t_ref) / period)
    on = np.abs(downs - (t_ref + k_down * period)) < INLIER_TOL
    phases = k_down[on].astype(int) % BEATS_PER_BAR
    phase = int(np.bincount(phases, minlength=BEATS_PER_BAR).argmax()) if len(phases) else 0
    phase_agreement = float(np.mean(phases == phase)) if len(phases) else 0.0
    in_region = supported[(ks >= k_start) & (ks <= k_end)]

    return {
        "period": float(period),
        "bpm": float(60.0 / period),
        "t_ref": float(t_ref),
        "k_start": k_start,
        "k_end": k_end,
        "start": float(t_ref + k_start * period),
        "end": float(t_ref + k_end * period),
        "downbeat_phase": phase,
        "downbeat_phase_agreement": phase_agreement,
        "region_beats": int(k_end - k_start + 1),
        "supported_fraction": float(in_region.mean()),
        "fit_beats": int(fit.sum()),
        "residual_ms": {
            "median": float(np.median(res) * 1000),
            "p95": float(np.percentile(res, 95) * 1000),
            "max": float(res.max() * 1000),
        },
        "constant_tempo": bool(np.percentile(res, 95) < CONSTANT_TEMPO_P95 and in_region.mean() >= MIN_SUPPORTED_FRACTION),
    }


def grid_beats(grid: dict) -> list[dict]:
    """Beats of the grid region with bar numbers; bar 1 starts at the first downbeat."""
    phase = grid["downbeat_phase"]
    k0 = grid["k_start"]
    first_downbeat_k = k0 + (phase - k0) % BEATS_PER_BAR
    out = []
    for k in range(grid["k_start"], grid["k_end"] + 1):
        rel = k - first_downbeat_k
        out.append({
            "t": grid["t_ref"] + k * grid["period"],
            "bar": rel // BEATS_PER_BAR + 1,  # pickup beats before the first downbeat get bar 0
            "beat": rel % BEATS_PER_BAR + 1,
            "src": "grid",
        })
    return out


def build_beats(song: Path, structure: dict, out: Path) -> dict:
    a_beats = np.asarray(structure["beats"])
    a_down = np.asarray(structure["downbeats"])
    bt_beats, bt_down = track_beat_this(song)

    duration = sf.info(str(song)).duration
    grid = fit_grid([a_beats, bt_beats], [a_down, bt_down], structure["bpm"], duration)
    beats = grid_beats(grid) if grid["constant_tempo"] else []

    if beats:
        # Keep tracker beats outside the grid region (free-tempo intro, ritardando outro...).
        lo, hi = grid["start"] - grid["period"] / 2, grid["end"] + grid["period"] / 2
        positions = structure["beat_positions"]
        before = [{"t": t, "bar": 0, "beat": p, "src": "allin1"} for t, p in zip(a_beats, positions) if t < lo]
        after = [{"t": t, "bar": None, "beat": p, "src": "allin1"} for t, p in zip(a_beats, positions) if t > hi]
        last_bar = beats[-1]["bar"]
        for b in after:
            if b["beat"] == 1:
                last_bar += 1
            b["bar"] = last_bar
        beats = before + beats + after
    else:
        bar = 0
        for t, p in zip(a_beats, structure["beat_positions"]):
            bar += p == 1
            beats.append({"t": float(t), "bar": bar, "beat": p, "src": "allin1"})

    beat_times = np.array([b["t"] for b in beats])
    downbeat_times = np.array([b["t"] for b in beats if b["beat"] == 1 and b["bar"]])

    data = {
        "bpm": grid["bpm"] if grid["constant_tempo"] else structure["bpm"],
        "period": grid["period"],
        "beats_per_bar": BEATS_PER_BAR,
        "grid": grid,
        "checks": {
            "window_ms": MATCH_WINDOW * 1000,
            "allin1_vs_beat_this": {
                "beats_f": f_measure(bt_beats, a_beats),
                "downbeats_f": f_measure(bt_down, a_down),
            },
            "final_vs_beat_this": {
                "beats_f": f_measure(bt_beats, beat_times),
                "downbeats_f": f_measure(bt_down, downbeat_times),
            },
        },
        "beats": beats,
        "downbeats": downbeat_times.tolist(),
        "trackers": {
            "beat_this": {"beats": bt_beats.tolist(), "downbeats": bt_down.tolist()},
        },
    }
    write_json(out, data)
    return data


def grid_position(t: float, beats: dict) -> dict:
    """Nearest sixteenth note on the grid: bar, beat (1-4), sixteenth (0-3), offset in ms."""
    g = beats["grid"]
    step = g["period"] / 4
    k16 = round((t - g["t_ref"]) / step)
    k_beat, sixteenth = divmod(k16, 4)
    first_downbeat_k = g["k_start"] + (g["downbeat_phase"] - g["k_start"]) % beats["beats_per_bar"]
    rel = k_beat - first_downbeat_k
    return {
        "bar": rel // beats["beats_per_bar"] + 1,
        "beat": rel % beats["beats_per_bar"] + 1,
        "sixteenth": int(sixteenth),
        "offset_ms": round((t - (g["t_ref"] + k16 * step)) * 1000, 1),
    }
