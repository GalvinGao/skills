"""Word-level (and character-level) lyric timing from the vocal stem.

Two ways in, one output format:

    songscope lyrics              Draft without any lyric text: MLX Whisper transcribes the vocal
                            stem with word timestamps -> lyrics/<song>/transcript.json, and
                            writes lyrics/<song>/draft.txt (one sung phrase per line).
    songscope lyrics-align        Forced alignment of lyrics/lyrics.txt (licensed or corrected
                            text, one sung line per line) -> lyrics/<song>/alignment.json.
                            Use this for the real thing; ASR on a synthesized voice makes mistakes.

Each JSON holds lines -> words -> characters with seconds and video frames, the
word's position on the beat grid, and a ``voiced`` flag from the pitch tracker so
hallucinated words in silent passages stand out. Karaoke subtitles (.ass with \\kf
tags) and an .srt are written next to it for checking the sync over the reference MV.

Character times inside a word are interpolated evenly (``chars_interpolated``).
Everything here stays in lyrics/, which git ignores: the text is third-party IP.
"""

from __future__ import annotations

from pathlib import Path

import librosa
import numpy as np

from songscope.beats import grid_position
from songscope.common import frame_of, load_audio, lyrics_dir, read_json, stems_dir, write_json

DEFAULT_MODEL = "mlx-community/whisper-large-v3-mlx"
WORD_PULSE_TAU = 0.08
# A frame counts as sung when the vocal stem is within this range of its loud peak.
VOICED_RANGE_DB = 35.0


def default_vocals(song: Path) -> Path:
    return stems_dir(song) / "vocals_mel_band_roformer" / "vocals.wav"


def _load_model(name: str):
    from stable_whisper.whisper_word_level.mlx_whisper import load_mlx_whisper

    return load_mlx_whisper(name)


def _result_to_lines(result, fps: int, frame_start: int, beats: dict | None, voiced: np.ndarray) -> list[dict]:
    def voiced_share(start: float, end: float) -> float:
        a, b = int(start * fps), max(int(start * fps) + 1, int(np.ceil(end * fps)))
        return float(voiced[a:b].mean()) if a < len(voiced) else 0.0

    lines = []
    for i, seg in enumerate(result.segments):
        words = []
        for w in seg.words:
            text = w.word
            chars = [c for c in text if not c.isspace()]
            span = (w.end - w.start) / max(len(chars), 1)
            entry = {
                "text": text,
                "start": w.start,
                "end": w.end,
                "start_frame": frame_of(w.start, fps, frame_start),
                "end_frame": frame_of(w.end, fps, frame_start),
                "prob": getattr(w, "probability", None),
                "voiced": voiced_share(w.start, w.end),
                "chars": [
                    {"text": c, "start": w.start + j * span, "end": w.start + (j + 1) * span,
                     "start_frame": frame_of(w.start + j * span, fps, frame_start)}
                    for j, c in enumerate(chars)
                ],
            }
            if beats is not None:
                entry["pos"] = grid_position(w.start, beats)
            words.append(entry)
        lines.append({
            "index": i,
            "text": seg.text.strip(),
            "start": seg.start,
            "end": seg.end,
            "start_frame": frame_of(seg.start, fps, frame_start),
            "end_frame": frame_of(seg.end, fps, frame_start),
            "words": words,
        })
    return lines


def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def write_subtitles(lines: list[dict], stem: Path) -> list[Path]:
    """<stem>.ass (karaoke, \\kf per word) and <stem>.srt (one cue per line)."""
    ass = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        "Style: Karaoke,Hiragino Sans,64,&H00BBC539,&H00FFFFFF,&H00202020,&H64000000,1,0,0,0,100,100,0,0,1,3,0,2,60,60,80,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    srt = []
    for n, line in enumerate(lines, 1):
        parts, cursor = [], line["start"]
        for w in line["words"]:
            if w["start"] > cursor + 0.005:  # gap before the word: advance the sweep silently
                parts.append(f"{{\\k{round((w['start'] - cursor) * 100)}}}")
            parts.append(f"{{\\kf{max(1, round((w['end'] - w['start']) * 100))}}}{w['text']}")
            cursor = max(cursor, w["end"])
        ass.append(f"Dialogue: 0,{_ass_time(line['start'])},{_ass_time(line['end'])},Karaoke,,0,0,0,,{''.join(parts)}")
        srt += [str(n), f"{_srt_time(line['start'])} --> {_srt_time(line['end'])}", line["text"], ""]
    out_ass, out_srt = stem.with_suffix(".ass"), stem.with_suffix(".srt")
    out_ass.write_text("\n".join(ass) + "\n")
    out_srt.write_text("\n".join(srt))
    return [out_ass, out_srt]


def _context(analysis_dir: Path, vocals: Path, fps: int) -> tuple[dict | None, np.ndarray]:
    """Beat grid (if analysed) and per-frame vocal activity from the stem's own loudness."""
    beats = read_json(analysis_dir / "beats.json") if (analysis_dir / "beats.json").exists() else None
    y, sr = load_audio(vocals, sr=48000)
    hop = 48000 // fps
    rms = librosa.feature.rms(y=y, frame_length=2 * hop, hop_length=hop)[0]
    db = 20 * np.log10(np.maximum(rms, 1e-9))
    return beats, (db > np.percentile(db, 99) - VOICED_RANGE_DB).astype(float)


def _finish(method: str, model_name: str, vocals: Path, lines: list[dict], out: Path, fps: int, frame_start: int,
            voiced: np.ndarray) -> dict:
    words = [w for line in lines for w in line["words"]]
    covered = np.zeros(len(voiced), dtype=bool)
    for w in words:
        covered[int(w["start"] * fps): int(np.ceil(w["end"] * fps))] = True
    sung = voiced > 0
    shares = [w["voiced"] for w in words]
    data = {
        "method": method,
        "model": model_name,
        "vocals": str(vocals),
        "fps": fps,
        "frame_start": frame_start,
        "chars_interpolated": True,
        "stats": {
            "lines": len(lines),
            "words": len(words),
            "chars": sum(len(w["chars"]) for w in words),
            "words_mostly_unvoiced": int(sum(s < 0.2 for s in shares)),
            "sung_frames_covered": round(float((covered & sung).sum() / max(sung.sum(), 1)), 3),
            "mean_word_prob": float(np.mean([w["prob"] for w in words if w["prob"] is not None])) if words else None,
        },
        "lines": lines,
    }
    write_json(out, data)
    write_subtitles(lines, out)
    return data


def transcribe(song: Path, vocals: Path, analysis_dir: Path, fps: int, frame_start: int = 1,
               model_name: str = DEFAULT_MODEL, language: str = "ja") -> dict:
    beats, voiced = _context(analysis_dir, vocals, fps)
    model = _load_model(model_name)
    # Conditioning on the previous window makes Whisper loop and drop most sung lines
    # (40 words vs 348 on the song this was tuned on); Silero VAD made no difference on the vocal stem.
    result = model.transcribe(str(vocals), language=language, condition_on_previous_text=False,
                              suppress_silence=True, regroup=True, verbose=None)
    lines = _result_to_lines(result, fps, frame_start, beats, voiced)
    out_dir = lyrics_dir(song)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "draft.txt").write_text("\n".join(line["text"] for line in lines) + "\n")
    return _finish("transcribe", model_name, vocals, lines, out_dir / "transcript.json", fps, frame_start, voiced)


def align(song: Path, vocals: Path, lyrics: Path, analysis_dir: Path, fps: int, frame_start: int = 1,
          model_name: str = DEFAULT_MODEL, language: str = "ja", refine: bool = False) -> dict:
    text = lyrics.read_text().strip()
    if not text:
        raise ValueError(f"{lyrics} is empty")
    beats, voiced = _context(analysis_dir, vocals, fps)
    model = _load_model(model_name)
    result = model.align(str(vocals), text, language=language, original_split=True)
    if refine:
        # Iteratively mutes parts of the audio to tighten word boundaries; several times slower.
        model.refine(str(vocals), result)
    lines = _result_to_lines(result, fps, frame_start, beats, voiced)
    out_dir = lyrics_dir(song)
    out_dir.mkdir(parents=True, exist_ok=True)
    return _finish("align", model_name, vocals, lines, out_dir / "alignment.json", fps, frame_start, voiced)


def block_windows(voiced: np.ndarray, fps: int, n_blocks: int, pad: float = 1.5,
                  min_gap: float = 1.2) -> list[tuple[float, float]]:
    """Time windows for n_blocks lyric blocks, split at the longest silent gaps of the vocal.

    Blank lines in lyrics.txt separate blocks (verses, choruses...). Aligning each block in
    its own window keeps one hard passage from dragging the rest of the song off time.
    """
    k = max(1, int(0.3 * fps))
    sung = np.convolve(voiced, np.ones(k) / k, mode="same") > 0.5
    idx = np.nonzero(sung)[0]
    if len(idx) == 0:
        raise ValueError("no vocal activity found")
    first, last = int(idx[0]), int(idx[-1])
    gaps, run_start = [], None
    for i in range(first, last + 1):
        if not sung[i] and run_start is None:
            run_start = i
        elif sung[i] and run_start is not None:
            if (i - run_start) / fps >= min_gap:
                gaps.append((run_start, i))
            run_start = None
    if len(gaps) < n_blocks - 1:
        raise ValueError(f"found {len(gaps)} vocal gaps for {n_blocks} blocks; align without --blocks")
    chosen = sorted(sorted(gaps, key=lambda g: g[1] - g[0], reverse=True)[:n_blocks - 1])
    cuts = [first / fps - pad] + [(a + b) / 2 / fps for a, b in chosen] + [last / fps + pad]
    return [(max(0.0, cuts[i] - (0 if i == 0 else pad)), cuts[i + 1] + (0 if i == n_blocks - 1 else pad))
            for i in range(n_blocks)]


def align_blocks(song: Path, vocals: Path, lyrics: Path, analysis_dir: Path, fps: int, frame_start: int = 1,
                 model_name: str = DEFAULT_MODEL, language: str = "ja",
                 windows: list[tuple[float, float]] | None = None) -> dict:
    """Forced alignment block by block (blocks = paragraphs of lyrics.txt).

    Windows come from the vocal's silent gaps unless given; songs with vocals almost
    everywhere (a song with one real gap) need them passed explicitly.
    """
    import soundfile as sf

    blocks = [b for b in lyrics.read_text().strip().split("\n\n") if b.strip()]
    beats, voiced = _context(analysis_dir, vocals, fps)
    windows = windows or block_windows(voiced, fps, len(blocks))
    if len(windows) != len(blocks):
        raise ValueError(f"{len(windows)} windows for {len(blocks)} lyric blocks")
    y, sr = load_audio(vocals, sr=16000)
    model = _load_model(model_name)
    out_dir = lyrics_dir(song)
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = []
    for n, (block, (a, b)) in enumerate(zip(blocks, windows)):
        clip = out_dir / f"align-block-{n + 1}.wav"
        sf.write(clip, y[int(a * sr):int(b * sr)], sr)
        result = model.align(str(clip), block, language=language, original_split=True)
        result.offset_time(a)
        lines.extend(_result_to_lines(result, fps, frame_start, beats, voiced))
        clip.unlink()
    for i, line in enumerate(lines):
        line["index"] = i
    data = _finish("align-blocks", model_name, vocals, lines, out_dir / "alignment.json", fps, frame_start, voiced)
    data["windows"] = windows
    return data


def best_alignment(song: Path) -> Path | None:
    """The alignment to animate with: forced alignment if present, else the ASR draft."""
    for name in ("alignment.json", "transcript.json"):
        if (lyrics_dir(song) / name).exists():
            return lyrics_dir(song) / name
    return None


def lyric_channels(path: Path, n: int, fps: int) -> dict[str, np.ndarray]:
    """Per-frame lyric curves for features.json: activity, word pulses, line counter/progress."""
    data = read_json(path)
    times = np.arange(n) / fps
    active = np.zeros(n)
    pulse = np.zeros(n)
    line_index = np.zeros(n)
    line_phase = np.zeros(n)
    snap = lambda t: round(t * fps) / fps  # noqa: E731  (peak on the frame nearest the onset)
    for line in data["lines"]:
        start, end = snap(line["start"]), snap(line["end"])
        in_line = (times >= start) & (times < end)
        line_index[in_line] = line["index"] + 1
        line_phase[in_line] = (times[in_line] - start) / max(end - start, 1e-6)
        for w in line["words"]:
            ws = snap(w["start"])
            active[(times >= ws) & (times < snap(w["end"]))] = 1.0
            after = times >= ws
            pulse[after] = np.maximum(pulse[after], np.exp(-(times[after] - ws) / WORD_PULSE_TAU))
    return {"lyric_active": active, "lyric_word_pulse": pulse, "lyric_line": line_index, "lyric_line_phase": line_phase}
