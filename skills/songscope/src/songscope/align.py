"""Find the time offset between two versions of the song.

Use this before switching audio sources (e.g. from the MV rip used for analysis to a
lossless master for the final render): if the offset is not zero, every cue moves.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
from scipy import signal

from songscope.common import load_audio

SR = 22050
HOP = 128  # ~5.8 ms coarse resolution


def estimate_offset(ref: Path, other: Path, max_offset: float = 120.0) -> dict:
    """Return ``offset`` such that ``t_ref = t_other + offset``, plus a confidence ratio."""
    a, _ = load_audio(ref, sr=SR)
    b, _ = load_audio(other, sr=SR)
    oa = librosa.onset.onset_strength(y=a, sr=SR, hop_length=HOP)
    ob = librosa.onset.onset_strength(y=b, sr=SR, hop_length=HOP)
    oa, ob = oa - oa.mean(), ob - ob.mean()

    xc = signal.correlate(oa, ob, mode="full", method="fft")
    lags = signal.correlation_lags(len(oa), len(ob), mode="full")
    keep = np.abs(lags) <= max_offset * SR / HOP
    xc, lags = xc[keep], lags[keep]
    best = int(np.argmax(xc))
    coarse = lags[best] * HOP / SR

    # Confidence: best peak versus the best peak at least 0.5 s away from it.
    far = np.abs(lags - lags[best]) > 0.5 * SR / HOP
    confidence = float(xc[best] / max(xc[far].max(), 1e-9)) if far.any() else float("inf")

    # Refine on raw samples in a +-20 ms window around the coarse lag.
    lag = int(round(coarse * SR))
    win = int(0.02 * SR)
    seg = slice(SR * 30, SR * 60) if len(a) > SR * 70 else slice(0, len(a))
    ref_seg = a[seg]
    scores = []
    for d in range(lag - win, lag + win + 1):
        start = seg.start - d
        if start < 0 or start + len(ref_seg) > len(b):
            scores.append(-np.inf)
            continue
        scores.append(float(np.dot(ref_seg, b[start:start + len(ref_seg)])))
    fine = (lag - win + int(np.argmax(scores))) / SR if np.isfinite(max(scores)) else coarse
    return {"offset": fine, "coarse_offset": coarse, "confidence": confidence}
