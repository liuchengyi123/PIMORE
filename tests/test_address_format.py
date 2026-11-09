from shop.address_format import (
    compose_street,
    extra_regions,
    extra_required,
    field_order,
    formats_for,
    label_lines,
    required_keys,
)
from shop.geo import here_fields


def test_each_country_keeps_its_own_order():
    assert field_order("US") == ["line", "region", "city", "postal"]
    assert field_order("GB") == ["line", "city", "postal"]
    assert field_order("JP") == ["postal", "region", "city", "line"]
    assert field_order("BR") == ["postal", "line", "number", "district", "region", "city"]
    assert field_order("CN") == ["region", "city", "district", "line", "postal"]
    assert field_order("HK") == ["region", "district", "line"]
    assert field_order("NL") == ["postal", "number", "line", "city"]
    assert "region" not in field_order("ZZ")


def test_hidden_lines_are_not_required():
    assert "region" not in required_keys("GB")
    assert "city" not in required_keys("HK")
    assert "postal" not in required_keys("HK")
    assert "region" in required_keys("US")
    assert "postal" in required_keys("CN")
    assert extra_required("CN") == ["district"]
    assert extra_required("BR") == ["street_number", "district"]
    assert extra_required("US") == []


def test_labels_follow_the_shop_language_and_the_country():
    zh = formats_for("zh")["CN"]
    assert zh["labels"]["region"] == "省 / 直辖市"
    assert zh["labels"]["district"] == "区 / 县"
    assert zh["order"][0] == "region"
    en = formats_for("en")["CN"]
    assert en["labels"]["region"] == "Province"
    assert en["place"] == "China"
    assert formats_for("en")["US"]["labels"]["postal"] == "ZIP code"
    assert formats_for("ja")["JP"]["labels"]["region"] == "都道府県"
    assert formats_for("en")["*"]["order"] == ["line", "city", "postal"]


def test_street_is_composed_in_the_local_order():
    assert compose_street("CN", "中山路 1 号", "", "朝阳区") == "朝阳区\n中山路 1 号"
    assert compose_street("BR", "Rua A", "10", "Centro") == "Rua A, 10\nCentro"
    assert compose_street("NL", "Damrak", "1", "") == "Damrak 1"
    assert compose_street("US", "1 Main", "9", "Downtown") == "1 Main"
    cn = label_lines("CN", "李雷", "13800000000", "朝阳区\n中山路 1 号", "北京市", "北京市", "100000")
    assert cn[0] == "李雷"
    assert "100000" in cn


def test_province_list_is_in_the_shop_language():
    en = extra_regions("CN", "en")
    assert en[0]["code"] == "北京市"
    assert en[0]["name"] == "Beijing"
    zh = extra_regions("CN", "zh")
    assert zh[0]["name"] == "北京市"
    assert extra_regions("US", "en") == []
    assert len(extra_regions("AU", "en")) == 8


def test_pasted_address_uses_the_town_library_and_keeps_the_street():
    from shop.places import read_address, suggest_places

    us = read_address("US", "Jane Roe 123 Main St, Austin, TX 78701")
    assert us["name"] == "Jane Roe"
    assert us["city"] == "Austin"
    assert us["region"] == "TX"
    assert us["postal"] == "78701"
    assert us["line"] == "123 Main St"
    cn = read_address("CN", "李雷 13800138000 广东省深圳市南山区科技园南路1号 518057")
    assert cn["name"] == "李雷"
    assert cn["phone"] == "13800138000"
    assert cn["region"] == "广东省"
    assert cn["city"] == "深圳市"
    assert cn["district"] == "南山区"
    assert cn["postal"] == "518057"
    assert "科技园" in cn["line"]
    assert "南山区" not in cn["line"]
    huangpu = read_address("CN", "广东省广州市黄埔区科学城开源大道1号")
    assert huangpu["region"] == "广东省"
    assert huangpu["city"] == "广州市"
    assert huangpu["district"] == "黄埔区"
    assert "科学城" in huangpu["line"]
    assert "黄埔" not in huangpu["line"]
    from shop.cn_areas import cities, districts
    assert "广州市" in cities("广东省")
    assert "黄埔区" in districts("广东省", "广州市")
    assert "东城区" in districts("北京市", "北京市")
    places = suggest_places("US", "aus", "TX", "en")
    assert any(row["city"] == "Austin" and row["region"] == "TX" for row in places)
    assert all(row["region"] == "TX" for row in places)


def test_location_fill_uses_the_local_street_order():
    de = here_fields({"address": {
        "country_code": "de",
        "road": "Hauptstraße",
        "house_number": "12",
        "city": "Berlin",
        "postcode": "10115",
    }})
    assert de["line"] == "Hauptstraße 12"
    assert de["number"] == ""
    us = here_fields({"address": {
        "country_code": "us",
        "road": "Main Street",
        "house_number": "12",
        "city": "Austin",
        "state": "Texas",
        "postcode": "78701",
    }})
    assert us["line"] == "12 Main Street"
    br = here_fields({"address": {
        "country_code": "br",
        "road": "Rua A",
        "house_number": "10",
        "suburb": "Centro",
        "city": "São Paulo",
    }})
    assert br["line"] == "Rua A"
    assert br["number"] == "10"
    assert br["district"] == "Centro"
