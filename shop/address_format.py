"""How each destination country writes a shipping address.

Labels follow the shop language. Field order follows the destination country.
The region list is still shown where the city list is too long to scroll,
even when that region is not printed on the local envelope.
"""

ORDER = {
    "US": ["line", "region", "city", "postal"],
    "CA": ["line", "region", "city", "postal"],
    "GB": ["line", "city", "postal"],
    "DE": ["line", "region", "postal", "city"],
    "FR": ["line", "region", "postal", "city"],
    "ES": ["line", "region", "postal", "city"],
    "PT": ["line", "region", "postal", "city"],
    "BR": ["postal", "line", "number", "district", "region", "city"],
    "MX": ["postal", "line", "district", "region", "city"],
    "JP": ["postal", "region", "city", "line"],
}

# line, city, region, postal, number, district
_TEXT = {
    "en": {
        "US": ("Street address", "City", "State", "ZIP code", "Number", "Neighborhood"),
        "CA": ("Street address", "City", "Province", "Postal code", "Number", "Neighborhood"),
        "GB": ("Street address", "Post town", "County", "Postcode", "Number", "Locality"),
        "DE": ("Street and house number", "City", "State", "Postcode", "Number", "District"),
        "FR": ("Street address", "City", "Department", "Postcode", "Number", "Locality"),
        "ES": ("Street address", "City", "Province", "Postcode", "Number", "Locality"),
        "PT": ("Street address", "City", "District", "Postcode", "Number", "Parish"),
        "BR": ("Street", "City", "State", "CEP", "Number", "Neighborhood"),
        "MX": ("Street and number", "Municipality", "State", "Postal code", "Number", "Colonia"),
        "JP": ("Block and number", "City", "Prefecture", "Postal code", "Number", "District"),
    },
    "es": {
        "US": ("Calle", "Ciudad", "Estado", "Código ZIP", "Número", "Barrio"),
        "CA": ("Calle", "Ciudad", "Provincia", "Código postal", "Número", "Barrio"),
        "GB": ("Calle", "Ciudad postal", "Condado", "Código postal", "Número", "Localidad"),
        "DE": ("Calle y número", "Ciudad", "Estado", "Código postal", "Número", "Distrito"),
        "FR": ("Calle", "Ciudad", "Departamento", "Código postal", "Número", "Localidad"),
        "ES": ("Calle y número", "Localidad", "Provincia", "Código postal", "Número", "Localidad"),
        "PT": ("Calle", "Ciudad", "Distrito", "Código postal", "Número", "Freguesia"),
        "BR": ("Calle", "Ciudad", "Estado", "CEP", "Número", "Barrio"),
        "MX": ("Calle y número", "Municipio", "Estado", "Código postal", "Número", "Colonia"),
        "JP": ("Manzana y número", "Municipio", "Prefectura", "Código postal", "Número", "Distrito"),
    },
    "de": {
        "US": ("Straße", "Stadt", "Bundesstaat", "PLZ", "Nummer", "Viertel"),
        "CA": ("Straße", "Stadt", "Provinz", "Postleitzahl", "Nummer", "Viertel"),
        "GB": ("Straße", "Postort", "Grafschaft", "Postleitzahl", "Nummer", "Ortsteil"),
        "DE": ("Straße und Hausnummer", "Ort", "Bundesland", "Postleitzahl", "Nummer", "Ortsteil"),
        "FR": ("Straße", "Stadt", "Département", "Postleitzahl", "Nummer", "Ortsteil"),
        "ES": ("Straße", "Ort", "Provinz", "Postleitzahl", "Nummer", "Ortsteil"),
        "PT": ("Straße", "Ort", "Distrikt", "Postleitzahl", "Nummer", "Gemeinde"),
        "BR": ("Straße", "Stadt", "Bundesstaat", "CEP", "Nummer", "Stadtviertel"),
        "MX": ("Straße und Hausnummer", "Gemeinde", "Bundesstaat", "Postleitzahl", "Nummer", "Colonia"),
        "JP": ("Block und Hausnummer", "Gemeinde", "Präfektur", "Postleitzahl", "Nummer", "Bezirk"),
    },
    "fr": {
        "US": ("Rue", "Ville", "État", "Code ZIP", "Numéro", "Quartier"),
        "CA": ("Rue", "Ville", "Province", "Code postal", "Numéro", "Quartier"),
        "GB": ("Rue", "Ville postale", "Comté", "Code postal", "Numéro", "Localité"),
        "DE": ("Rue et numéro", "Ville", "Land", "Code postal", "Numéro", "Quartier"),
        "FR": ("Numéro et rue", "Ville", "Département", "Code postal", "Numéro", "Lieu-dit"),
        "ES": ("Rue", "Localité", "Province", "Code postal", "Numéro", "Lieu-dit"),
        "PT": ("Rue", "Localité", "District", "Code postal", "Numéro", "Freguesia"),
        "BR": ("Rue", "Ville", "État", "CEP", "Numéro", "Quartier"),
        "MX": ("Rue et numéro", "Municipalité", "État", "Code postal", "Numéro", "Colonia"),
        "JP": ("Îlot et numéro", "Commune", "Préfecture", "Code postal", "Numéro", "Quartier"),
    },
    "pt": {
        "US": ("Rua", "Cidade", "Estado", "CEP americano", "Número", "Bairro"),
        "CA": ("Rua", "Cidade", "Província", "Código postal", "Número", "Bairro"),
        "GB": ("Rua", "Cidade postal", "Condado", "Código postal", "Número", "Localidade"),
        "DE": ("Rua e número", "Cidade", "Estado", "Código postal", "Número", "Bairro"),
        "FR": ("Rua", "Cidade", "Departamento", "Código postal", "Número", "Localidade"),
        "ES": ("Rua", "Cidade", "Província", "Código postal", "Número", "Localidade"),
        "PT": ("Morada", "Localidade", "Distrito", "Código postal", "Número", "Freguesia"),
        "BR": ("Rua", "Cidade", "Estado", "CEP", "Número", "Bairro"),
        "MX": ("Rua e número", "Município", "Estado", "Código postal", "Número", "Colonia"),
        "JP": ("Quadra e número", "Cidade", "Prefeitura", "Código postal", "Número", "Distrito"),
    },
    "ja": {
        "US": ("番地", "都市", "州", "ZIPコード", "番号", "地区"),
        "CA": ("番地", "都市", "州", "郵便番号", "番号", "地区"),
        "GB": ("番地", "ポストタウン", "州", "郵便番号", "番号", "地区"),
        "DE": ("番地", "都市", "州", "郵便番号", "番号", "地区"),
        "FR": ("番地", "コミューン", "県", "郵便番号", "番号", "地区"),
        "ES": ("番地", "市区町村", "県", "郵便番号", "番号", "地区"),
        "PT": ("番地", "市区町村", "県", "郵便番号", "番号", "地区"),
        "BR": ("通り", "市", "州", "CEP", "番号", "地区"),
        "MX": ("通りと番号", "基礎自治体", "州", "郵便番号", "番号", "コロニア"),
        "JP": ("町域・番地", "市区町村", "都道府県", "郵便番号", "番号", "地区"),
    },
    "zh": {
        "US": ("街道地址", "城市", "州", "邮政编码", "门牌号", "街区"),
        "CA": ("街道地址", "城市", "省", "邮政编码", "门牌号", "街区"),
        "GB": ("街道地址", "城镇", "郡", "邮编", "门牌号", "地区"),
        "DE": ("街道和门牌", "城市", "州", "邮编", "门牌号", "区"),
        "FR": ("街道地址", "城市", "省", "邮编", "门牌号", "地区"),
        "ES": ("街道地址", "城市", "省", "邮编", "门牌号", "地区"),
        "PT": ("街道地址", "城市", "区", "邮编", "门牌号", "堂区"),
        "BR": ("街道", "城市", "州", "邮编", "门牌号", "街区"),
        "MX": ("街道和门牌", "市", "州", "邮编", "门牌号", "社区"),
        "JP": ("番地", "市区町村", "都道府县", "邮编", "门牌号", "地区"),
    },
    "zh-Hant": {
        "US": ("街道地址", "城市", "州", "郵遞區號", "門牌號", "街區"),
        "CA": ("街道地址", "城市", "省", "郵遞區號", "門牌號", "街區"),
        "GB": ("街道地址", "城鎮", "郡", "郵編", "門牌號", "地區"),
        "DE": ("街道和門牌", "城市", "州", "郵編", "門牌號", "區"),
        "FR": ("街道地址", "城市", "省", "郵編", "門牌號", "地區"),
        "ES": ("街道地址", "城市", "省", "郵編", "門牌號", "地區"),
        "PT": ("街道地址", "城市", "區", "郵編", "門牌號", "堂區"),
        "BR": ("街道", "城市", "州", "郵編", "門牌號", "街區"),
        "MX": ("街道和門牌", "市", "州", "郵編", "門牌號", "社區"),
        "JP": ("番地", "市區町村", "都道府縣", "郵編", "門牌號", "地區"),
    },
}

_KEYS = ("line", "city", "region", "postal", "number", "district")


_DEST_LANG = {
    "US": "en",
    "GB": "en",
    "CA": "en",
    "DE": "de",
    "FR": "fr",
    "ES": "es",
    "PT": "pt",
    "BR": "pt",
    "MX": "es",
    "JP": "ja",
}


def _lang_key(lang):
    text = str(lang or "en").lower().replace("_", "-")
    if text.startswith("zh-hant") or text.startswith("zh-tw") or text.startswith("zh-hk"):
        return "zh-Hant"
    if text.startswith("zh"):
        return "zh"
    return text.split("-", 1)[0]


def formats_for(lang):
    table = _TEXT.get(_lang_key(lang))
    packed = {}
    for code, order in ORDER.items():
        words = (table or {}).get(code) or _TEXT[_DEST_LANG[code]][code]
        labels = dict(zip(_KEYS, words))
        entry = {"order": order, "labels": labels}
        if code == "CA":
            french = _TEXT["fr"]["CA"]
            entry["regions"] = {"QC": dict(zip(_KEYS, french if table is None else words))}
        packed[code] = entry
    return packed


def compose_street(country, street, number, district):
    street = (street or "").strip()
    number = (number or "").strip()
    district = (district or "").strip()
    country = (country or "").upper()
    if country == "BR":
        line = f"{street}, {number}" if street and number else street or number
        if district:
            line = f"{line}\n{district}" if line else district
        return line
    if country == "MX" and district:
        return f"{street}\n{district}" if street else district
    return street


def label_lines(country, name, phone, street, city, region, postal):
    country = (country or "US").upper()
    name = (name or "").strip()
    phone = (phone or "").strip()
    street = (street or "").strip()
    city = (city or "").strip()
    region = (region or "").strip()
    postal = (postal or "").strip()
    if country == "JP":
        lines = [f"〒{postal}" if postal else "", f"{region}{city}", street, name, phone]
    elif country == "US":
        lines = [name, street, " ".join(part for part in (f"{city}, {region}".strip(", "), postal) if part), phone]
    elif country == "CA":
        lines = [name, street, " ".join(part for part in (city, region, postal) if part), phone]
    elif country == "GB":
        lines = [name, street, city, postal, phone]
    elif country == "DE":
        lines = [name, street, " ".join(part for part in (postal, city) if part), phone]
    elif country == "FR":
        lines = [name, street, " ".join(part for part in (postal, city) if part), phone]
    elif country == "BR":
        lines = [name, street, " - ".join(part for part in (city, region) if part), postal, phone]
    elif country == "MX":
        lines = [name, street, ", ".join(part for part in (city, region) if part), postal, phone]
    elif country in {"ES", "PT"}:
        lines = [name, street, " ".join(part for part in (postal, city) if part), region, phone]
    else:
        lines = [name, street, " ".join(part for part in (city, region, postal) if part), phone]
    return [line for line in lines if line]
