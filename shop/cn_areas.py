"""Mainland China province, city, and district names.

The list is the public province-city-district file. A municipality such as
Beijing is stored as one city level (北京市) with its districts underneath,
so the form can offer three choices and leave the street to be typed.
"""
import json
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "data" / "cn_areas.json"
_DATA = None
_FLAT_CITY = {"市辖区", "县"}


def _tree():
    global _DATA
    if _DATA is None:
        with _PATH.open(encoding="utf-8") as handle:
            _DATA = json.load(handle)
    return _DATA


def provinces():
    return list(_tree())


def cities(province):
    block = _tree().get(province) or {}
    keys = list(block)
    if keys and set(keys) <= _FLAT_CITY:
        return [province]
    return keys


def districts(province, city):
    block = _tree().get(province) or {}
    if city == province and set(block) <= _FLAT_CITY:
        names = []
        for key in ("市辖区", "县"):
            names.extend(block.get(key) or [])
        return names
    return list(block.get(city) or [])
