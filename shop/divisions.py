"""Address lists rebuilt on 2026-11-02.

Spain is the INE municipality list as of 1 Jan 2026. Portugal is all 308
municipalities. Brazil is the IBGE municipality list. Mexico is the state
municipality list, including the 16 Mexico City alcaldías. Canada is every
2025 StatCan census subdivision. Germany is every 2025 Gemeinde, with the
district added when two short names would otherwise collide. Britain adds
villages, localities and London to the post towns. The United States stays
the open place register: the Census file refused the download, and the postal
city file cannot be redistributed. France is the current INSEE commune list.
Japan is the July 2026 municipality list, including wards. Street, bairro and
colonia stay typed; there is no free complete street file.
"""
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "divisions.json"
_DATA = None


def divisions():
    global _DATA
    if _DATA is None:
        # Address library is optional at runtime. Checkout quote and order
        # placement still run when the file was not shipped with the tree.
        if not _PATH.is_file():
            _DATA = {}
        else:
            with _PATH.open(encoding="utf-8") as handle:
                _DATA = json.load(handle)
    return _DATA


def country_choices():
    data = divisions()
    return [(code, data[code]["label"]) for code in data]


def region_choices(country):
    block = divisions().get((country or "").strip().upper()[:2])
    if not block:
        return []
    return [{"code": row["code"], "name": row["name"]} for row in block["regions"]]


def city_choices(country, region):
    block = divisions().get((country or "").strip().upper()[:2])
    if not block:
        return []
    wanted = (region or "").strip()
    for row in block["regions"]:
        if row["code"] == wanted or row["name"] == wanted:
            return row["cities"]
    return []
