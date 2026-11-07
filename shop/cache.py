import json
import os


class MemoryCache:
    def __init__(self):
        self.values = {}
        self.deleted = []

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.deleted.append(key)
        self.values.pop(key, None)


class RedisCache:
    def __init__(self, client):
        self.client = client

    def get(self, key):
        raw = self.client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set(self, key, value):
        self.client.set(key, json.dumps(value))

    def delete(self, key):
        self.client.delete(key)


def open_cache():
    url = os.environ.get("REDIS_URL", "")
    if not url:
        return MemoryCache()
    import redis

    return RedisCache(redis.Redis.from_url(url))
