"""Timing helpers: the beat grid, frame/timecode maths, grid positions, event curves."""

import numpy as np
import pytest

from songscope.beats import f_measure, fit_grid, grid_beats, grid_position
from songscope.common import frame_of, timecode
from songscope.events import event_channels

PERIOD = 0.4  # 150 BPM


def _track(start: float, n: int, jitter: float = 0.004, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return start + np.arange(n) * PERIOD + rng.uniform(-jitter, jitter, n)


def test_frame_and_timecode():
    assert frame_of(0.0, 30) == 1
    assert frame_of(64.936, 30) == 1949
    assert timecode(64.936, 30) == "00:01:04:28"
    assert timecode(0.0, 30, hour_offset=1) == "01:00:00:00"


def test_fit_grid_recovers_tempo_and_region():
    beats = _track(12.1, 600)
    downbeats = beats[::4]
    grid = fit_grid([beats], [downbeats], bpm_hint=150, duration=260)
    assert grid["constant_tempo"]
    assert grid["bpm"] == pytest.approx(150, abs=0.01)
    assert grid["start"] == pytest.approx(12.1, abs=0.01)
    assert grid["end"] == pytest.approx(12.1 + 599 * PERIOD, abs=0.01)
    assert grid["downbeat_phase_agreement"] == 1.0
    first = next(b for b in grid_beats(grid) if b["bar"] == 1 and b["beat"] == 1)
    assert first["t"] == pytest.approx(12.1, abs=0.01)


def test_fit_grid_survives_a_tracker_on_the_offbeat():
    """One tracker locked 0.18 s late for 60 beats must not cut the grid short."""
    good = _track(12.1, 600)
    shifted = good.copy()
    shifted[5:65] += 0.18
    sparse_second = good[::2]  # a second tracker that only catches every other beat
    grid = fit_grid([shifted, sparse_second], [good[::4]], bpm_hint=150, duration=260)
    assert grid["start"] == pytest.approx(12.1, abs=0.01)
    assert grid["residual_ms"]["p95"] < 10


def test_f_measure():
    ref = np.arange(0, 10, 0.5)
    assert f_measure(ref, ref) == 1.0
    assert f_measure(ref, ref + 0.2) == 0.0
    assert f_measure(ref, ref[::2]) == pytest.approx(2 * 0.5 / 1.5)


def test_grid_position():
    grid = {"period": PERIOD, "t_ref": 12.1, "k_start": 0, "k_end": 599, "downbeat_phase": 0}
    beats = {"grid": grid, "beats_per_bar": 4}
    assert grid_position(12.1, beats) == {"bar": 1, "beat": 1, "sixteenth": 0, "offset_ms": 0.0}
    pos = grid_position(12.1 + 5 * PERIOD + PERIOD / 4 + 0.008, beats)
    assert (pos["bar"], pos["beat"], pos["sixteenth"]) == (2, 2, 1)
    assert pos["offset_ms"] == pytest.approx(8.0, abs=0.1)


def test_event_channels_pulse_and_ramp():
    data = {
        "events": [{"t": 1.0, "kind": "sparkle", "strength": 0.5}],
        "sweeps": [{"kind": "riser", "t": 2.0, "end": 3.0}],
    }
    ch = event_channels(data, n=150, fps=30)
    assert ch["evt_sparkle"][30] == pytest.approx(0.5)
    assert ch["evt_sparkle"][29] == 0.0
    assert 0 < ch["evt_sparkle"][40] < 0.5
    assert ch["evt_riser"][60] == pytest.approx(0.0)
    assert ch["evt_riser"][75] == pytest.approx(0.5)
    assert ch["evt_riser"][95] == 0.0
