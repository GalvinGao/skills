---
name: songscope
description: Analyze a song or audio file so you can "look around" inside it — tempo and beat grid, labelled sections (intro/verse/chorus), stems, drum hits and sound events, vocal pitch, per-frame control curves, spectrogram boards, an interactive timeline, editor markers, and a mix fingerprint (spectrum, stereo width, loudness, sidechain pump, half-time groove, key). Use when the user asks what is in a track, wants a genre/style/production breakdown, a spectrum or frequency analysis, BPM/key/structure, beat-synced cue sheets or video markers, music-video or animation sync data, stem separation, or the offset between two versions of a song. Apple Silicon (MLX) only.
---

# songscope

`songscope` is a CLI that turns one audio file into data you can read and images you can look at. Run it, then read its outputs instead of guessing from the waveform.

## Run

The skill folder is a uv project. Run every command through it; the first run creates `.venv` here and downloads model weights (allin1, beat_this, PANNs; separation models on first `separate`).

```bash
SS="uv run --project ~/.claude/skills/songscope --frozen songscope"
$SS --song path/to/song.wav analyze      # everything; slow model steps are cached
$SS --song path/to/song.wav info         # tempo, grid quality, section table with per-section BPM
$SS --song path/to/song.wav at 1:04.9    # what is at a time; also f1949 (frame) or b34.1 (bar.beat)
```

Requirements: Apple Silicon, `uv`, `ffmpeg` for non-WAV input. Convert video or AAC first: `ffmpeg -i in.mp4 -vn -ac 2 -ar 48000 song.wav`. Name the WAV after the song: the file stem names the workspace.

Outputs go to `songscope/<stem>/` beside the audio (`analysis/`, `stems/`, `lyrics/`), or to `$SONGSCOPE_DIR/<stem>/`. `--song` can also come from `$SONGSCOPE_SONG`; the frame rate from `--fps` or `$SONGSCOPE_FPS` (default 30).

| Command | Does |
|---|---|
| `analyze [--force]` | structure → beats → cues → events → lyrics (skipped without a vocal stem) → features → mix → viz → timeline → markers. `--force` recomputes the cached model steps. |
| `structure` | allin1-mlx: beats, downbeats, labelled sections, and htdemucs stems (vocals/drums/bass/other). |
| `beats` | Cross-checks allin1 against beat_this and fits a constant-tempo grid to the steady region. |
| `separate --preset vocals\|4stem\|6stem\|drumsep` | Cleaner stems. `drumsep` needs `4stem` first. `events` uses whatever exists. |
| `events` | Drum hits, sparkles, stabs, notes, noise FX, risers, downlifters, impacts, timbre clusters with audition WAVs. |
| `mix` | Spectrum, width, loudness, pump, groove and key, per section and for the whole song. |
| `lyrics` / `lyrics-align` | Word timings (install the extra: `uv sync --project <skill> --extra lyrics`). `lyrics-align` reads `lyrics/lyrics.txt` the user supplies. |
| `align ref.wav other.wav` | Time offset between two versions (rip vs master). |

## Look around

Work from coarse to fine; each step tells you where to look next.

1. `info`. Check the grid span and the BPM column. **A grid that ends early or a BPM that changes between sections means a tempo change or a medley** (a single preview often holds two songs). The headline BPM then describes only the steady region.
2. Read `analysis/overview.png` with the Read tool: loudness, mel spectrogram with bar numbers, band curves, stem curves, drum hits, vocal pitch, and chroma, all on one time axis. Then `events_overview.png` and `mix.png`.
3. Open `analysis/mix.json` for numbers per section. See [references/reading-the-mix.md](references/reading-the-mix.md) to turn them into style claims (future bass, half-time, sidechain, supersaw width, sub weight).
4. Zoom in with `at <time>` and with your own crop: `ffmpeg -ss A -to B -i song.wav clip.wav`, then run a step on the clip, or plot it with the project's venv (`uv run --project <skill> python …`).
5. `analysis/timeline.html` is an interactive scrubber for the user (open it locally; it plays `timeline_audio.m4a` beside it).

File formats: [references/outputs.md](references/outputs.md).

## Traps

- **Do not trust a single tracker.** `librosa.beat.beat_track` reported 152 BPM on a 150 BPM track; folding on that grid erased a real pump. Use `beats.json`, and fold on local beats, as `mix` does.
- **Repetitive music fools cross-correlation.** Onset correlation between two renders of a riff picks a match a half-bar off with nearly equal scores. Confirm an alignment with a distinctive event: a held note, a drop, a silence.
- **Platform rips are normalized and re-encoded.** A −6 dBFS true peak at −14 LUFS is the platform, not the master; a shelf above 16 kHz is the codec. Say so before you compare loudness or air.
- **The event kinds are heuristics** tuned on one J-pop/EDM song; review clusters by listening to `analysis/events/*.wav` before you name them.
- **Section labels are guesses** from a model trained on Western pop; a post-chorus riff can come out as "chorus". Check against the spectrogram.
- **Stems and model weights are large.** Delete `songscope/<stem>/stems/` when done if disk matters.

## Rights

Analysis is local. Keep the song, stems, and outputs on the machine unless the user approves a service. Do not print or commit lyric text: report lyric timing as counts and times.
