import pytest

from liveroom.room import Room
from liveroom.speech import SpeechError, answer_line, guard, selling_line


def sku():
    return {
        "id": "jacket",
        "name": "棒球夹克",
        "price": "199元",
        "sizes": "M适合160到170",
        "fabric": "棉",
        "banned": ["全网最低"],
        "script": [
            "这件{name}今天到手{price}。",
            "面料是{fabric}。",
            "尺码你对一下，{sizes}。",
        ],
        "facts": [{"keywords": ["版型"], "text": "这件{name}是宽松版。"}],
        "video": "jacket.mp4",
    }


def test_price_edit_is_spoken_on_the_next_line():
    data = sku()
    data["price"] = "79元"
    text, cursor, index = selling_line(data, 0)
    assert text == "这件棒球夹克今天到手79元。"
    assert index == 0
    assert cursor == 1


def test_size_question_uses_the_chart_and_unknown_question_invents_nothing():
    answer, topic = answer_line(sku(), "我穿多大")
    assert topic == "size"
    assert "M适合160到170" in answer
    bridge, bridge_topic = answer_line(sku(), "有红色的帽子吗")
    assert bridge_topic == "bridge"
    assert "帽子" not in bridge
    assert "红色" not in bridge
    fit, fit_topic = answer_line(sku(), "版型怎么样")
    assert fit_topic == "fact"
    assert "宽松" in fit


def test_banned_phrase_and_foreign_price_are_replaced():
    data = sku()
    assert "全网最低" not in guard("这件全网最低只要199元", data)
    assert "199元" in guard("这件全网最低只要199元", data)
    replaced = guard("今天只要1元", data)
    assert "1元" not in replaced
    assert "199元" in replaced


def test_blank_script_line_is_skipped():
    data = sku()
    data["script"] = ["", "面料是{fabric}。"]
    text, cursor, index = selling_line(data, 0)
    assert text == "面料是棉。"
    assert index == 1
    assert cursor == 0


def test_answer_does_not_skip_the_selling_line():
    room = Room({"current": "jacket", "skus": [sku(), {**sku(), "id": "shirt", "name": "卫衣", "price": "129元", "video": "shirt.mp4", "script": ["这件{name}{price}"]}]})
    room.push_danmaku("多少钱", "小王")
    answered = room.speak()
    assert answered["kind"] == "answer"
    assert "199元" in answered["text"]
    assert room.cursor == 0
    sold = room.speak()
    assert sold["kind"] == "sell"
    assert sold["text"].startswith("这件棒球夹克今天到手199元")
    assert room.cursor == 1


def test_switch_changes_the_picture_and_the_price():
    room = Room({"current": "jacket", "skus": [sku(), {**sku(), "id": "shirt", "name": "卫衣", "price": "129元", "video": "shirt.mp4", "script": ["换{name}，{price}"]}]})
    room.cursor = 2
    room.switch("shirt")
    spoken = room.speak()
    assert spoken["sku_id"] == "shirt"
    assert spoken["video"] == "shirt.mp4"
    assert "129元" in spoken["text"]
    assert room.cursor == 0


def test_unknown_slot_is_rejected():
    with pytest.raises(SpeechError):
        selling_line({**sku(), "script": ["颜色是{color}"]}, 0)


def test_duplicate_comment_stays_one_line_in_the_queue():
    room = Room({"current": "jacket", "skus": [sku()]})
    assert room.push_danmaku("我穿多大", "小王") is not None
    assert room.push_danmaku("我穿多大", "小王") is None
    assert len(room.queue) == 1
