import pytest

from app.limits import validate_media

MB = 1024 * 1024


def test_accepts_a_normal_mp4():
    validate_media(size_bytes=20 * MB, duration=12.5, suffix=".mp4")


def test_rejects_oversize():
    with pytest.raises(ValueError, match="100MB"):
        validate_media(size_bytes=100 * MB + 1, duration=10, suffix=".MP4")


def test_rejects_over_60_seconds():
    with pytest.raises(ValueError, match="60"):
        validate_media(size_bytes=MB, duration=60.1, suffix=".mov")


def test_rejects_unknown_suffix():
    with pytest.raises(ValueError, match="mp4"):
        validate_media(size_bytes=MB, duration=3, suffix=".gif")


def test_rejects_empty_duration():
    with pytest.raises(ValueError, match="时长"):
        validate_media(size_bytes=MB, duration=0, suffix=".webm")
