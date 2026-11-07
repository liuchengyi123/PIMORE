from shop.hot import _profile, build_scores, hot_line, match_score, parse_titles


def _score(product, hot):
    tokens, bigrams, cjk = _profile(hot)
    return match_score(product, [(tokens, bigrams, cjk, hot)])


def test_parse_titles_reads_bestseller_names():
    html = """
    <div class="p13n-sc-css-line-clamp-3_g3dy1">Owala FreeSip Water Bottle</div>
    <div class="p13n-sc-css-line-clamp-2_">4.6 out of 5 stars</div>
    <div class="p13n-sc-css-line-clamp-3_g3dy1">Kitchen Dish Rack Stainless</div>
    """
    assert parse_titles(html) == ["Owala FreeSip Water Bottle", "Kitchen Dish Rack Stainless"]


def test_same_type_matches_and_a_shared_word_does_not():
    assert _score("Dish rack", "Acme Dish Rack Stainless Steel") > 0
    assert _score("Door stop", "Heavy Duty Rubber Door Stopper") > 0
    assert _score("Sheet mask", "Queen Sheet Set Grey") == 0
    assert _score("Electric bike cover", "Clear Shower Curtain Liner") == 0


def test_scores_use_the_country_language():
    rows = [
        {"sku": "rack", "names": '{"en":"Dish rack","de":"Geschirrstaender"}'},
        {"sku": "mask", "names": '{"en":"Sheet mask","de":"Tuchmaske"}'},
    ]
    scores = build_scores(rows, {"DE": ["Acme Geschirrstaender Schwarz"], "US": ["Queen Sheet Set"]})
    assert "rack" in scores["DE"]
    assert "mask" not in scores["DE"]
    assert "mask" not in scores["US"]


def test_hot_line_waits_until_a_list_exists():
    assert hot_line({}, False) == "热销同款　还没有"
    assert "美国 1" in hot_line({"US": {"rack": 3}}, True)
    assert hot_line({"US": {}}, True) == "热销同款　这一周没有对上"
