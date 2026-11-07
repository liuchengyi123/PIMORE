import pytest

from app.shots import build_shots, frame_timestamps


def test_no_cuts_is_one_shot():
    assert build_shots(5.0, []) == [(0.0, 5.0)]


def test_cuts_split_the_timeline():
    assert build_shots(6.0, [2.0, 4.0]) == [(0.0, 2.0), (2.0, 4.0), (4.0, 6.0)]


def test_short_opening_merges_forward():
    assert build_shots(5.0, [0.2]) == [(0.0, 5.0)]


def test_short_ending_merges_backward():
    assert build_shots(5.0, [4.8]) == [(0.0, 5.0)]


def test_short_middle_merges_into_previous():
    assert build_shots(5.0, [2.0, 2.2]) == [(0.0, 2.2), (2.2, 5.0)]


def test_caps_at_twelve_shots():
    cuts = [float(i) for i in range(1, 13)]
    shots = build_shots(13.0, cuts, max_shots=12)
    assert len(shots) == 12
    assert shots[0] == (0.0, 2.0)
    assert shots[-1] == (12.0, 13.0)


def test_ignores_cuts_outside_and_duplicates():
    assert build_shots(4.0, [0.0, 2.0, 2.0, 4.0, -1, 9]) == [(0.0, 2.0), (2.0, 4.0)]


def test_frame_timestamps_sample_start_middle_end():
    times = frame_timestamps(0.0, 5.0)
    assert times == pytest.approx([0.05, 2.5, 4.95])


def test_tiny_shot_uses_one_frame():
    assert frame_timestamps(0.0, 0.1) == pytest.approx([0.05])
