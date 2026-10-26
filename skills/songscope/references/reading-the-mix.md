# Reading mix.json as style evidence

Numbers support a style claim only together with the spectrogram and listening. Compare sections against each other first (drop vs verse), then against references of the claimed genre analyzed the same way.

| Question | Where to look | How to read it |
|---|---|---|
| Sidechain pump | `pump_other.depth_db`, `trough_phase` | A ducked pad dips 3–10 dB just after the kick (trough phase 0.0–0.3) and recovers by the next beat. Under ~1.5 dB, or a trough late in the beat, is no audible pump. Compare drops with verses. |
| Half-time feel | `groove.halftime_ratio`, `snare_16ths` | Above ~1.3: the backbeat sits on beat 3 (future bass, trap). Near or below 1: backbeat on 2 and 4. The 16th list shows fills and off-beat hats (`offbeat_16th_share`). |
| Supersaw / wide chords | `spectrum["mid 400-2k"]`, `["upper-mid 2-5k"].side_to_mid_db`, `stereo_correlation` | Wide detuned chords give side/mid near −3 dB or higher in the mids and a correlation of 0.3–0.7. A mono-ish rock mix sits below −6 dB. |
| Sub weight | `spectrum["sub 20-60"].share_pct`, `side_to_mid_db` | A modern EDM drop often puts 10–20 % of energy below 60 Hz, mono (side/mid below −15 dB). |
| Brightness | `centroid_hz`, `presence`/`air` shares | Kawaii and future bass leads push the centroid and the 5–10 kHz share up; a codec cut above 16 kHz is the file, not the mix. |
| Vocal forwardness | `vocal_to_music_db` | Positive: the vocal leads the stems' "other" energy. Stems leak, so compare sections, not absolute values. |
| Key | `key` | The top candidate and the relative or dominant key often score close; confirm with the bass notes and the chords you hear. |
| Tempo | `bpm` per section | A jump between sections is a tempo change or a second song. Re-run on each part separately when it is a medley. |
| Loudness | `lufs`, `peak_dbfs`, `crest_db` | Crest under ~8 dB is a dense, limited master. Platform rips are normalized: do not compare LUFS across sources. |

A genre signature is a pattern across these, for example future bass: half-time drums, a deep pump on wide detuned chords in the drop, a heavy mono sub, and bright pitched leads or vocal chops. A rock arrangement at the same tempo shows backbeats on 2 and 4, no pump, and guitars filling 150 Hz–5 kHz.
