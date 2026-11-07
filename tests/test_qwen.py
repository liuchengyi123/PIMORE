import json

import httpx

from app.qwen import QwenClient, QwenError


def _payload():
    return {
        "overview": {"summary": "雨夜", "kling": "总可灵", "jimeng": "总即梦"},
        "shots": [
            {
                "subject": "黑衣人",
                "action": "快走",
                "scene": "街道",
                "camera": "跟随",
                "lighting": "霓虹",
                "style": "电影感",
                "kling": "可灵",
                "jimeng": "即梦",
            }
        ],
    }


def test_qwen_sends_frames_without_thinking():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(_payload(), ensure_ascii=False)}}], "usage": {"prompt_tokens": 100, "completion_tokens": 40}},
        )

    client = QwenClient("sk-test", transport=httpx.MockTransport(handler))
    result = client.describe(
        model="qwen3.8-flash",
        shots=[{"index": 1, "start": 0.0, "end": 2.0, "frames": [b"\xff\xd8\xff jpeg"]}],
    )
    assert seen["auth"] == "Bearer sk-test"
    body = seen["body"]
    assert body["model"] == "qwen3.8-flash"
    assert body["enable_thinking"] is False
    content = body["messages"][-1]["content"]
    texts = [part.get("text", "") for part in content if part.get("type") == "text"]
    assert any(part.get("type") == "image_url" for part in content)
    assert any("可灵" in text and "镜头 1" in text for text in texts)
    assert result["shots"][0]["kling"] == "可灵"
    assert result["usage"]["prompt_tokens"] == 100


def test_qwen_rejects_unknown_model():
    client = QwenClient("sk-test", transport=httpx.MockTransport(lambda request: httpx.Response(500)))
    try:
        client.describe(model="qwen3.8-max", shots=[])
    except QwenError as exc:
        assert "模型" in str(exc)
    else:
        raise AssertionError("expected QwenError")


def test_qwen_maps_auth_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "Invalid API-key"}})

    client = QwenClient("sk-bad", transport=httpx.MockTransport(handler))
    try:
        client.describe(model="qwen3.8-flash", shots=[{"index": 1, "start": 0, "end": 1, "frames": [b"\xff\xd8"]}])
    except QwenError as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("expected QwenError")
