from shop.image_gen import cover_slot, normalize_cover, order_mains

URLS = [
    "/static/catalog/sku/en/main/1.jpg",
    "/static/catalog/sku/en/main/2.jpg",
    "/static/catalog/sku/en/main/4.jpg",
]


def test_unknown_cover_means_the_scene_shot():
    assert normalize_cover("") == "1"
    assert normalize_cover("9") == "1"
    assert normalize_cover("124") == "124"


def test_one_slot_leads_every_product():
    assert order_mains(URLS, "a", "4")[0].endswith("/4.jpg")
    assert order_mains(URLS, "b", "2")[0].endswith("/2.jpg")
    assert order_mains(URLS, "c", "1")[0].endswith("/1.jpg")


def test_mix_stays_inside_the_chosen_slots_and_does_not_flicker():
    first = order_mains(URLS, "lint", "12")[0]
    again = order_mains(URLS, "lint", "12")[0]
    assert first == again
    assert first.endswith("/1.jpg") or first.endswith("/2.jpg")
    seen = {cover_slot(f"sku-{i}", "124") for i in range(30)}
    assert seen == {1, 2, 4}


def test_a_missing_slot_uses_another_picture_from_the_mix():
    only_white = ["/static/catalog/sku/en/main/4.jpg"]
    assert order_mains(only_white, "sku", "1")[0].endswith("/4.jpg")
    pair = [
        "/static/catalog/sku/en/main/2.jpg",
        "/static/catalog/sku/en/main/4.jpg",
    ]
    assert order_mains(pair, "sku", "14")[0].endswith("/4.jpg")
