import json

import httpx
from fastapi.testclient import TestClient

from liveroom.api import BANNER, create_app
from liveroom.llm import SentenceClient
from liveroom.tts import TtsClient


def test_room_speaks_from_the_knowledge_base_without_a_key(tmp_path):
    client = TestClient(create_app(tmp_path))
    state = client.get("/api/state").json()
    assert state["banner"] == BANNER
    assert "人工智能生成" in state["banner"]
    page = client.get("/")
    assert page.status_code == 200
    assert 'id="banner"' in page.text

    saved = client.put(
        "/api/skus/jacket",
        json={"price": "79元", "script": ["改完这一行只要{price}。", "面料是{fabric}。"]},
    )
    assert saved.status_code == 200
    spoken = client.post("/api/speak")
    assert spoken.status_code == 200
    utterance = spoken.json()["utterance"]
    assert utterance["text"] == "改完这一行只要79元。"
    assert utterance["audio_url"] == ""

    client.post("/api/danmaku", json={"user": "小王", "text": "我穿多大"})
    answer = client.post("/api/speak").json()["utterance"]
    assert answer["kind"] == "answer"
    assert "M适合160到170" in answer["text"]
    assert "帽子" not in answer["text"]


def test_unknown_claim_is_rejected_and_switch_changes_sku(tmp_path):
    client = TestClient(create_app(tmp_path))
    bad = client.put("/api/skus/jacket", json={"script": ["颜色是{color}"]})
    assert bad.status_code == 400
    switched = client.post("/api/switch", json={"sku_id": "shirt"})
    assert switched.json()["current"] == "shirt"
    text = client.post("/api/speak").json()["utterance"]["text"]
    assert "129元" in text


def test_rewrite_and_voice_use_the_providers(tmp_path):
    class FakeLlm:
        def __init__(self, key):
            self.key = key

        def rewrite(self, sku, draft, kind):
            assert self.key == "sk-test"
            assert sku["price"] == "199元"
            return "家人们今天只要1元"

    class FakeTts:
        def __init__(self, key):
            pass

        def audio_url(self, text, voice):
            assert voice == "clone-a"
            assert "1元" not in text
            return "https://example.test/a.wav"

    def save_audio(url, dest):
        assert url == "https://example.test/a.wav"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"RIFF")

    client = TestClient(
        create_app(tmp_path, llm_factory=FakeLlm, tts_factory=FakeTts, downloader=save_audio)
    )
    client.put("/api/settings", json={"voice": "clone-a"})
    spoken = client.post("/api/speak", headers={"Authorization": "Bearer sk-test"})
    body = spoken.json()["utterance"]
    assert "199元" in body["text"]
    assert "1元" not in body["text"]
    audio = client.get(body["audio_url"])
    assert audio.status_code == 200
    assert audio.content == b"RIFF"


def test_sentence_client_sends_facts_and_tts_reads_the_audio_url():
    seen = {}

    def chat(request: httpx.Request) -> httpx.Response:
        seen["chat"] = json.loads(request.content.decode())
        seen["auth"] = request.headers["authorization"]
        return httpx.Response(200, json={"choices": [{"message": {"content": "今天这件还是199元。"}}]})

    def speech(request: httpx.Request) -> httpx.Response:
        seen["speech"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"output": {"audio": {"url": "https://example.test/a.wav"}}})

    sku = {
        "name": "棒球夹克",
        "price": "199元",
        "sizes": "M",
        "fabric": "棉",
        "facts": [],
        "banned": ["全网最低"],
    }
    line = SentenceClient("sk-test", transport=httpx.MockTransport(chat)).rewrite(sku, "草稿", "sell")
    assert line == "今天这件还是199元。"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["chat"]["model"] == "qwen-flash"
    assert seen["chat"]["enable_thinking"] is False
    assert "199元" in seen["chat"]["messages"][1]["content"]
    url = TtsClient("sk-test", transport=httpx.MockTransport(speech)).audio_url("今天这件还是199元。", "clone-a")
    assert url == "https://example.test/a.wav"
    assert seen["speech"]["model"] == "qwen3-tts-flash"
    assert seen["speech"]["input"]["voice"] == "clone-a"
    assert seen["speech"]["input"]["language_type"] == "Chinese"
