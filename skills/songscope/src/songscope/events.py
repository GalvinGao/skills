"""Sound events: drum hits, "sparkles", synth stabs, noise FX, risers, downlifters, impacts.

Each layer is a separated stem (see songscope.separate), with fallbacks to coarser stems:

    kick snare toms hihat ride crash   DrumSep stems              one kind per stem
    other                              htdemucs_6s "other"        synths and FX, classified per hit
    piano guitar                       htdemucs_6s                note onsets
    instrumental                       Roformer "other" (no voice) risers, downlifters, impacts

For every hit: onset (5 ms resolution), end, strength, spectral descriptors, a
heuristic kind (sparkle / noise_fx / stab / note / drum name), a timbre cluster
within its layer, AudioSet tags (PANNs sound-event detection), and its position on
the sixteenth-note grid. Each cluster gets an audition WAV in analysis/events/ so
a person can name it, and every kind becomes a per-frame pulse channel
(``evt_<kind>``) in features.json for animation drivers.

The kinds are heuristics tuned on one J-pop/EDM song; treat them as a first pass to review
in the timeline, not ground truth.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from songscope.beats import grid_position
from songscope.common import frame_of, load_audio, stems_dir, write_json

SR = 48000
HOP = 240  # 5 ms
N_FFT = 2048


DRUM_KINDS = ("kick", "snare", "toms", "hihat", "ride", "crash")
# Levels below the stem's loud peak by more than this are bleed, not hits.
GATE_DB = {"drum": 32.0, "tonal": 40.0}
MAX_EVENT_S = 2.0
DECAY_DB = 20.0
# Heuristic kind thresholds for the synth/FX layer.
SPARKLE_CENTROID_HZ = 3000.0
SPARKLE_MIN_MIDI = 84  # C6 and above counts as sparkle-high even when the centroid is lower
SPARKLE_MAX_FLATNESS = 0.15
SPARKLE_MAX_DUR = 0.8
# Flatness of the tuning song's cymbals sits around 0.01; tonal synths stay below 0.003.
NOISE_MIN_FLATNESS = 0.02
STAB_MAX_DUR = 0.35
# A quiet drum hit (this far below its own stem's peak) is bleed when another drum
# stem is this much louder at the same moment.
BLEED_REL_DB = 15.0
BLEED_MARGIN_DB = 12.0
# Impacts: the strongest onsets of the backing track that land on a crash or a section start.
IMPACT_PERCENTILE = 90
# Sweep detection.
SWEEP_SMOOTH_S = 0.4
SWEEP_MIN_S = 0.75
SWEEP_MIN_OCTAVES = 0.75
SWELL_MIN_DB = 10.0
PULSE_TAU = {"kick": 0.08, "snare": 0.10, "toms": 0.12, "hihat": 0.05, "ride": 0.15, "crash": 0.45,
             "sparkle": 0.15, "noise_fx": 0.25, "stab": 0.10, "note": 0.20, "piano": 0.20, "guitar": 0.20,
             "impact": 0.50}
TAG_TRACKS = ("Jingle, tinkle", "Chime", "Bell", "Ding", "Glockenspiel", "Zing", "Sizzle", "Synthesizer",
              "Whoosh, swoosh, swish", "Sound effect", "Cymbal", "Crash cymbal", "Hi-hat", "Clapping",
              "Finger snapping", "Beep, bleep", "Sine wave", "Synthetic singing", "Piano", "Electric piano",
              "Guitar", "Harp")
# Per-hit tags come only from instrument and sound-event classes: AudioSet's genre and
# mood classes ("Techno", "Exciting music"...) win on every frame and say nothing about a hit.
TAG_VOCAB = set(TAG_TRACKS) | {
    "Bass drum", "Snare drum", "Drum machine", "Drum", "Drum kit", "Drum roll", "Rimshot", "Tambourine", "Maraca",
    "Cowbell", "Wood block", "Vibraphone", "Marimba, xylophone", "Steelpan", "Wind chime", "Jingle bell",
    "Tubular bells", "Church bell", "Bicycle bell", "Tuning fork", "Ringtone", "Organ", "Electronic organ",
    "Keyboard (musical)", "Sampler", "Scratching (performance technique)", "String section", "Violin, fiddle",
    "Pizzicato", "Harpsichord", "Accordion", "Brass instrument", "Trumpet", "Flute", "Saxophone", "Clarinet",
    "Plucked string instrument", "Electric guitar", "Bass guitar", "Acoustic guitar", "Strum", "Singing", "Choir",
    "Humming", "Whistling", "Theremin", "Echo", "Reverberation", "Noise", "White noise", "Pink noise", "Static",
    "Hiss", "Buzz", "Click", "Tick", "Clang", "Thump, thud", "Bang", "Squeak", "Chirp tone", "Pulse",
}


def _first(*paths: Path) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def layer_sources(song: Path, allin1_stems: Path) -> dict[str, Path]:
    base = stems_dir(song)
    drumsep, six, four, roformer = (base / "MDX23C-DrumSep-aufr33-jarredou", base / "htdemucs_6s",
                                    base / "htdemucs_ft", base / "vocals_mel_band_roformer")
    src: dict[str, Path] = {}
    for kind in DRUM_KINDS:
        if (drumsep / f"{kind}.wav").exists():
            src[kind] = drumsep / f"{kind}.wav"
    other = _first(six / "other.wav", four / "other.wav", allin1_stems / "other.wav")
    if other:
        src["other"] = other
    for name in ("piano", "guitar"):
        if (six / f"{name}.wav").exists():
            src[name] = six / f"{name}.wav"
    inst = _first(roformer / "other.wav")
    if inst:
        src["instrumental"] = inst
    return src


class _Stem:
    """Frame-level descriptors of one stem at a 5 ms hop."""

    def __init__(self, path: Path):
        self.path = path
        self.y, _ = load_audio(path, sr=SR)
        power = np.abs(librosa.stft(self.y, n_fft=N_FFT, hop_length=HOP)) ** 2
        self.power = power
        self.rms_db = 10 * np.log10(np.maximum(power.sum(axis=0) / N_FFT, 1e-12))
        self.ref_db = float(np.percentile(self.rms_db, 99.5))
        self.centroid = librosa.feature.spectral_centroid(S=np.sqrt(power), sr=SR)[0]
        self.flatness = librosa.feature.spectral_flatness(S=np.sqrt(power))[0]
        self.mfcc = librosa.feature.mfcc(S=librosa.power_to_db(librosa.feature.melspectrogram(S=power, sr=SR, n_mels=96)), n_mfcc=13)
        self.n = power.shape[1]

    def onsets(self, delta: float) -> np.ndarray:
        env = librosa.onset.onset_strength(S=librosa.power_to_db(librosa.feature.melspectrogram(S=self.power, sr=SR, n_mels=128)), sr=SR, hop_length=HOP)
        ms = lambda s: max(1, int(round(s * SR / HOP)))  # noqa: E731
        return librosa.onset.onset_detect(
            onset_envelope=env, sr=SR, hop_length=HOP, units="frames", normalize=True,
            pre_max=ms(0.03), post_max=ms(0.03), pre_avg=ms(0.10), post_avg=ms(0.10), delta=delta, wait=ms(0.03),
        )

    def pitch_midi(self) -> np.ndarray:
        f0 = librosa.yin(self.y, fmin=80, fmax=4000, sr=SR, frame_length=N_FFT, hop_length=HOP)
        return _fit(librosa.hz_to_midi(f0), self.n)


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    return x[:n] if len(x) >= n else np.pad(x, (0, n - len(x)), mode="edge")


def _hits(stem: _Stem, layer: str, kind_group: str, delta: float, pitch: np.ndarray | None) -> list[dict]:
    frames = stem.onsets(delta)
    gate = stem.ref_db - GATE_DB[kind_group]
    look = int(0.05 * SR / HOP)
    out = []
    for i, f in enumerate(frames):
        seg = stem.rms_db[f:f + look]
        if len(seg) == 0 or seg.max() < gate:
            continue
        peak_f = f + int(np.argmax(seg))
        peak_db = float(stem.rms_db[peak_f])
        nxt = frames[i + 1] if i + 1 < len(frames) else stem.n
        limit = min(nxt, f + int(MAX_EVENT_S * SR / HOP), stem.n)
        below = np.nonzero(stem.rms_db[peak_f:limit] < peak_db - DECAY_DB)[0]
        end_f = peak_f + int(below[0]) if len(below) else limit
        w = slice(f, max(f + 1, min(end_f, f + int(0.25 * SR / HOP))))
        weights = stem.power[:, w].sum(axis=0) + 1e-12
        ev = {
            "t": f * HOP / SR,
            "end": end_f * HOP / SR,
            "layer": layer,
            "_abs_db": peak_db,
            "level_db": round(peak_db - stem.ref_db, 1),
            "strength": float(np.clip((peak_db - gate) / GATE_DB[kind_group], 0, 1)),
            "centroid": float(np.average(stem.centroid[w], weights=weights)),
            "flatness": float(np.average(stem.flatness[w], weights=weights)),
            "_mfcc": stem.mfcc[:, w].mean(axis=1),
        }
        ev["dur"] = ev["end"] - ev["t"]
        if pitch is not None:
            p = pitch[w]
            ev["pitch_midi"] = float(np.median(p)) if ev["flatness"] < NOISE_MIN_FLATNESS else None
        out.append(ev)
    return out


def _drop_bleed(events: list[dict], drum_levels: dict[str, np.ndarray]) -> list[dict]:
    """Remove quiet drum-stem hits that are another drum leaking into the stem."""
    look = int(0.03 * SR / HOP) + 1
    keep = []
    for e in events:
        if e["layer"] in drum_levels and e["level_db"] < -BLEED_REL_DB:
            f = int(e["t"] * SR / HOP)
            if any(arr[f:f + look].max() > e["_abs_db"] + BLEED_MARGIN_DB
                   for layer, arr in drum_levels.items() if layer != e["layer"] and f < len(arr)):
                continue
        keep.append(e)
    return keep


def _classify(ev: dict) -> str:
    if ev["layer"] in DRUM_KINDS or ev["layer"] in ("piano", "guitar"):
        return ev["layer"]
    pm = ev.get("pitch_midi")
    tonal = ev["flatness"] <= SPARKLE_MAX_FLATNESS
    high = ev["centroid"] >= SPARKLE_CENTROID_HZ or (pm is not None and pm >= SPARKLE_MIN_MIDI)
    if tonal and high and ev["dur"] <= SPARKLE_MAX_DUR:
        return "sparkle"
    if ev["flatness"] >= NOISE_MIN_FLATNESS:
        return "noise_fx"
    return "stab" if ev["dur"] <= STAB_MAX_DUR else "note"


def _cluster(events: list[dict], layer: str, max_k: int = 8) -> None:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler

    evs = [e for e in events if e["layer"] == layer]
    if len(evs) < 12:
        for e in evs:
            e["cluster"] = f"{layer}_c0"
        return
    X = np.array([np.r_[e["_mfcc"], np.log(e["centroid"] + 1), e["flatness"], np.log(e["dur"] + 0.01)] for e in evs])
    X = StandardScaler().fit_transform(X)
    # Silhouette favours k = 2 here, which is too coarse to audition; a size-based k
    # gives groups small enough to name ("glitter arp", "bell hit"...).
    k = int(np.clip(round(np.sqrt(len(evs) / 10)), 3, max_k))
    km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
    labels, centers = km.labels_, km.cluster_centers_
    for e, lab, x in zip(evs, labels, X):
        e["cluster"] = f"{layer}_c{lab}"
        e["_dist"] = float(np.linalg.norm(x - centers[lab]))


def _sweeps(stem: _Stem, downbeats: np.ndarray) -> list[dict]:
    """Risers (rising brightness + level), downlifters (falling), swells (level ramps)."""
    per_s = SR / HOP
    k = max(1, int(SWEEP_SMOOTH_S * per_s))
    kernel = np.ones(k) / k
    loud = stem.rms_db > stem.ref_db - 45
    cent = np.log2(np.maximum(stem.centroid, 50))
    cent_s = np.convolve(np.where(loud, cent, np.nan_to_num(cent)), kernel, mode="same")
    hi = 10 * np.log10(np.maximum(stem.power[librosa.fft_frequencies(sr=SR, n_fft=N_FFT) >= 2000].sum(axis=0), 1e-12))
    hi_s = np.convolve(hi, kernel, mode="same")
    step = int(0.05 * per_s)
    c, h = cent_s[::step], hi_s[::step]
    out = []

    def runs(sign: int, series: np.ndarray):
        d = np.sign(np.diff(series)) == sign
        i = 0
        while i < len(d):
            if not d[i]:
                i += 1
                continue
            j = i
            misses = 0
            while j + 1 < len(d) and (d[j + 1] or misses < 2):
                misses = misses + 1 if not d[j + 1] else 0
                j += 1
            yield i, j + 1
            i = j + 1

    for sign, kind in ((1, "riser"), (-1, "downlifter")):
        for a, b in runs(sign, c):
            t0, t1 = a * step / per_s, b * step / per_s
            octaves = (c[b] - c[a]) * sign
            level_change = (h[b] - h[a]) * sign
            if t1 - t0 >= SWEEP_MIN_S and octaves >= SWEEP_MIN_OCTAVES and level_change > -3:
                out.append({"kind": kind, "t": t0, "end": t1, "octaves": round(float(octaves), 2),
                            "level_change_db": round(float(level_change), 1)})
    for a, b in runs(1, h):
        t0, t1 = a * step / per_s, b * step / per_s
        rise = h[b] - h[a]
        if 0.5 <= t1 - t0 <= 6 and rise >= SWELL_MIN_DB:
            out.append({"kind": "swell", "t": t0, "end": t1, "octaves": None, "level_change_db": round(float(rise), 1)})

    for s in out:
        edge = s["end"] if s["kind"] in ("riser", "swell") else s["t"]
        if len(downbeats):
            i = int(np.argmin(np.abs(downbeats - edge)))
            s["nearest_downbeat"] = float(downbeats[i])
            s["downbeat_offset_ms"] = round((edge - downbeats[i]) * 1000, 1)
    out.sort(key=lambda s: s["t"])
    return out


def _panns_tags(path: Path) -> tuple[np.ndarray, list[str]]:
    """Framewise AudioSet probabilities (100 fps, 527 classes) from PANNs Cnn14 SED."""
    import torch
    from panns_inference import SoundEventDetection, labels

    y, _ = load_audio(path, sr=32000)
    sed = SoundEventDetection(checkpoint_path=None, device="cpu")
    chunk = 32000 * 30
    parts = []
    with torch.no_grad():
        for s in range(0, len(y), chunk):
            seg = y[s:s + chunk]
            if len(seg) < 32000:
                seg = np.pad(seg, (0, 32000 - len(seg)))
            out = sed.inference(seg[None, :])[0]
            parts.append(out[: int(np.ceil(len(y[s:s + chunk]) / 320))])
    return np.concatenate(parts, axis=0), list(labels)


def _tag_events(events: list[dict], probs: np.ndarray, names: list[str], layers: set[str]) -> None:
    keep = np.array([n in TAG_VOCAB for n in names])
    for e in events:
        if e["layer"] not in layers:
            continue
        a = int(e["t"] * 100)
        b = max(a + 1, int(min(e["end"], e["t"] + 0.5) * 100))
        p = probs[a:b].mean(axis=0) * keep
        top = np.argsort(p)[::-1][:3]
        e["tags"] = [[names[i], round(float(p[i]), 3)] for i in top if p[i] > 0.02]


def _auditions(events: list[dict], sources: dict[str, Path], out_dir: Path, per_cluster: int = 10) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.wav"):
        old.unlink()
    files = {}
    by_cluster: dict[str, list[dict]] = {}
    for e in events:
        if "cluster" in e:
            by_cluster.setdefault(e["cluster"], []).append(e)
    cache: dict[str, np.ndarray] = {}
    gap = np.zeros(int(0.3 * SR), dtype=np.float32)
    for cid, evs in by_cluster.items():
        layer = evs[0]["layer"]
        if layer not in cache:
            cache[layer], _ = load_audio(sources[layer], sr=SR)
        y = cache[layer]
        chosen = sorted(evs, key=lambda e: (e.get("_dist", 0), -e["strength"]))[:per_cluster]
        pieces = []
        for e in sorted(chosen, key=lambda e: e["t"]):
            a, b = int(max(0, e["t"] - 0.02) * SR), int(min(e["end"], e["t"] + 0.6) * SR + 0.05 * SR)
            clip = y[a:b].copy()
            fade = min(len(clip) // 4, int(0.01 * SR))
            if fade:
                clip[:fade] *= np.linspace(0, 1, fade)
                clip[-fade:] *= np.linspace(1, 0, fade)
            pieces += [clip, gap]
        path = out_dir / f"{cid}.wav"
        sf.write(path, np.concatenate(pieces), SR)
        files[cid] = str(path)
    return files


def detect_events(song: Path, beats: dict, cues: dict, allin1_stems: Path, out: Path, tags: bool = True) -> dict:
    sources = layer_sources(song, allin1_stems)
    downbeats = np.array(beats["downbeats"])
    events: list[dict] = []
    sweeps: list[dict] = []
    drum_levels: dict[str, np.ndarray] = {}
    for layer, path in sources.items():
        if layer == "instrumental":
            continue
        stem = _Stem(path)
        group = "drum" if layer in DRUM_KINDS else "tonal"
        if group == "drum":
            drum_levels[layer] = stem.rms_db
        pitch = stem.pitch_midi() if group == "tonal" else None
        for ev in _hits(stem, layer, group, delta=0.08 if group == "drum" else 0.06, pitch=pitch):
            ev["kind"] = _classify(ev)
            events.append(ev)
    events = _drop_bleed(events, drum_levels)

    if "instrumental" in sources:
        stem = _Stem(sources["instrumental"])
        sweeps = _sweeps(stem, downbeats)
        hits = _hits(stem, "instrumental", "drum", delta=0.12, pitch=None)
        crash_t = np.array(sorted(e["t"] for e in events if e["kind"] == "crash"))
        section_t = np.array([sec["start"] for sec in cues["sections"]])
        if hits:
            cut = np.percentile([h["strength"] for h in hits], IMPACT_PERCENTILE)
            for h in hits:
                near_crash = len(crash_t) and np.min(np.abs(crash_t - h["t"])) < 0.04
                near_section = np.min(np.abs(section_t - h["t"])) < 0.08
                if h["strength"] >= cut and (near_crash or near_section):
                    events.append(dict(h, kind="impact"))

    for layer in ("other", "piano", "guitar"):
        _cluster(events, layer)

    tag_tracks = {}
    if tags:
        tag_src = sources.get("instrumental") or sources.get("other")
        if tag_src is not None:
            probs, names = _panns_tags(tag_src)
            _tag_events(events, probs, names, {"other", "piano", "guitar", "impact", "instrumental"})
            for label in TAG_TRACKS:
                if label in names:
                    tag_tracks[label] = np.round(probs[::10, names.index(label)], 3)  # 10 fps

    events.sort(key=lambda e: e["t"])
    auditions = _auditions(events, sources, out.parent / "events")
    fps, fs = cues["fps"], cues["frame_start"]
    clusters: dict[str, dict] = {}
    for i, e in enumerate(events):
        e["id"] = i
        e["frame"] = frame_of(e["t"], fps, fs)
        e["pos"] = grid_position(e["t"], beats)
        for key in ("_mfcc", "_dist", "_abs_db"):
            e.pop(key, None)
        if "cluster" in e:
            c = clusters.setdefault(e["cluster"], {"id": e["cluster"], "layer": e["layer"], "count": 0, "kinds": {},
                                                   "centroids": [], "on_16th": 0})
            c["count"] += 1
            c["kinds"][e["kind"]] = c["kinds"].get(e["kind"], 0) + 1
            c["centroids"].append(e["centroid"])
            c["on_16th"] += abs(e["pos"]["offset_ms"]) < 25
    for c in clusters.values():
        c["median_centroid_hz"] = round(float(np.median(c.pop("centroids"))))
        c["on_grid_share"] = round(c.pop("on_16th") / c["count"], 2)
        c["audition"] = auditions.get(c["id"])
        c["name"] = None  # fill in after listening, e.g. "glitter arp"
    for s in sweeps:
        s["frame"] = frame_of(s["t"], fps, fs)
        s["end_frame"] = frame_of(s["end"], fps, fs)

    counts: dict[str, int] = {}
    for e in events:
        counts[e["kind"]] = counts.get(e["kind"], 0) + 1
    data = {
        "song": str(song),
        "fps": fps,
        "sources": {k: str(v) for k, v in sources.items()},
        "counts": counts,
        "clusters": sorted(clusters.values(), key=lambda c: c["id"]),
        "sweeps": sweeps,
        "events": events,
        "tag_tracks_fps": 10,
        "tag_tracks": tag_tracks,
    }
    write_json(out, data, ndigits=4, indent=None)
    return data


def event_channels(data: dict, n: int, fps: int) -> dict[str, np.ndarray]:
    """Per-frame curves: ``evt_<kind>`` pulses (strength-weighted decays) and sweep ramps."""
    times = np.arange(n) / fps
    ch: dict[str, np.ndarray] = {}
    for e in data["events"]:
        name = f"evt_{e['kind']}"
        arr = ch.setdefault(name, np.zeros(n))
        a = int(round(e["t"] * fps))  # peak on the frame nearest the hit
        if a >= n:
            continue
        tau = PULSE_TAU.get(e["kind"], 0.15)
        b = min(n, a + int(6 * tau * fps) + 1)
        arr[a:b] = np.maximum(arr[a:b], e["strength"] * np.exp(-(times[a:b] - a / fps) / tau))
    for kind in ("riser", "downlifter", "swell"):
        arr = np.zeros(n)
        for s in data["sweeps"]:
            if s["kind"] != kind:
                continue
            m = (times >= s["t"]) & (times < s["end"])
            ramp = (times[m] - s["t"]) / max(s["end"] - s["t"], 1e-6)
            arr[m] = np.maximum(arr[m], 1 - ramp if kind == "downlifter" else ramp)
        ch[f"evt_{kind}"] = arr
    return ch
