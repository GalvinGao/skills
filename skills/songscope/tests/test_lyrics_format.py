"""Lyric output formats, with placeholder text (never real lyrics in the repo)."""

from types import SimpleNamespace

import numpy as np

from songscope.lyrics import _result_to_lines, write_subtitles


def _result():
    words = [SimpleNamespace(word="ab", start=1.0, end=1.5, probability=0.9),
             SimpleNamespace(word=" cd", start=1.6, end=2.0, probability=0.8)]
    return SimpleNamespace(segments=[SimpleNamespace(text="ab cd", start=1.0, end=2.0, words=words)])


def test_lines_words_chars_and_voicing():
    voiced = np.zeros(90)
    voiced[30:45] = 1  # 1.0 s .. 1.5 s sung
    lines = _result_to_lines(_result(), fps=30, frame_start=1, beats=None, voiced=voiced)
    assert len(lines) == 1 and lines[0]["start_frame"] == 31
    w0, w1 = lines[0]["words"]
    assert [c["text"] for c in w0["chars"]] == ["a", "b"]
    assert w0["chars"][1]["start"] == 1.25  # interpolated inside the word
    assert w0["voiced"] == 1.0 and w1["voiced"] == 0.0


def test_karaoke_subtitles(tmp_path):
    lines = _result_to_lines(_result(), fps=30, frame_start=1, beats=None, voiced=np.ones(90))
    ass, srt = write_subtitles(lines, tmp_path / "t.json")
    text = ass.read_text()
    assert "Dialogue: 0,0:00:01.00,0:00:02.00,Karaoke" in text
    assert "{\\kf50}ab" in text and "{\\k10}" in text and "{\\kf40} cd" in text
    assert srt.read_text().startswith("1\n00:00:01,000 --> 00:00:02,000\nab cd")
