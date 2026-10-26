"""Interactive, dependency-free HTML timeline for scrubbing the song and planning shots.

The page plays ``timeline_audio.m4a`` next to it through an <audio> element (works
from file://) and draws everything else from data embedded at build time, including
the word-timed lyrics when they exist. It therefore holds lyric text: keep it local
(analysis/ pages are git-ignored).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from songscope.common import load_audio

PEAKS_PER_SECOND = 100
LANES = ["rms", "bass", "kick", "snare", "hat", "stem_vocals", "vocal_pitch", "onset", "is_chorus",
         "evt_sparkle", "evt_stab", "evt_crash", "evt_impact", "evt_riser", "evt_swell", "lyric_word_pulse"]


def _peaks(song: Path) -> list[float]:
    y, sr = load_audio(song, sr=24000)
    hop = sr // PEAKS_PER_SECOND
    n = len(y) // hop
    frames = y[: n * hop].reshape(n, hop)
    peak = np.abs(frames).max(axis=1)
    return np.round(peak / max(peak.max(), 1e-9), 3).tolist()


def build_timeline(song: Path, cues: dict, features: dict, out: Path, lyrics: dict | None = None) -> Path:
    audio = out.parent / "timeline_audio.m4a"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(song), "-vn", "-c:a", "aac", "-b:a", "192k", str(audio)],
        check=True,
    )
    lanes = {k: np.round(features["channels"][k], 3).tolist() for k in LANES if k in features["channels"]}
    data = {
        "title": Path(song).stem,
        "audio": audio.name,
        "fps": cues["fps"],
        "frameStart": cues["frame_start"],
        "duration": cues["duration"],
        "bpm": cues["bpm"],
        "framesPerBeat": cues["frames_per_beat"],
        "peaksPerSecond": PEAKS_PER_SECOND,
        "peaks": _peaks(song),
        "sections": [{k: s[k] for k in ("name", "label", "start", "end")} for s in cues["sections"]],
        "bars": [[round(b["t"], 4), b["bar"]] for b in cues["bars"]],
        "beats": [[round(b["t"], 4), b["bar"], b["beat"]] for b in cues["beats"]],
        "lanes": lanes,
        "words": [[round(w["start"], 3), round(w["end"], 3), w["text"].strip()]
                  for line in (lyrics or {}).get("lines", []) for w in line["words"]],
        "lyricsSource": (lyrics or {}).get("method"),
    }
    html = TEMPLATE.replace("/*DATA*/null", json.dumps(data, separators=(",", ":")))
    out.write_text(html)
    return out


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Song Timeline</title>
<style>
  :root {
    --bg: #101216; --panel: #181b21; --line: #2a2f38; --text: #e6e8eb; --muted: #8b93a1;
    --accent: #39c5bb; --playhead: #ff5a7a; --marker: #ffd166;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--text); font: 13px/1.4 ui-sans-serif, system-ui, -apple-system, sans-serif; }
  header { display: flex; flex-wrap: wrap; gap: 12px 24px; align-items: baseline; padding: 12px 16px; border-bottom: 1px solid var(--line); }
  header h1 { font-size: 15px; margin: 0; font-weight: 600; }
  .readout { display: flex; flex-wrap: wrap; gap: 6px 18px; font-variant-numeric: tabular-nums; }
  .readout b { color: var(--muted); font-weight: 500; margin-right: 4px; }
  #section-name { color: var(--accent); font-weight: 600; }
  canvas { display: block; width: 100%; }
  #overview { height: 44px; cursor: pointer; border-bottom: 1px solid var(--line); }
  #detail { height: 420px; cursor: crosshair; }
  .bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px 16px; border-top: 1px solid var(--line); background: var(--panel); }
  button { background: #252a33; color: var(--text); border: 1px solid var(--line); border-radius: 6px; padding: 5px 10px; font: inherit; cursor: pointer; }
  button:hover { border-color: var(--accent); }
  label { color: var(--muted); display: inline-flex; gap: 4px; align-items: center; }
  .keys { color: var(--muted); font-size: 12px; }
  kbd { background: #252a33; border: 1px solid var(--line); border-radius: 4px; padding: 0 4px; font: 11px ui-monospace, monospace; color: var(--text); }
  table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
  td, th { text-align: left; padding: 4px 16px; border-bottom: 1px solid var(--line); }
  th { color: var(--muted); font-weight: 500; }
  td input { background: transparent; color: var(--text); border: 1px solid transparent; font: inherit; width: 100%; }
  td input:focus { border-color: var(--line); outline: none; }
  #shots-wrap { max-height: 280px; overflow: auto; }
</style>
</head>
<body>
<header>
  <h1 id="title"></h1>
  <div class="readout">
    <span><b>time</b><span id="r-time"></span></span>
    <span><b>frame</b><span id="r-frame"></span></span>
    <span><b>tc</b><span id="r-tc"></span></span>
    <span><b>bar.beat</b><span id="r-bar"></span></span>
    <span><b>section</b><span id="section-name"></span></span>
    <span><b>tempo</b><span id="r-bpm"></span></span>
  </div>
</header>
<canvas id="overview"></canvas>
<canvas id="detail"></canvas>
<div class="bar">
  <button id="play">Play</button>
  <button id="zoom-in">Zoom +</button>
  <button id="zoom-out">Zoom -</button>
  <span id="lane-toggles"></span>
  <button id="export">Export shots.json</button>
  <button id="clear">Clear shots</button>
  <span class="keys"><kbd>Space</kbd> play <kbd>&larr;</kbd><kbd>&rarr;</kbd> bar <kbd>Shift</kbd>+arrows beat <kbd>[</kbd><kbd>]</kbd> section <kbd>M</kbd> shot at beat <kbd>Shift</kbd>+<kbd>M</kbd> shot at bar <kbd>+</kbd><kbd>-</kbd> zoom, drag to scroll</span>
</div>
<div id="shots-wrap">
  <table><thead><tr><th>#</th><th>name</th><th>time</th><th>frame</th><th>bar.beat</th><th>section</th><th></th></tr></thead><tbody id="shots"></tbody></table>
</div>
<audio id="audio" preload="auto"></audio>
<script>
const D = /*DATA*/null;
const audio = document.getElementById('audio');
audio.src = D.audio;
// Simple HTTP servers (python -m http.server) ignore Range requests, which leaves the
// media element unseekable; a blob URL always seeks. file:// pages keep the direct src.
if (location.protocol.startsWith('http')) {
  fetch(D.audio).then(r => r.blob()).then(b => { audio.src = URL.createObjectURL(b); }).catch(() => {});
}
const COLORS = { intro:'#9aa5b1', verse:'#4f86c6', 'pre-chorus':'#8e6cc9', chorus:'#39b5a4', bridge:'#e0a030', inst:'#c9677f', solo:'#c9677f', break:'#b0b0b0', outro:'#7c8a99', end:'#5a6570' };
const LANE_COLORS = ['#e6e8eb','#4f86c6','#bbbbbb','#ff6b6b','#ffd166','#ff5a9e','#ff5a9e','#39c5bb','#39b5a4','#fff3a3','#9ad0ff','#ffb86b','#ff7b7b','#c3a6ff','#a6ffcb','#39c5bb'];
const laneNames = Object.keys(D.lanes);
const lanesOn = new Set(['rms','kick','evt_sparkle','lyric_word_pulse'].filter(n => laneNames.includes(n)));
const STORE_KEY = 'songscope-shots-' + D.title;
let shots = [];
try { shots = JSON.parse(localStorage.getItem(STORE_KEY) || '[]'); } catch (e) { shots = []; }
let view = { start: 0, span: Math.min(24, D.duration) };
const beatTimes = D.beats.map(b => b[0]);
const barTimes = D.bars.map(b => b[0]);

document.getElementById('title').textContent = D.title;
document.getElementById('r-bpm').textContent = `${D.bpm.toFixed(2)} BPM - ${D.framesPerBeat.toFixed(2)} f/beat @ ${D.fps} fps`;

function frameOf(t) { return D.frameStart + Math.round(t * D.fps); }
function tc(t) { const f = Math.round(t * D.fps), s = Math.floor(f / D.fps), p = n => String(n).padStart(2, '0'); return `${p(Math.floor(s/3600))}:${p(Math.floor(s/60)%60)}:${p(s%60)}:${p(f % D.fps)}`; }
function fmt(t) { const m = Math.floor(t / 60); return `${m}:${(t - m*60).toFixed(3).padStart(6, '0')}`; }
function lastIndex(arr, t) { let lo = 0, hi = arr.length - 1, r = -1; while (lo <= hi) { const m = (lo + hi) >> 1; if (arr[m] <= t + 1e-6) { r = m; lo = m + 1; } else hi = m - 1; } return r; }
function nearestIndex(arr, t) { const i = lastIndex(arr, t); if (i < 0) return 0; if (i >= arr.length - 1) return arr.length - 1; return (t - arr[i] < arr[i+1] - t) ? i : i + 1; }
function sectionAt(t) { for (const s of D.sections) if (t >= s.start && t < s.end) return s; return D.sections[D.sections.length - 1]; }
function barBeatAt(t) { const i = lastIndex(beatTimes, t); if (i < 0) return '-'; const b = D.beats[i]; return `${b[1] ?? '-'}.${b[2]}`; }

const ov = document.getElementById('overview'), dt = document.getElementById('detail');
function fit(c) { const r = c.getBoundingClientRect(), k = devicePixelRatio || 1; c.width = Math.round(r.width * k); c.height = Math.round(r.height * k); const g = c.getContext('2d'); g.setTransform(k, 0, 0, k, 0, 0); return [g, r.width, r.height]; }

function drawOverview() {
  const [g, w, h] = fit(ov);
  g.fillStyle = '#0c0e11'; g.fillRect(0, 0, w, h);
  for (const s of D.sections) { g.fillStyle = COLORS[s.label] || '#666'; g.globalAlpha = 0.55; g.fillRect(s.start / D.duration * w, 0, (s.end - s.start) / D.duration * w, h); }
  g.globalAlpha = 1; g.fillStyle = 'rgba(255,255,255,0.8)';
  const step = D.peaks.length / w;
  for (let x = 0; x < w; x++) { let m = 0; for (let i = Math.floor(x * step); i < Math.floor((x + 1) * step); i++) m = Math.max(m, D.peaks[i] || 0); const hh = m * (h - 8) / 2; g.fillRect(x, h / 2 - hh, 1, hh * 2); }
  g.strokeStyle = '#fff'; g.lineWidth = 1.5; g.strokeRect(view.start / D.duration * w, 1, view.span / D.duration * w, h - 2);
  g.fillStyle = 'var(--playhead)'; g.fillStyle = '#ff5a7a'; g.fillRect(audio.currentTime / D.duration * w - 1, 0, 2, h);
  for (const s of shots) { g.fillStyle = '#ffd166'; g.fillRect(s.t / D.duration * w, 0, 1, h); }
}

function drawDetail() {
  const [g, w, h] = fit(dt);
  const x = t => (t - view.start) / view.span * w;
  const t0 = view.start, t1 = view.start + view.span;
  g.fillStyle = '#101216'; g.fillRect(0, 0, w, h);
  const waveH = 170, lyricTop = waveH + 26, lyricH = D.words.length ? 26 : 0;
  const laneTop = lyricTop + lyricH + 4, laneH = (h - laneTop - 6) / Math.max(1, lanesOn.size);
  for (const s of D.sections) { if (s.end < t0 || s.start > t1) continue; g.fillStyle = COLORS[s.label] || '#666'; g.globalAlpha = 0.14; g.fillRect(x(s.start), 0, x(s.end) - x(s.start), h); g.globalAlpha = 1; g.fillRect(x(s.start), 0, 2, h); g.fillStyle = '#e6e8eb'; g.font = '600 12px system-ui'; g.fillText(s.name, Math.max(x(s.start), 0) + 6, 14); }
  const pxPerBeat = w / view.span * (60 / D.bpm);
  if (pxPerBeat > 6) for (const b of D.beats) { if (b[0] < t0 || b[0] > t1 || b[2] === 1) continue; g.fillStyle = 'rgba(255,255,255,0.12)'; g.fillRect(x(b[0]), 20, 1, waveH); }
  g.font = '11px ui-monospace, monospace';
  for (const [t, bar] of D.bars) { if (t < t0 || t > t1) continue; g.fillStyle = 'rgba(255,255,255,0.35)'; g.fillRect(x(t), 20, 1, h - 20); if (w / view.span * (60 / D.bpm) * 4 > 22 || bar % 4 === 1) { g.fillStyle = '#8b93a1'; g.fillText(String(bar), x(t) + 3, 30); } }
  g.fillStyle = 'rgba(230,232,235,0.85)';
  const mid = 20 + waveH / 2 + 8, pps = D.peaksPerSecond;
  for (let px = 0; px < w; px++) { const a = Math.floor((t0 + px / w * view.span) * pps), b = Math.max(a + 1, Math.floor((t0 + (px + 1) / w * view.span) * pps)); let m = 0; for (let i = a; i < b; i++) m = Math.max(m, D.peaks[i] || 0); const hh = m * (waveH - 30) / 2; g.fillRect(px, mid - hh, 1, hh * 2); }
  if (lyricH) {
    g.save(); g.font = '12px "Hiragino Sans", system-ui, sans-serif';
    g.fillStyle = '#8b93a1'; g.fillText(`lyrics (${D.lyricsSource})`, 6, lyricTop - 3);
    for (const [ws, we, text] of D.words) {
      if (we < t0 || ws > t1) continue;
      const xa = x(ws), xb = Math.max(x(we), xa + 2);
      g.fillStyle = 'rgba(57,197,187,0.28)'; g.fillRect(xa, lyricTop, xb - xa - 1, lyricH);
      g.save(); g.beginPath(); g.rect(xa, lyricTop, xb - xa - 1, lyricH); g.clip();
      g.fillStyle = '#e6e8eb'; g.fillText(text, xa + 2, lyricTop + 17); g.restore();
    }
    g.restore();
  }
  let li = 0;
  for (const name of laneNames) {
    if (!lanesOn.has(name)) continue;
    const top = laneTop + li * laneH, v = D.lanes[name], c = LANE_COLORS[laneNames.indexOf(name) % LANE_COLORS.length];
    g.fillStyle = '#8b93a1'; g.fillText(name, 6, top + 12);
    g.strokeStyle = c; g.lineWidth = 1.2; g.beginPath();
    const f0 = Math.max(0, Math.floor(t0 * D.fps)), f1 = Math.min(v.length - 1, Math.ceil(t1 * D.fps));
    for (let f = f0; f <= f1; f++) { const px = x(f / D.fps), py = top + laneH - 4 - v[f] * (laneH - 18); f === f0 ? g.moveTo(px, py) : g.lineTo(px, py); }
    g.stroke(); li++;
  }
  for (const [i, s] of shots.entries()) { if (s.t < t0 || s.t > t1) continue; g.fillStyle = '#ffd166'; g.fillRect(x(s.t) - 1, 18, 2, h - 18); g.fillText(`${i + 1} ${s.name}`, x(s.t) + 4, 44); }
  const tp = audio.currentTime; g.fillStyle = '#ff5a7a'; g.fillRect(x(tp) - 1, 0, 2, h);
}

function updateReadout() {
  const t = audio.currentTime;
  document.getElementById('r-time').textContent = fmt(t);
  document.getElementById('r-frame').textContent = frameOf(t);
  document.getElementById('r-tc').textContent = tc(t);
  document.getElementById('r-bar').textContent = barBeatAt(t);
  document.getElementById('section-name').textContent = sectionAt(t).name;
}

function follow() { const t = audio.currentTime; if (!audio.paused && (t > view.start + view.span * 0.85 || t < view.start)) view.start = Math.min(Math.max(0, t - view.span * 0.15), Math.max(0, D.duration - view.span)); }
function frame() { follow(); drawOverview(); drawDetail(); updateReadout(); requestAnimationFrame(frame); }

function seek(t) { audio.currentTime = Math.min(Math.max(0, t), D.duration); if (audio.paused) { if (t < view.start || t > view.start + view.span) view.start = Math.max(0, Math.min(t - view.span / 2, D.duration - view.span)); } }
function zoom(k, around) { const c = around ?? audio.currentTime; const span = Math.min(D.duration, Math.max(1.5, view.span * k)); view.start = Math.max(0, Math.min(c - (c - view.start) * span / view.span, D.duration - span)); view.span = span; }

ov.addEventListener('click', e => { const r = ov.getBoundingClientRect(); seek((e.clientX - r.left) / r.width * D.duration); });
let drag = null;
dt.addEventListener('mousedown', e => { drag = { x: e.clientX, start: view.start, moved: false }; });
window.addEventListener('mousemove', e => { if (!drag) return; const r = dt.getBoundingClientRect(); const dx = e.clientX - drag.x; if (Math.abs(dx) > 3) drag.moved = true; view.start = Math.max(0, Math.min(drag.start - dx / r.width * view.span, D.duration - view.span)); });
window.addEventListener('mouseup', e => { if (drag && !drag.moved && e.target === dt) { const r = dt.getBoundingClientRect(); seek(view.start + (e.clientX - r.left) / r.width * view.span); } drag = null; });
dt.addEventListener('wheel', e => { e.preventDefault(); const r = dt.getBoundingClientRect(); if (e.ctrlKey || e.metaKey) zoom(Math.exp(e.deltaY * 0.01), view.start + (e.clientX - r.left) / r.width * view.span); else view.start = Math.max(0, Math.min(view.start + (e.deltaX || e.deltaY) / r.width * view.span, D.duration - view.span)); }, { passive: false });

function jump(list, dir) { const t = audio.currentTime, i = lastIndex(list, t - (dir < 0 ? 0.05 : -0.05)); const j = Math.min(Math.max(dir < 0 ? (list[i] < t - 0.05 ? i : i - 1) : i + 1, 0), list.length - 1); seek(list[j]); }
function addShot(atBar) { const list = atBar ? barTimes : beatTimes; const t = list[nearestIndex(list, audio.currentTime)]; const s = sectionAt(t); shots.push({ name: `${s.name}_shot`, t }); shots.sort((a, b) => a.t - b.t); saveShots(); }
function saveShots() { try { localStorage.setItem(STORE_KEY, JSON.stringify(shots)); } catch (e) {} renderShots(); }
function renderShots() {
  const tb = document.getElementById('shots'); tb.replaceChildren();
  shots.forEach((s, i) => {
    const tr = document.createElement('tr');
    const cell = v => { const td = document.createElement('td'); td.textContent = v; return td; };
    tr.append(cell(i + 1));
    const nameTd = document.createElement('td'), input = document.createElement('input'); input.value = s.name; input.addEventListener('change', () => { s.name = input.value; saveShots(); }); nameTd.append(input); tr.append(nameTd);
    tr.append(cell(fmt(s.t)), cell(frameOf(s.t)), cell(barBeatAt(s.t)), cell(sectionAt(s.t).name));
    const del = document.createElement('td'), btn = document.createElement('button'); btn.textContent = 'x'; btn.addEventListener('click', () => { shots.splice(i, 1); saveShots(); }); del.append(btn); tr.append(del);
    tr.addEventListener('dblclick', () => seek(s.t));
    tb.append(tr);
  });
}
function exportShots() {
  const out = { song: D.title, fps: D.fps, frame_start: D.frameStart, shots: shots.map((s, i) => ({ index: i + 1, name: s.name, t: +s.t.toFixed(4), frame: frameOf(s.t), bar_beat: barBeatAt(s.t), section: sectionAt(s.t).name })) };
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], { type: 'application/json' })); a.download = 'shots.json'; a.click();
}

document.getElementById('play').addEventListener('click', () => audio.paused ? audio.play() : audio.pause());
audio.addEventListener('play', () => document.getElementById('play').textContent = 'Pause');
audio.addEventListener('pause', () => document.getElementById('play').textContent = 'Play');
document.getElementById('zoom-in').addEventListener('click', () => zoom(0.5));
document.getElementById('zoom-out').addEventListener('click', () => zoom(2));
document.getElementById('export').addEventListener('click', exportShots);
document.getElementById('clear').addEventListener('click', () => { if (confirm('Remove all shot markers?')) { shots = []; saveShots(); } });
const toggles = document.getElementById('lane-toggles');
for (const n of laneNames) { const l = document.createElement('label'), c = document.createElement('input'); c.type = 'checkbox'; c.checked = lanesOn.has(n); c.addEventListener('change', () => c.checked ? lanesOn.add(n) : lanesOn.delete(n)); l.append(c, n); toggles.append(l, ' '); }
window.addEventListener('keydown', e => {
  if (e.target.tagName === 'INPUT') return;
  const k = e.key;
  if (k === ' ') { e.preventDefault(); audio.paused ? audio.play() : audio.pause(); }
  else if (k === 'ArrowRight') { e.preventDefault(); jump(e.shiftKey ? beatTimes : barTimes, 1); }
  else if (k === 'ArrowLeft') { e.preventDefault(); jump(e.shiftKey ? beatTimes : barTimes, -1); }
  else if (k === ']') jump(D.sections.map(s => s.start), 1);
  else if (k === '[') jump(D.sections.map(s => s.start), -1);
  else if (k === 'm' || k === 'M') addShot(e.shiftKey);
  else if (k === '+' || k === '=') zoom(0.5);
  else if (k === '-') zoom(2);
});
renderShots();
requestAnimationFrame(frame);
</script>
</body>
</html>
"""
