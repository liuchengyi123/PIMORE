from fastapi.testclient import TestClient

from app.main import analyze_file, app
from tests.test_media import make_cut_video


class FakeQwen:
    def __init__(self, api_key, transport=None):
        self.api_key = api_key

    def describe(self, model, shots):
        assert self.api_key == "sk-test"
        assert model == "qwen3.8-flash"
        assert shots and shots[0]["frames"]
        return {
            "overview": {"summary": "黑白切换", "kling": "总可灵", "jimeng": "总即梦"},
            "shots": [
                {
                    "subject": "色块",
                    "action": "由黑变白",
                    "scene": "纯色背景",
                    "camera": "固定",
                    "lighting": "均匀",
                    "style": "抽象",
                    "kling": f"可灵镜头{item['index']}",
                    "jimeng": "短画面",
                }
                for item in shots
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 8},
        }


def test_analyze_file_returns_prompts(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.QwenClient", FakeQwen)
    video = make_cut_video(tmp_path)
    result = analyze_file(video, api_key="sk-test", model="qwen3.8-flash")
    assert result["embedded_prompt"] and "雨夜" in result["embedded_prompt"]
    assert result["overview"]["kling"] == "总可灵"
    assert result["shots"][0]["kling"].startswith("可灵镜头")
    assert result["shots"][0]["end"] > result["shots"][0]["start"]
    assert result["usage"]["prompt_tokens"] == 12


def test_http_requires_api_key(tmp_path):
    client = TestClient(app)
    video = tmp_path / "a.mp4"
    video.write_bytes(b"0000")
    response = client.post("/api/analyze", files={"file": ("a.mp4", video.read_bytes(), "video/mp4")})
    assert response.status_code == 401


def test_http_analyze(tmp_path, monkeypatch):
    monkeypatch.setattr("app.main.QwenClient", FakeQwen)
    client = TestClient(app)
    video = make_cut_video(tmp_path)
    response = client.post(
        "/api/analyze",
        files={"file": ("cut.mp4", video.read_bytes(), "video/mp4")},
        data={"model": "qwen3.8-flash"},
        headers={"Authorization": "Bearer sk-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["shots"]
    assert body["overview"]["jimeng"] == "总即梦"
