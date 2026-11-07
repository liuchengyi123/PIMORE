import json

import pytest

from app.prompts import assemble_result, parse_prompt_payload


def test_parse_strips_json_fence():
    text = """```json
{"overview": {"summary": "雨夜街头", "kling": "k", "jimeng": "j"}, "shots": []}
```"""
    data = parse_prompt_payload(text)
    assert data["overview"]["summary"] == "雨夜街头"


def test_parse_rejects_non_json():
    with pytest.raises(ValueError, match="JSON"):
        parse_prompt_payload("不是提示词")


def test_assemble_keeps_detected_times_and_model_copy():
    detected = [(0.0, 2.4), (2.4, 5.0)]
    payload = {
        "overview": {"summary": "一个人走过雨夜", "kling": "总可灵", "jimeng": "总即梦"},
        "shots": [
            {
                "start": 9,
                "end": 9,
                "subject": "黑衣人",
                "action": "快走",
                "scene": "湿漉漉的街道",
                "camera": "跟随",
                "lighting": "霓虹",
                "style": "电影感",
                "kling": "可灵一",
                "jimeng": "即梦一",
            },
            {
                "subject": "黑衣人",
                "action": "回头",
                "scene": "巷口",
                "camera": "固定",
                "lighting": "冷光",
                "style": "写实",
                "kling": "可灵二",
                "jimeng": "即梦二",
            },
        ],
    }
    result = assemble_result(detected, payload)
    assert result["shots"][0]["start"] == 0.0
    assert result["shots"][0]["end"] == 2.4
    assert result["shots"][0]["kling"] == "可灵一"
    assert result["shots"][1]["index"] == 2
    assert result["overview"]["jimeng"] == "总即梦"
    assert result["warnings"] == []


def test_assemble_warns_when_model_skips_a_shot():
    result = assemble_result([(0.0, 1.0), (1.0, 2.0)], {"overview": {}, "shots": [{"kling": "只有一条"}]})
    assert result["shots"][1]["kling"] == ""
    assert result["warnings"]


def test_prompt_payload_round_trip_shape():
    raw = json.dumps({"overview": {"summary": "", "kling": "", "jimeng": ""}, "shots": []})
    assert parse_prompt_payload(raw)["shots"] == []
