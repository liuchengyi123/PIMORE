from shop.locale import resolve, shipping_tier


def test_japan_and_germany():
    assert resolve("JP") == ("ja", "JPY")
    assert resolve("DE") == ("de", "EUR")
    assert resolve("BR") == ("pt", "BRL")
    assert resolve("MX") == ("es", "MXN")
    assert resolve("GB") == ("en", "GBP")
    assert resolve("CA") == ("en", "CAD")
    assert resolve("US") == ("en", "USD")
    assert resolve("ZZ") == ("en", "USD")


def test_more_language_and_currency_pairs():
    assert resolve("ES") == ("es", "EUR")
    assert resolve("FR") == ("fr", "EUR")
    assert resolve("PT") == ("pt", "EUR")
    assert resolve("AT") == ("de", "EUR")


def test_shipping_tiers():
    assert shipping_tier("JP") == "JP"
    assert shipping_tier("US") == "USCA"
    assert shipping_tier("CA") == "USCA"
    assert shipping_tier("MX") == "MXBR"
    assert shipping_tier("BR") == "MXBR"
    assert shipping_tier("DE") == "EU"
    assert shipping_tier("GB") == "EU"
    assert shipping_tier("CH") == "EU"
    assert shipping_tier("AU") == "USCA"
