"""``songscope``: command-line entry point for the analysis pipeline.

    songscope --song X analyze         full pipeline (stems, structure, beats, events, curves, mix, charts)
    songscope info                     tempo, grid quality, and the section table
    songscope at 1:04.2 | f1924 | b33  what is at a time / frame / bar
    songscope separate --preset vocals cleaner stems (vocals | 4stem | 6stem | drumsep)
    songscope events                   drum hits, sparkles, stabs, noise FX, risers, impacts
    songscope mix                      spectrum, stereo width, loudness, sidechain pump, groove per section
    songscope lyrics                   ASR draft of word timings from the vocal stem
    songscope lyrics-align             forced alignment of lyrics/lyrics.txt (most accurate)
    songscope align ref.wav other.wav  offset between two versions of the song
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import soundfile as sf

from songscope.common import DEFAULT_FPS, active_song, analysis_dir, frame_of, lyrics_dir, read_json, timecode

STEPS = ["structure", "beats", "cues", "events", "lyrics", "features", "mix", "viz", "timeline", "markers"]
# Model-driven steps whose outputs `songscope analyze` reuses unless --force is given.
SLOW_STEPS = ("structure", "beats", "events", "lyrics")


def _paths(song: Path) -> dict[str, Path]:
    d = analysis_dir(song)
    return {
        "structure": d / "structure.json",
        "beats": d / "beats.json",
        "cues": d / "cues.json",
        "events": d / "events.json",
        "lyrics": lyrics_dir(song) / "transcript.json",
        "features": d / "features.json",
        "viz": d / "overview.png",
        "timeline": d / "timeline.html",
        "markers": d / "markers_resolve.edl",
        "mix": d / "mix.json",
    }


def run_steps(song: Path, steps: list[str], fps: int, stems: Path | None, force: bool) -> None:
    p = _paths(song)
    song = song.resolve()
    duration = sf.info(str(song)).duration
    cache: dict[str, dict] = {}

    def need(name: str) -> dict:
        if name not in cache:
            if not p[name].exists():
                sys.exit(f"missing {p[name]}; run `songscope {name}` or `songscope analyze` first")
            cache[name] = read_json(p[name])
        return cache[name]

    for step in steps:
        if step in SLOW_STEPS and p[step].exists() and not force and len(steps) > 1:
            print(f"[{step}] reusing {p[step].relative_to(Path.cwd()) if p[step].is_relative_to(Path.cwd()) else p[step]}")
            continue
        print(f"[{step}] ...", flush=True)
        if step == "structure":
            from songscope.structure import analyze_structure

            cache["structure"] = analyze_structure(song, p["structure"])
        elif step == "beats":
            from songscope.beats import build_beats

            cache["beats"] = build_beats(song, need("structure"), p["beats"])
        elif step == "cues":
            from songscope.cues import build_cues

            cache["cues"] = build_cues(song, need("structure"), need("beats"), fps, duration, p["cues"])
        elif step == "events":
            from songscope.events import detect_events

            data = detect_events(song, need("beats"), need("cues"), Path(need("structure")["stems_dir"]), p["events"])
            print(f"[events] {sum(data['counts'].values())} hits {data['counts']}, {len(data['sweeps'])} sweeps, "
                  f"{len(data['clusters'])} timbre clusters (auditions in {p['events'].parent / 'events'})")
        elif step == "lyrics":
            from songscope.lyrics import default_vocals, transcribe

            if (lyrics_dir(song) / "alignment.json").exists() and not force:
                print(f"[lyrics] {lyrics_dir(song) / 'alignment.json'} exists (forced alignment); skipping the ASR draft")
                continue
            vocals = default_vocals(song)
            if not vocals.exists():
                # Lyrics are optional: the rest of the pipeline never needs them.
                print(f"[lyrics] skipped: no {vocals} (run `songscope separate --preset vocals` for word timings)")
                continue
            data = transcribe(song, vocals, p["structure"].parent, fps)
            print(f"[lyrics] ASR draft: {data['stats']}")
        elif step == "features":
            from songscope.features import compute_features

            stems_dir = stems or Path(need("structure")["stems_dir"])
            cache["features"] = compute_features(song, need("beats"), need("cues"), stems_dir, fps, p["features"])
        elif step == "mix":
            from songscope.mix import analyze_mix

            stems_dir = stems or Path(need("structure")["stems_dir"])
            cache["mix"] = analyze_mix(song, need("beats"), need("cues"), stems_dir, p["mix"])
        elif step == "viz":
            from songscope.lyrics import best_alignment
            from songscope.viz import render_events, render_overview

            render_overview(song, need("cues"), need("features"), p["viz"])
            if p["events"].exists():
                lyr = best_alignment(song)
                render_events(need("cues"), need("events"), read_json(lyr) if lyr else None,
                              p["viz"].with_name("events_overview.png"))
        elif step == "timeline":
            from songscope.lyrics import best_alignment
            from songscope.timeline import build_timeline

            lyr = best_alignment(song)
            build_timeline(song, need("cues"), need("features"), p["timeline"], read_json(lyr) if lyr else None)
        elif step == "markers":
            from songscope.markers import export_markers

            export_markers(need("cues"), p["markers"].parent)
        print(f"[{step}] done -> {p[step]}")


def cmd_info(song: Path) -> None:
    p = _paths(song)
    beats, cues = read_json(p["beats"]), read_json(p["cues"])
    g = beats["grid"]
    print(f"song      {song}")
    print(f"tempo     {beats['bpm']:.3f} BPM ({'constant grid' if g['constant_tempo'] else 'tracker beats'}), "
          f"grid {g['start']:.3f}s .. {g['end']:.3f}s, residual median {g['residual_ms']['median']:.1f} ms, "
          f"p95 {g['residual_ms']['p95']:.1f} ms")
    c = beats["checks"]
    print(f"checks    allin1 vs beat_this F={c['allin1_vs_beat_this']['beats_f']:.3f} (beats) "
          f"{c['allin1_vs_beat_this']['downbeats_f']:.3f} (downbeats); final grid vs beat_this "
          f"F={c['final_vs_beat_this']['beats_f']:.3f} / {c['final_vs_beat_this']['downbeats_f']:.3f}")
    period = beats["period"]
    print("frames/beat  " + "  ".join(f"{fps}fps={period * fps:.2f}" for fps in (24, 25, 30, 50, 60)))
    print(f"frames    {cues['frame_start']}..{cues['frame_end']} at {cues['fps']} fps ({cues['duration']:.2f}s)\n")
    beat_t = [b["t"] for b in beats["beats"]]
    for s in cues["sections"]:
        inside = [t for t in beat_t if s["start"] <= t < s["end"]]
        gaps = sorted(b - a for a, b in zip(inside, inside[1:]))
        s["_bpm"] = f"{60 / gaps[len(gaps) // 2]:.1f}" if gaps else "-"
    print(f"{'section':<12}{'start':>9}{'frame':>7}  {'timecode':<12}{'bar':>6}{'bars':>6}{'length':>9}{'bpm':>8}"
          f"  {'1st downbeat (bar @ frame)':>26}")
    for s in cues["sections"]:
        first = f"{s['downbeat_bar']} @ {s['downbeat_frame']}" if s.get("downbeat_bar") else "-"
        print(f"{s['name']:<12}{s['start']:>9.3f}{s['start_frame']:>7}  {s['start_tc']:<12}"
              f"{s.get('start_bar', s.get('start_bar_beat', '-'))!s:>6}{s.get('bars', '-')!s:>6}{s['end'] - s['start']:>8.2f}s{s['_bpm']:>8}"
              f"  {first:>26}")


def _parse_when(text: str, cues: dict) -> float:
    fps, fs = cues["fps"], cues["frame_start"]
    if text.startswith("f"):
        return (int(text[1:]) - fs) / fps
    if text.startswith("b"):
        bar, _, beat = text[1:].partition(".")
        for b in cues["beats"]:
            if b["bar"] == int(bar) and b["beat"] == int(beat or 1):
                return b["t"]
        sys.exit(f"bar {text[1:]} not found")
    if ":" in text:
        m, s = text.split(":")
        return int(m) * 60 + float(s)
    return float(text)


def cmd_at(song: Path, when: str) -> None:
    cues = read_json(_paths(song)["cues"])
    t = _parse_when(when, cues)
    fps = cues["fps"]
    # Half a frame of slack: typed times are rounded, and a frame "shows" a beat that
    # lands within it.
    tol = 0.5 / fps
    beat = max((b for b in cues["beats"] if b["t"] <= t + tol), key=lambda b: b["t"], default=None)
    sec = next((s for s in cues["sections"] if s["start"] <= t + tol < s["end"]), cues["sections"][-1])
    print(f"t={t:.3f}s  frame={frame_of(t, fps, cues['frame_start'])}  tc={timecode(t, fps)}  "
          f"bar.beat={'-' if beat is None else f'{beat['bar']}.{beat['beat']}'}  "
          f"section={sec['name']} (+{max(0.0, t - sec['start']):.3f}s, "
          f"{max(0.0, t - sec['start']) / (sec['end'] - sec['start']):.0%})")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="songscope", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--song", type=Path, default=None, help="audio file (default: $SONGSCOPE_SONG); outputs go to songscope/<stem>/ beside it, or $SONGSCOPE_DIR/<stem>/")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name in ["analyze", *STEPS]:
        s = sub.add_parser(name, help="full pipeline" if name == "analyze" else f"run the {name} step")
        s.add_argument("--fps", type=int, default=DEFAULT_FPS)
        s.add_argument("--stems", type=Path, help="stem folder with vocals/drums/bass/other.wav (default: allin1 stems)")
        s.add_argument("--force", action="store_true", help="recompute structure and beats too")

    sub.add_parser("info", help="print tempo, grid quality and sections")
    s = sub.add_parser("at", help="describe a moment: seconds, m:ss.s, f<frame>, or b<bar>[.<beat>]")
    s.add_argument("when")
    s = sub.add_parser("separate", help="stem separation with mlx-audio-separator")
    s.add_argument("--preset", default="vocals", help="vocals | 4stem | 6stem | drumsep | <model filename>")
    s.add_argument("--input", type=Path, help="source audio (default: the song; drumsep: the 4stem drums)")
    s = sub.add_parser("align", help="offset between two versions of the song")
    s.add_argument("ref", type=Path)
    s.add_argument("other", type=Path)
    s = sub.add_parser("lyrics-align", help="forced alignment of <workspace>/lyrics/lyrics.txt to the vocal stem")
    s.add_argument("--lyrics", type=Path, default=None, help="lyric text (default: <workspace>/lyrics/lyrics.txt)")
    s.add_argument("--vocals", type=Path, default=None, help="vocal stem (default: Roformer vocals)")
    s.add_argument("--model", default=None, help="MLX Whisper model repo (default: whisper-large-v3)")
    s.add_argument("--refine", action="store_true", help="tighten word boundaries (several times slower)")
    s.add_argument("--blocks", action="store_true",
                   help="align each blank-line-separated block of lyrics.txt in its own window (more robust)")
    s.add_argument("--windows", default=None,
                   help='explicit block windows in seconds, e.g. "24-52.5,52.5-80" (implies --blocks)')
    s.add_argument("--fps", type=int, default=DEFAULT_FPS)

    args = ap.parse_args(argv)
    song = (args.song or active_song()).resolve()

    if args.cmd == "analyze":
        run_steps(song, STEPS, args.fps, args.stems, args.force)
        print()
        cmd_info(song)
    elif args.cmd in STEPS:
        run_steps(song, [args.cmd], args.fps, args.stems, args.force)
    elif args.cmd == "info":
        cmd_info(song)
    elif args.cmd == "at":
        cmd_at(song, args.when)
    elif args.cmd == "separate":
        from songscope.separate import separate

        print(separate(song, args.preset, args.input))
    elif args.cmd == "align":
        from songscope.align import estimate_offset

        r = estimate_offset(args.ref, args.other)
        print(f"offset {r['offset']:+.4f}s (t_ref = t_other + offset), coarse {r['coarse_offset']:+.4f}s, "
              f"confidence {r['confidence']:.2f} (>1.5 is a clear match)")
    elif args.cmd == "lyrics-align":
        from songscope.lyrics import DEFAULT_MODEL, align, default_vocals

        vocals = args.vocals or default_vocals(song)
        args.lyrics = args.lyrics or lyrics_dir(song) / "lyrics.txt"
        if not args.lyrics.exists():
            sys.exit(f"{args.lyrics} not found: add the lyrics you have the rights to use, one sung line per line "
                     "(draft.txt from `songscope lyrics` is a starting point to correct)")
        if not vocals.exists():
            sys.exit(f"{vocals} not found: run `songscope separate --preset vocals` first, or pass --vocals")
        if args.blocks or args.windows:
            from songscope.lyrics import align_blocks

            windows = ([tuple(float(x) for x in w.split("-")) for w in args.windows.split(",")]
                       if args.windows else None)
            data = align_blocks(song, vocals, args.lyrics, analysis_dir(song), args.fps,
                                model_name=args.model or DEFAULT_MODEL, windows=windows)
            print("block windows (s): " + ", ".join(f"{a:.1f}-{b:.1f}" for a, b in data["windows"]))
        else:
            data = align(song, vocals, args.lyrics, analysis_dir(song), args.fps,
                         model_name=args.model or DEFAULT_MODEL, refine=args.refine)
        print(f"aligned: {data['stats']} -> {lyrics_dir(song) / 'alignment.json'} (+ .ass/.srt); "
              "re-run `songscope features` to update curves")
