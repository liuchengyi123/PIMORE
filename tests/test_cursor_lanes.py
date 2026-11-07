import httpx

from shop.writer import _FollowGate, ai_pair, configure_cursor_lanes, cursor_product


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("bad", request=None, response=self)

    def json(self):
        return self._payload


def _install(monkeypatch):
    calls = []
    agents = {"n": 0}

    def post(url, headers=None, json=None, timeout=None):
        calls.append(("POST", url))
        if url.endswith("/v1/agents"):
            agents["n"] += 1
            agent = f"bc-{agents['n']}"
            return _Response({"agent": {"id": agent}, "run": {"id": f"run-{agent}"}}, 201)
        return _Response({"run": {"id": "run-next"}})

    def get(url, headers=None, timeout=None):
        calls.append(("GET", url))
        return _Response({"status": "FINISHED", "result": "{\"title\":{\"en\":\"Cup\"}}"})

    def delete(url, headers=None, timeout=None):
        calls.append(("DELETE", url))
        return _Response({})

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx, "delete", delete)
    return calls


def _complete():
    return ai_pair("crsr_test", "https://api.cursor.com", "auto")[2]


def test_one_agent_serves_twenty_products_then_rotates(monkeypatch):
    calls = _install(monkeypatch)
    configure_cursor_lanes(lanes=1, products_per_agent=2)
    complete = _complete()

    with cursor_product():
        assert "Cup" in complete("first")
        assert "Cup" in complete("repair")
    with cursor_product():
        complete("second")
    with cursor_product():
        complete("third")

    creates = [url for kind, url in calls if kind == "POST" and url.endswith("/v1/agents")]
    follows = [url for kind, url in calls if kind == "POST" and url.endswith("/runs")]
    deletes = [url for kind, url in calls if kind == "DELETE"]
    assert creates == [
        "https://api.cursor.com/v1/agents",
        "https://api.cursor.com/v1/agents",
    ]
    assert follows == [
        "https://api.cursor.com/v1/agents/bc-1/runs",
        "https://api.cursor.com/v1/agents/bc-1/runs",
    ]
    assert deletes == ["https://api.cursor.com/v1/agents/bc-1"]


def test_follow_sends_wait_for_the_next_minute_instead_of_stacking():
    now = [0.0]

    def clock():
        return now[0]

    def sleep(seconds):
        now[0] += seconds

    gate = _FollowGate(per_minute=2, clock=clock, sleep=sleep)
    gate.wait()
    gate.wait()
    gate.wait()
    assert now[0] >= 60


def test_a_busy_agent_is_retried_instead_of_skipping_the_product(monkeypatch):
    calls = []
    state = {"posts": 0}

    def post(url, headers=None, json=None, timeout=None):
        calls.append(url)
        state["posts"] += 1
        if url.endswith("/v1/agents"):
            return _Response({"agent": {"id": "bc-1"}, "run": {"id": "run-1"}}, 201)
        if state["posts"] == 2:
            return _Response({"error": "agent_busy"}, 409)
        return _Response({"run": {"id": "run-2"}})

    def get(url, headers=None, timeout=None):
        return _Response({"status": "FINISHED", "result": "{\"title\":{\"en\":\"Cup\"}}"})

    def delete(url, headers=None, timeout=None):
        return _Response({})

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx, "delete", delete)
    monkeypatch.setattr("shop.writer.time.sleep", lambda _seconds: None)
    configure_cursor_lanes(lanes=1, products_per_agent=20)
    complete = _complete()

    with cursor_product():
        complete("first")
    with cursor_product():
        assert "Cup" in complete("second")

    assert calls.count("https://api.cursor.com/v1/agents/bc-1/runs") == 2


def test_a_dropped_poll_reads_the_finished_translation(monkeypatch):
    gets = {"n": 0}

    def post(url, headers=None, json=None, timeout=None):
        if url.endswith("/v1/agents"):
            return _Response({"agent": {"id": "bc-1"}, "run": {"id": "run-1"}}, 201)
        return _Response({"run": {"id": "run-next"}})

    def get(url, headers=None, timeout=None):
        gets["n"] += 1
        if gets["n"] == 1:
            raise httpx.ConnectError("reset")
        return _Response({"status": "FINISHED", "result": "{\"title\":{\"en\":\"Cup\"}}"})

    def delete(url, headers=None, timeout=None):
        raise AssertionError("a dropped poll must not delete the agent")

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "get", get)
    monkeypatch.setattr(httpx, "delete", delete)
    monkeypatch.setattr("shop.writer.time.sleep", lambda _seconds: None)
    monkeypatch.setattr("shop.writer._poll_gate._sleep", lambda _seconds: None)
    configure_cursor_lanes(lanes=1, products_per_agent=20)
    complete = _complete()

    with cursor_product():
        assert "Cup" in complete("first")

    assert gets["n"] == 2


def test_a_call_outside_a_product_still_opens_and_closes_its_own_agent(monkeypatch):
    calls = _install(monkeypatch)
    configure_cursor_lanes(lanes=1, products_per_agent=20)
    complete = _complete()

    complete("judge")

    creates = [url for kind, url in calls if kind == "POST" and url.endswith("/v1/agents")]
    deletes = [url for kind, url in calls if kind == "DELETE"]
    assert creates == ["https://api.cursor.com/v1/agents"]
    assert deletes == ["https://api.cursor.com/v1/agents/bc-1"]
