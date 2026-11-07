from dataclasses import dataclass
from datetime import timezone


class NoRate(Exception):
    pass


CURRENCIES = ("JPY", "EUR", "GBP", "BRL", "MXN", "CAD")


@dataclass(frozen=True)
class Rate:
    units_per_usd: float
    stale: bool


def _pick(rates):
    return {code: float(rates[code]) for code in CURRENCIES}


def fetch_frankfurter():
    import httpx

    response = httpx.get(
        "https://api.frankfurter.app/latest",
        params={"from": "USD", "to": ",".join(CURRENCIES)},
        timeout=4,
    )
    response.raise_for_status()
    return _pick(response.json()["rates"])


def fetch_open_er():
    import httpx

    response = httpx.get("https://open.er-api.com/v6/latest/USD", timeout=8)
    response.raise_for_status()
    body = response.json()
    if body.get("result") not in (None, "success"):
        raise RuntimeError("rate")
    return _pick(body["rates"])


def fetch_rates(primary=fetch_frankfurter, backup=fetch_open_er):
    try:
        return primary()
    except Exception:
        return backup()


def remember_rates(conn, data, hour):
    for code, units in data.items():
        conn.execute(
            "insert or replace into rates (currency, hour, units_per_usd) values (?, ?, ?)",
            (code, hour, float(units)),
        )


def load_rates(conn, hour):
    rows = conn.execute(
        "select currency, hour, units_per_usd from rates order by hour"
    ).fetchall()
    last = {}
    current = {}
    for row in rows:
        last[row["currency"]] = row["units_per_usd"]
        if row["hour"] == hour:
            current[row["currency"]] = row["units_per_usd"]
    return last, current


class RateBook:
    def __init__(self, fetch):
        self.fetch = fetch
        self.saved = {}
        self.last = {}

    def rate_for(self, currency, now):
        if currency == "USD":
            return Rate(1.0, False)
        hour = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")
        key = (currency, hour)
        if key in self.saved:
            return Rate(self.saved[key], False)
        try:
            data = self.fetch()
            rate = float(data[currency])
        except Exception:
            if currency not in self.last:
                raise NoRate(currency)
            return Rate(self.last[currency], True)
        for code, value in data.items():
            number = float(value)
            self.saved[(code, hour)] = number
            self.last[code] = number
        self.saved[key] = rate
        self.last[currency] = rate
        return Rate(rate, False)
