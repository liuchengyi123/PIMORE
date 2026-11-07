import json
import os
import re
import threading
import time

from shop.translate import LANGS, has_cjk

CURSOR_LANES = 6
# One product per agent. The next product opens a new agent instead of continuing the last chat.
PRODUCTS_PER_AGENT = 1
# Cursor allows 30 add-followup calls per minute. Stay under that for every lane together.
FOLLOW_PER_MINUTE = 24

_LANG_NAMES = {
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "pt": "Brazilian Portuguese",
    "ja": "Japanese",
}


def write_english(facts, complete):
    prompt = (
        "Write a household-store listing in natural English. "
        "The title is what a shopper reads, not a keyword list. "
        "Keep numbers and units unchanged. "
        "Reply with a JSON object and nothing else, keys title, description, options. "
        "title and description are English. "
        "options is an array of English labels, same count and same order as the source options. "
        "Translate every Chinese word. Keep numbers, sizes, and units.\n"
        f"Source title: {facts.get('title') or ''}\n"
        f"Details: {facts.get('description') or ''}\n"
        f"Material: {facts.get('material') or ''}\n"
        f"Size: {facts.get('size') or ''}\n"
        f"Weight: {facts.get('weight') or ''}\n"
        "Source options, one per line:\n"
        + "\n".join(facts.get("options") or [])
    )
    data = _json_object(complete(prompt))
    title = str(data.get("title") or "").strip()
    description = str(data.get("description") or "").strip()
    if not title or has_cjk(title) or has_cjk(description):
        raise ValueError("title")
    result = {"title": title[:140], "description": description[:2000]}
    source_options = [str(item).strip() for item in (facts.get("options") or []) if str(item).strip()]
    raw_options = data.get("options")
    if isinstance(raw_options, list) and len(raw_options) == len(source_options):
        translated = []
        for item in raw_options:
            text = str(item or "").strip()
            if not text or has_cjk(text):
                translated = []
                break
            translated.append(text[:180])
        if translated:
            result["options"] = translated
    return result


def _clean_text(value, limit, lang="en"):
    text = str(value or "").strip()
    if not text:
        return ""
    if lang != "ja" and has_cjk(text):
        return ""
    return text[:limit]


def _lang_dict(value, limit):
    if isinstance(value, str):
        text = _clean_text(value, limit, "en")
        return {"en": text} if text else {}
    if not isinstance(value, dict):
        return {}
    found = {}
    for lang in LANGS:
        text = _clean_text(value.get(lang), limit, lang)
        if text:
            found[lang] = text
    return found


def _listing_prompt(facts, source_options):
    languages = ", ".join(f"{code} ({_LANG_NAMES[code]})" for code in LANGS)
    return (
        "Translate this household product into every language in one JSON object. "
        "Reply with JSON only. Keys: title, description, material, options. "
        "title, description, and material are objects keyed by "
        f"{languages}. "
        "options is an array with one object per source option, same count and same order. "
        "Each option object uses the same language keys. "
        "Write natural shopper language, not a keyword list. "
        "Keep numbers, sizes, and units unchanged. Do not leave any Chinese characters.\n"
        f"Source title: {facts.get('title') or ''}\n"
        f"Details: {facts.get('description') or ''}\n"
        f"Material: {facts.get('material') or ''}\n"
        f"Size: {facts.get('size') or ''}\n"
        f"Weight: {facts.get('weight') or ''}\n"
        "Source options, one per line:\n"
        + "\n".join(source_options)
    )


def _option_rows(raw, source_options):
    if not source_options:
        return []
    if not isinstance(raw, list) or len(raw) != len(source_options):
        return None
    rows = []
    for item in raw:
        if isinstance(item, str):
            text = _clean_text(item, 180)
            if not text:
                return None
            rows.append({"en": text})
            continue
        if not isinstance(item, dict):
            return None
        labels = _lang_dict(item, 180)
        if not labels.get("en"):
            return None
        rows.append(labels)
    return rows


def _listing_from_json(data, source_options):
    titles = _lang_dict(data.get("title"), 140)
    if not titles.get("en"):
        return None
    descriptions = _lang_dict(data.get("description"), 2000)
    material = _lang_dict(data.get("material"), 200) if data.get("material") else {}
    return {
        "title": titles,
        "description": descriptions,
        "material": material,
        "options": _option_rows(data.get("options"), source_options),
    }


def _missing_langs(result, source_options):
    missing = []
    for lang in LANGS:
        if lang == "en":
            continue
        title_missing = not result["title"].get(lang)
        description_missing = bool(result["description"].get("en")) and not result["description"].get(lang)
        if title_missing or description_missing:
            missing.append(lang)
    options = result["options"]
    if source_options and options is None:
        missing.append("options")
    elif source_options and isinstance(options, list):
        for row in options:
            if any(lang != "en" and not row.get(lang) for lang in LANGS):
                missing.append("options")
                break
    return missing


def _repair_prompt(result, source_options, missing):
    languages = ", ".join(missing)
    return (
        "The English listing is done. Fill the missing translations in one JSON object. "
        "Reply with JSON only. Use the same keys: title, description, material, options. "
        f"Include these languages: {languages}. "
        "options must have the same count and order as the source options. "
        "Keep numbers and units. Do not leave Chinese characters.\n"
        f"English title: {result['title'].get('en') or ''}\n"
        f"English description: {result['description'].get('en') or ''}\n"
        f"English material: {result['material'].get('en') or ''}\n"
        "Source options, one per line:\n"
        + "\n".join(source_options)
    )


def _merge_listing(base, extra, source_options):
    for key, limit in (("title", 140), ("description", 2000), ("material", 200)):
        incoming = _lang_dict(extra.get(key), limit)
        for lang, text in incoming.items():
            if not base[key].get(lang):
                base[key][lang] = text
    if base["options"] is None:
        base["options"] = _option_rows(extra.get("options"), source_options)
    elif isinstance(base["options"], list):
        incoming = _option_rows(extra.get("options"), source_options)
        if incoming:
            for current, row in zip(base["options"], incoming):
                for lang, text in row.items():
                    if not current.get(lang):
                        current[lang] = text
    return base


def write_listing(facts, complete):
    source_options = [str(item).strip() for item in (facts.get("options") or []) if str(item).strip()]
    result = _listing_from_json(_json_object(complete(_listing_prompt(facts, source_options))), source_options)
    if result is None:
        raise ValueError("title")
    missing = _missing_langs(result, source_options)
    if missing:
        try:
            extra = _json_object(complete(_repair_prompt(result, source_options, missing)))
            result = _merge_listing(result, extra, source_options)
        except Exception:
            pass
    result["localized"] = True
    return result


def _json_object(raw):
    text = str(raw or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.IGNORECASE).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("title")
    return data


def _cursor_model(model):
    model = str(model or "").strip() or "auto"
    if model == "auto":
        return "default"
    return model


def _uses_cursor(key, base):
    host = base.lower()
    return key.startswith("crsr_") or "api.cursor.com" in host or host.endswith("cursor.sh")


def _prompt_text(prompt):
    return (
        "Do not use tools or edit files. Reply with the answer only. "
        "This is a new product. Ignore every earlier product.\n\n"
        + prompt
    )


def _retryable_cursor_error(exc):
    name = type(exc).__name__
    return "Connect" in name or "Timeout" in name or "Proxy" in name


class _CursorLanes:
    def __init__(self, lanes=CURSOR_LANES, products_per_agent=PRODUCTS_PER_AGENT):
        self.lanes = lanes
        self.products_per_agent = products_per_agent
        self._mutex = threading.Lock()
        self._free = [
            {"agent_id": None, "products": 0, "touched": False, "key": ""}
            for _ in range(lanes)
        ]
        self._local = threading.local()

    def hold(self):
        lane = self._take()
        self._local.lane = lane

        class _Bound:
            def __enter__(self_):
                return lane

            def __exit__(self_, exc_type, exc, tb):
                current = self._local.lane
                self._local.lane = None
                self._finish(current)

        return _Bound()

    def live_agent_ids(self):
        with self._mutex:
            lanes = list(self._free)
        current = getattr(self._local, "lane", None)
        if current is not None:
            lanes.append(current)
        return {lane["agent_id"] for lane in lanes if lane.get("agent_id")}

    def _take(self):
        while True:
            with self._mutex:
                if self._free:
                    return self._free.pop()
            time.sleep(0.02)

    def _finish(self, lane):
        if lane is None:
            return
        try:
            if lane["touched"]:
                lane["products"] += 1
                lane["touched"] = False
            if lane["agent_id"] and lane["products"] >= self.products_per_agent:
                _delete_cursor_agent(lane["agent_id"], lane.get("key") or "")
                lane["agent_id"] = None
                lane["products"] = 0
                lane["key"] = ""
        finally:
            with self._mutex:
                self._free.append(lane)


_lanes = _CursorLanes()


def configure_cursor_lanes(lanes=CURSOR_LANES, products_per_agent=PRODUCTS_PER_AGENT):
    global _lanes
    _lanes = _CursorLanes(lanes, products_per_agent)
    return _lanes


def cursor_product():
    """Hold one translation agent for the current product, including a repair call."""
    return _lanes.hold()


def prepare_cursor_lanes(key):
    """Drop agents left behind by a restart before this process opens its own."""
    if _lanes.live_agent_ids():
        return
    key = str(key or "").strip()
    if not key.startswith("crsr_"):
        return
    try:
        _sweep_translate_agents(key)
    except Exception:
        return


def _cursor_headers(key):
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _delete_cursor_agent(agent_id, key):
    import httpx

    if not agent_id or not key:
        return
    try:
        httpx.delete(
            f"https://api.cursor.com/v1/agents/{agent_id}",
            headers=_cursor_headers(key),
            timeout=15,
        )
    except Exception:
        pass


def _sweep_translate_agents(key):
    import httpx

    headers = _cursor_headers(key)
    cursor = ""
    ids = []
    for _ in range(10):
        params = {"cursor": cursor} if cursor else None
        listed = httpx.get("https://api.cursor.com/v1/agents", headers=headers, params=params, timeout=30)
        if listed.status_code != 200:
            break
        payload = listed.json()
        items = payload.get("items") or []
        for agent in items:
            if isinstance(agent, dict) and agent.get("name") == "harbor-translate" and agent.get("id"):
                ids.append(str(agent["id"]))
        cursor = str(payload.get("nextCursor") or "")
        if not cursor or not items:
            break
    for agent_id in ids:
        _delete_cursor_agent(agent_id, key)


def _http_status(exc):
    return getattr(getattr(exc, "response", None), "status_code", None)


def _transient_http(exc):
    return _http_status(exc) in {401, 429, 502, 503, 504}


class _PollGate:
    """Spread result checks so eighteen lanes do not open eighteen connections at once."""

    def __init__(self, per_second=6, clock=None, sleep=None):
        self.interval = 1 / per_second
        self._clock = clock or time.time
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self):
        with self._lock:
            now = self._clock()
            delay = self._next - now
            self._next = max(self._next, now) + self.interval
        if delay > 0:
            self._sleep(delay)


_poll_gate = _PollGate()


def _poll_cursor_run(key, agent_id, run_id):
    import httpx

    headers = _cursor_headers(key)
    deadline = time.time() + 240
    auth_misses = 0
    while time.time() < deadline:
        _poll_gate.wait()
        try:
            current = httpx.get(
                f"https://api.cursor.com/v1/agents/{agent_id}/runs/{run_id}",
                headers=headers,
                timeout=30,
            )
            current.raise_for_status()
        except Exception as exc:
            if _http_status(exc) == 401:
                auth_misses += 1
                if auth_misses >= 4:
                    raise
            elif not _retryable_cursor_error(exc) and not _transient_http(exc):
                raise
            time.sleep(1.5)
            continue
        auth_misses = 0
        payload = current.json()
        status = payload.get("status")
        if status == "FINISHED":
            text = payload.get("result") or ""
            if text or time.time() + 1.5 >= deadline:
                return text
        elif status in {"ERROR", "CANCELLED", "EXPIRED"}:
            raise RuntimeError(status)
        time.sleep(1.5)
    raise TimeoutError("timed out")


def _create_cursor_run(key, model, prompt):
    import httpx

    headers = _cursor_headers(key)
    last = None
    for _ in range(3):
        try:
            created = httpx.post(
                "https://api.cursor.com/v1/agents",
                headers=headers,
                json={
                    "name": "harbor-translate",
                    "prompt": {"text": _prompt_text(prompt)},
                    "model": {"id": _cursor_model(model)},
                },
                timeout=httpx.Timeout(60.0, connect=8.0),
            )
            created.raise_for_status()
            data = created.json()
            return data["agent"]["id"], data["run"]["id"]
        except Exception as exc:
            last = exc
            if not _retryable_cursor_error(exc) and not _transient_http(exc):
                raise
            time.sleep(2)
    raise last


class _FollowGate:
    """One shared queue for follow-up sends. A full minute is a wait, not a failed product."""

    def __init__(self, per_minute=FOLLOW_PER_MINUTE, clock=None, sleep=None):
        self.per_minute = per_minute
        self._clock = clock or time.time
        self._sleep = sleep or time.sleep
        self._lock = threading.Lock()
        self._times = []

    def wait(self):
        while True:
            with self._lock:
                now = self._clock()
                self._times = [stamp for stamp in self._times if now - stamp < 60]
                if len(self._times) < self.per_minute:
                    self._times.append(now)
                    return
                delay = 60 - (now - self._times[0]) + 0.05
            self._sleep(max(delay, 0.05))

    def cool_down(self):
        with self._lock:
            now = self._clock()
            if self._times:
                delay = 60 - (now - self._times[0]) + 0.1
            else:
                delay = 60
        self._sleep(max(delay, 1))


_follow_gate = _FollowGate()


def _wait_until_idle(key, agent_id):
    import httpx

    deadline = time.time() + 90
    while time.time() < deadline:
        try:
            current = httpx.get(
                f"https://api.cursor.com/v1/agents/{agent_id}",
                headers=_cursor_headers(key),
                timeout=30,
            )
        except Exception as exc:
            if not _retryable_cursor_error(exc):
                raise
            time.sleep(2)
            continue
        if current.status_code != 200:
            return
        status = str((current.json() or {}).get("status") or "")
        if status not in {"ACTIVE", "RUNNING", "CREATING"}:
            return
        time.sleep(2)


def _follow_cursor_run(key, agent_id, prompt):
    import httpx

    _wait_until_idle(key, agent_id)
    last = None
    last_error = None
    for _ in range(4):
        _follow_gate.wait()
        try:
            followed = httpx.post(
                f"https://api.cursor.com/v1/agents/{agent_id}/runs",
                headers=_cursor_headers(key),
                json={"prompt": {"text": _prompt_text(prompt)}},
                timeout=httpx.Timeout(60.0, connect=8.0),
            )
        except Exception as exc:
            last_error = exc
            if not _retryable_cursor_error(exc) and not _transient_http(exc):
                raise
            time.sleep(2)
            continue
        last = followed
        if followed.status_code == 429:
            _follow_gate.cool_down()
            continue
        if followed.status_code == 409:
            _wait_until_idle(key, agent_id)
            continue
        followed.raise_for_status()
        data = followed.json()
        run = data.get("run") or {}
        run_id = run.get("id") or data.get("runId")
        if not run_id:
            raise RuntimeError("missing run")
        return run_id
    if last is not None:
        last.raise_for_status()
    if last_error is not None:
        raise last_error
    raise RuntimeError("agent_busy")


def _cursor_once(key, model, prompt):
    agent_id, run_id = _create_cursor_run(key, model, prompt)
    try:
        return _poll_cursor_run(key, agent_id, run_id)
    finally:
        _delete_cursor_agent(agent_id, key)


def _cursor_on_lane(lane, key, model, prompt):
    lane["touched"] = True
    lane["key"] = key

    def attempt(fresh):
        if fresh or not lane["agent_id"]:
            if lane["agent_id"]:
                _delete_cursor_agent(lane["agent_id"], key)
                lane["agent_id"] = None
            agent_id, run_id = _create_cursor_run(key, model, prompt)
            lane["agent_id"] = agent_id
        else:
            try:
                run_id = _follow_cursor_run(key, lane["agent_id"], prompt)
            except Exception as exc:
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status != 404:
                    raise
                _delete_cursor_agent(lane["agent_id"], key)
                lane["agent_id"] = None
                agent_id, run_id = _create_cursor_run(key, model, prompt)
                lane["agent_id"] = agent_id
            else:
                agent_id = lane["agent_id"]
        return _poll_cursor_run(key, agent_id, run_id)

    # A dropped connection retries the same run. Deleting the agent here throws away a finished translation.
    return attempt(False)


def _cursor_complete(key, model, prompt):
    lane = getattr(_lanes._local, "lane", None)
    if lane is None:
        return _cursor_once(key, model, prompt)
    return _cursor_on_lane(lane, key, model, prompt)


def ai_pair(key, base="", model=""):
    key = str(key or "").strip()
    if not key:
        return None
    base = (str(base or "").strip() or "https://api.cursor.com").rstrip("/")
    model = str(model or "").strip() or "auto"

    def complete(prompt, max_tokens=300):
        if _uses_cursor(key, base):
            return _cursor_complete(key, model, prompt)
        import httpx

        from shop.net import outbound_proxy

        response = httpx.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "temperature": 0.7,
                "max_tokens": int(max_tokens or 300),
                "enable_thinking": False,
                "messages": [
                    {"role": "system", "content": "Follow the instructions in the user message. Reply with only the final answer text."},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=httpx.Timeout(60.0, connect=5.0),
            proxy=outbound_proxy() or None,
        )
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        return message.get("content") or message.get("reasoning_content") or ""

    names = {
        "en": "English",
        "es": "Spanish",
        "de": "German",
        "fr": "French",
        "pt": "Brazilian Portuguese",
        "ja": "Japanese",
    }

    def translate(text, source, target):
        reply = complete(
            f"Translate this product text from {names.get(source, source)} into {names[target]}. "
            "Keep numbers and units. Reply with the translation only.\n\n"
            + text
        )
        return reply.strip()

    def writer(facts):
        return write_listing(facts, complete)

    return writer, translate, complete


def ai_from_env():
    return ai_pair(
        os.environ.get("AI_API_KEY", ""),
        os.environ.get("AI_BASE_URL", ""),
        os.environ.get("AI_MODEL", ""),
    )


def supplier_link(listing):
    url = str(listing.get("url") or "").strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    offer = re.sub(r"\D", "", str(listing.get("offer_id") or ""))
    if offer:
        return f"https://detail.1688.com/offer/{offer}.html"
    return ""
