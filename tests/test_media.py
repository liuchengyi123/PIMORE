import subprocess
from pathlib import Path

import imageio_ffmpeg
import pytest

from app.media import detect_cuts, extract_frames, probe


def make_cut_video(directory: Path) -> Path:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    target = directory / "cut.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x180:r=25:d=2",
            "-f",
            "lavfi",
            "-i",
            "color=c=white:s=320x180:r=25:d=2",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0,format=yuv420p",
            "-metadata",
            "comment=雨夜街头黑衣人快走",
            str(target),
        ],
        check=True,
        capture_output=True,
    )
    return target


def test_probe_reads_duration_and_comment(tmp_path):
    video = make_cut_video(tmp_path)
    info = probe(video)
    assert info["duration"] == pytest.approx(4.0, abs=0.2)
    assert "雨夜" in info["embedded_prompt"]


def test_detects_the_hard_cut_and_extracts_three_frames(tmp_path):
    video = make_cut_video(tmp_path)
    cuts = detect_cuts(video)
    assert any(1.2 <= cut <= 2.8 for cut in cuts)
    frames = extract_frames(video, [(0.0, 4.0)], tmp_path / "frames")
    assert len(frames) == 1
    assert len(frames[0]) == 3
    assert frames[0][0].stat().st_size > 100
