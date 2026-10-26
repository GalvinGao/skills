# songscope outputs

All under `songscope/<stem>/` (or `$SONGSCOPE_DIR/<stem>/`). Times are seconds from the start of the file. Frame `f` shows `t = (f - 1) / fps`.

## analysis/

| File | Contents |
|---|---|
| `structure.json` | allin1 result: `bpm`, raw `beats`, `downbeats`, `beat_positions`, `sections[{name,label,start,end}]`, `stems_dir` (htdemucs stems). |
| `beats.json` | `bpm`, `period`, `grid{start,end,t_ref,residual_ms,constant_tempo,downbeat_phase_agreement}`, `checks` (F-measures allin1 vs beat_this), `beats[{t,bar,beat,src}]` (`src` is `grid` inside the fitted region, a tracker name outside it), `downbeats`. |
| `cues.json` | Sections snapped to downbeats with frames and timecode; every bar and beat with its frame. Plan cuts against it. |
| `events.json` | `events[]` (onset, end, strength, layer, kind, cluster, AudioSet tags, 16th-grid position), `clusters[]`, `sweeps[]` (risers, downlifters, swells), `counts`. Audition WAVs per cluster in `events/`. |
| `features.json` | Per-frame channels at `fps`, mostly 0..1; `meta.channel_docs` documents each. Channels: `rms`, `sub/bass/lowmid/mid/high/air`, `onset`, `centroid`, `stem_*`, `kick/snare/hat`, `vocal_pitch`, `vocal_midi`, `vocal_voiced`, `chroma_00..11`, `beat_phase`, `bar_phase`, `beat_pulse`, `downbeat_pulse`, counters, `section_*`, `is_chorus`, `evt_<kind>`, `lyric_*`. |
| `mix.json` | `whole` and `sections[]`, each with `bpm`, `lufs`, `peak_dbfs`, `crest_db`, `stereo_correlation`, `centroid_hz`, `spectrum{band:{share_pct,side_to_mid_db}}`, `key` (top 3 with correlation), `pump_other`/`pump_bass{depth_db,trough_phase,peak_phase,profile_db[24]}`, `groove{kick_16ths,snare_16ths,halftime_ratio,offbeat_16th_share}`, `vocal_to_music_db`. `whole.third_octave[]` is the long-term average spectrum. |
| `overview.png` | Board: loudness, mel spectrogram with bar numbers, band curves, stem curves, drum hits, vocal pitch, chroma. |
| `events_overview.png` | Raster of every event by drum piece and timbre cluster. |
| `mix.png` | Third-octave spectrum (mid/side), band share per section, pump profiles, drum onsets per sixteenth. |
| `timeline.html` + `timeline_audio.m4a` | Offline scrubber with lanes and a shot list (browser local storage). Holds lyric text when lyrics exist: keep it local. |
| `markers_resolve.edl`, `markers.csv`, `sections_audacity.txt` | Section markers for DaVinci Resolve, spreadsheets, Audacity. |

## stems/

`allin1_demix/htdemucs/<stem>/{vocals,drums,bass,other}.wav` from `structure`; `<model>/` folders from `separate` (`vocals_mel_band_roformer`, `htdemucs_ft`, `htdemucs_6s`, `MDX23C-DrumSep-…`). `events` prefers the finest stems that exist.

## lyrics/

`lyrics.txt` (user-supplied, one sung line per line, blank line between blocks), `transcript.json` + `draft.txt` (ASR draft), `alignment.json` + `.ass`/`.srt` (forced alignment).
