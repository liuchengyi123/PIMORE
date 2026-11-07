import io
import subprocess
import time
import wave
from pathlib import Path

import imageio_ffmpeg
import pytest
from fastapi.testclient import TestClient

from liveroom.broadcast import ffmpeg_args, join_rtmp, redact
from liveroom.labels import BANNER
from liveroom.voice import wav_to_pcm


def _wav(seconds: float = 0.05) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x00" * int(24000 * seconds))
    return buffer.getvalue()


def test_rtmp_address_joins_the_key_and_rejects_a_web_address():
    assert join_rtmp("rtmp://push.example/live", "room-1") == "rtmp://push.example/live/room-1"
    assert join_rtmp("rtmp://push.example/live/room-1", "") == "rtmp://push.example/live/room-1"
    with pytest.raises(ValueError):
        join_rtmp("https://push.example/live", "room-1")
    assert "room-1" not in redact("failed rtmp://push.example/live/room-1", "rtmp://push.example/live/room-1")


def test_ffmpeg_command_keeps_the_banner_and_the_address_as_one_argument(tmp_path):
    caption = tmp_path / "caption.txt"
    caption.write_text("你好\n", encoding="utf-8")
    font = Path(r"C:\Windows\Fonts\simhei.ttf")
    args = ffmpeg_args("ffmpeg", tmp_path / "a.mp4", "rtmp://push.example/live/room-1", caption, font, BANNER)
    assert args[0] == "ffmpeg"
    assert args[-1] == "rtmp://push.example/live/room-1"
    assert "pipe:0" in args
    assert any("人工智能生成" in item for item in args)
    assert isinstance(args, list)


def test_wav_becomes_mono_pcm_at_the_stream_rate():
    pcm = wav_to_pcm(_wav(0.1))
    assert len(pcm) == 24000 * 2 // 10


class FakeCast:
    def __init__(self):
        self.running = False
        self.error = ""
        self.url = ""
        self.captions = []
        self.chunks = []

    def start(self, video, url, banner):
        assert "人工智能生成" in banner
        self.url = url
        self.running = True

    def stop(self):
        self.running = False

    def set_caption(self, text):
        self.captions.append(text)

    def enqueue(self, pcm):
        self.chunks.append(pcm)


def test_broadcast_speaks_then_answers_without_leaking_the_key(tmp_path):
    from liveroom.api import create_app

    cast = FakeCast()
    client = TestClient(create_app(tmp_path, broadcaster=cast, speaker=lambda text: _wav()))
    refused = client.post("/api/broadcast/start", json={"server": "https://nope", "stream_key": "secret"})
    assert refused.status_code == 400
    missing = client.post("/api/broadcast/start", json={"server": "rtmp://push.example/live", "stream_key": "secret"})
    assert missing.status_code == 400
    uploaded = client.post("/api/skus/jacket/video", files={"file": ("jacket.mp4", b"video", "video/mp4")})
    assert uploaded.status_code == 200
    started = client.post(
        "/api/broadcast/start",
        json={"server": "rtmp://push.example/live", "stream_key": "secret", "api_key": "sk-test"},
    )
    assert started.status_code == 200
    assert "secret" not in started.text
    assert "sk-test" not in started.text
    assert started.json()["live"]["on"] is True
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not any("199元" in item for item in cast.captions):
        time.sleep(0.05)
    assert any("199元" in item for item in cast.captions)
    client.post("/api/danmaku", json={"user": "小王", "text": "我穿多大"})
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not any("尺码" in item for item in cast.captions):
        time.sleep(0.05)
    assert any("尺码" in item for item in cast.captions)
    stopped = client.post("/api/broadcast/stop")
    assert stopped.json()["live"]["on"] is False


def test_ffmpeg_writes_a_second_of_labeled_video(tmp_path):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    font = Path(r"C:\Windows\Fonts\simhei.ttf")
    if not font.is_file():
        pytest.skip("没有黑体")
    video = tmp_path / "stand.mp4"
    made = subprocess.run(
        [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=black:s=320x240:d=1", str(video)],
        check=False,
        capture_output=True,
        timeout=20,
    )
    assert made.returncode == 0, made.stderr.decode("utf-8", "replace")
    caption = tmp_path / "caption.txt"
    caption.write_text("这件今天199元\n", encoding="utf-8")
    out = tmp_path / "out.flv"
    args = ffmpeg_args(ffmpeg, video, str(out), caption, font, BANNER)
    args = args[:-1] + ["-t", "1", str(out)]
    sent = subprocess.run(args, input=b"\x00\x00" * 24000, check=False, capture_output=True, timeout=30)
    assert sent.returncode == 0, sent.stderr.decode("utf-8", "replace")[-500:]
    assert out.stat().st_size > 1000
