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
    "CN": ["region", "city", "district", "line", "postal"],
    "TW": ["postal", "city", "district", "line"],
    "HK": ["region", "district", "line"],
    "MO": ["region", "line"],
    "SG": ["line", "postal"],
    "AU": ["line", "city", "region", "postal"],
    "NZ": ["line", "city", "postal"],
    "KR": ["postal", "region", "city", "line"],
    "IN": ["line", "city", "region", "postal"],
    "IT": ["line", "postal", "city", "region"],
    "NL": ["postal", "number", "line", "city"],
    "IE": ["line", "city", "postal"],
    "AT": ["line", "postal", "city"],
    "BE": ["line", "postal", "city"],
    "CH": ["line", "postal", "city"],
    "SE": ["line", "postal", "city"],
    "NO": ["line", "postal", "city"],
    "DK": ["line", "postal", "city"],
    "FI": ["line", "postal", "city"],
    "PL": ["line", "postal", "city"],
    "AE": ["line", "city", "region"],
}

DEFAULT_ORDER = ["line", "city", "postal"]

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

# line, city, region, postal, number, district — used when a country has no row in _TEXT.
_GENERIC = {
    "en": ("Street address", "City", "Region", "Postal code", "Number", "District"),
    "es": ("Dirección", "Ciudad", "Región", "Código postal", "Número", "Distrito"),
    "de": ("Straße", "Ort", "Region", "Postleitzahl", "Hausnummer", "Bezirk"),
    "fr": ("Adresse", "Ville", "Région", "Code postal", "Numéro", "Quartier"),
    "pt": ("Endereço", "Cidade", "Região", "Código postal", "Número", "Bairro"),
    "ja": ("住所", "市区町村", "地域", "郵便番号", "番地", "地区"),
    "zh": ("街道地址", "城市", "地区", "邮编", "门牌号", "区域"),
    "zh-Hant": ("街道地址", "城市", "地區", "郵遞區號", "門牌號", "區域"),
}

# Country words that the generic line does not say.
_LABELS = {
    "en": {
        "CN": {"line": "Street address", "city": "City", "region": "Province", "postal": "Postal code", "district": "District"},
        "TW": {"region": "County / city", "district": "District", "postal": "Postal code"},
        "HK": {"region": "Region", "district": "District", "line": "Street address"},
        "MO": {"region": "Parish", "line": "Street address"},
        "SG": {"line": "Street address", "postal": "Postal code"},
        "AU": {"city": "Suburb", "region": "State", "postal": "Postcode"},
        "NZ": {"city": "Town", "postal": "Postcode"},
        "KR": {"region": "Province", "city": "City", "postal": "Postal code"},
        "IN": {"region": "State", "postal": "PIN code"},
        "IT": {"region": "Province", "postal": "Postcode"},
        "NL": {"line": "Street", "number": "House number", "postal": "Postcode"},
        "IE": {"city": "Town", "postal": "Eircode"},
        "CH": {"region": "Canton", "postal": "Postcode"},
        "AE": {"region": "Emirate"},
    },
    "zh": {
        "CN": {"line": "详细地址", "city": "城市", "region": "省 / 直辖市", "postal": "邮政编码", "district": "区 / 县"},
        "TW": {"city": "县市", "district": "区", "postal": "邮编", "line": "街道地址"},
        "HK": {"region": "地域", "district": "地区", "line": "街道"},
        "MO": {"region": "堂区", "line": "街道"},
        "SG": {"line": "街道", "postal": "邮编"},
        "KR": {"region": "道 / 市", "city": "市", "postal": "邮编", "line": "街道"},
        "JP": {"line": "番地", "city": "市区町村", "region": "都道府县", "postal": "邮编"},
    },
    "zh-Hant": {
        "CN": {"line": "詳細地址", "city": "城市", "region": "省 / 直轄市", "postal": "郵政編碼", "district": "區 / 縣"},
        "TW": {"city": "縣市", "district": "區", "postal": "郵遞區號", "line": "街道地址"},
        "HK": {"region": "地域", "district": "地區", "line": "街道"},
        "MO": {"region": "堂區", "line": "街道"},
    },
}

_HINT = {
    "en": {
        "US": "Street, then city, state, and ZIP.",
        "CA": "Street, then city, province, and postal code.",
        "GB": "Street and town, then the postcode.",
        "DE": "Street and number, then postcode and city.",
        "FR": "Street, then postcode and city.",
        "ES": "Street, then postcode, city, and province.",
        "PT": "Street, then postcode and city.",
        "BR": "CEP first. Then the street, number, and neighborhood.",
        "MX": "Postal code first, then the street and the colonia.",
        "JP": "Postal code first. Then prefecture, city, and the block.",
        "CN": "Choose the province, city, and district. Type the street underneath.",
        "TW": "Postal code, city, and district, then the street.",
        "HK": "Region and district, then the street. No postal code.",
        "MO": "Parish, then the street.",
        "SG": "Street, then the postal code.",
        "AU": "Street, suburb, state, and postcode.",
        "KR": "Postal code first, then province, city, and street.",
        "IN": "Street, city, state, and PIN code.",
        "NL": "Postcode and house number, then the street and city.",
        "IT": "Street, then postcode and city.",
        "IE": "Street and town, then the Eircode.",
        "AE": "Street, city, and emirate.",
        "*": "Street, city, and postal code.",
    },
    "zh": {
        "CN": "省、市、区从名单里选，下面的详细地址再手写。",
        "TW": "先写邮编，再写县市、区和街道。",
        "HK": "先选地域和地区，再写街道。香港地址不用邮编。",
        "JP": "先写邮编，再选都道府县和市区町村，最后写番地。",
        "US": "先写街道，再选州和城市，最后写邮编。",
        "GB": "先写街道和城镇，再写邮编。",
        "BR": "先写邮编，再写街道、门牌和街区。",
        "DE": "先写街道和门牌，再写邮编和城市。",
        "*": "按这个国家的习惯填写街道、城市和邮编。",
    },
    "zh-Hant": {
        "TW": "先寫郵遞區號，再寫縣市、區和街道。",
        "HK": "先選地域和地區，再寫街道。",
        "CN": "省、市、區從名單裡選，下面的詳細地址再手寫。",
        "*": "依這個國家的習慣填寫街道、城市和郵遞區號。",
    },
    "ja": {
        "JP": "郵便番号、都道府県、市区町村、番地の順です。",
        "*": "その国の書き方で住所を入れます。",
    },
    "de": {
        "DE": "Straße und Hausnummer, dann Postleitzahl und Ort.",
        "AT": "Straße und Hausnummer, dann Postleitzahl und Ort.",
        "*": "Straße, Ort und Postleitzahl.",
    },
    "fr": {
        "FR": "Rue, puis code postal et ville.",
        "*": "Rue, ville et code postal.",
    },
    "es": {
        "ES": "Calle, luego código postal y ciudad.",
        "MX": "Primero el código postal, luego la calle y la colonia.",
        "*": "Calle, ciudad y código postal.",
    },
    "pt": {
        "BR": "Primeiro o CEP. Depois a rua, o número e o bairro.",
        "PT": "Rua, depois o código postal e a cidade.",
        "*": "Rua, cidade e código postal.",
    },
}

_PLACE = {
    "CN": {"en": "China", "zh": "中国", "zh-Hant": "中國", "ja": "中国"},
    "TW": {"en": "Taiwan", "zh": "台湾", "zh-Hant": "台灣"},
    "HK": {"en": "Hong Kong", "zh": "香港", "zh-Hant": "香港"},
    "MO": {"en": "Macau", "zh": "澳门", "zh-Hant": "澳門"},
    "SG": {"en": "Singapore", "zh": "新加坡", "zh-Hant": "新加坡"},
    "AU": {"en": "Australia", "zh": "澳大利亚", "zh-Hant": "澳洲"},
    "NZ": {"en": "New Zealand", "zh": "新西兰"},
    "KR": {"en": "South Korea", "zh": "韩国", "ja": "韓国"},
    "IN": {"en": "India", "zh": "印度"},
    "IT": {"en": "Italy", "zh": "意大利", "de": "Italien", "fr": "Italie"},
    "NL": {"en": "Netherlands", "zh": "荷兰", "de": "Niederlande"},
    "IE": {"en": "Ireland", "zh": "爱尔兰"},
    "AT": {"en": "Austria", "de": "Österreich", "zh": "奥地利"},
    "BE": {"en": "Belgium", "fr": "Belgique", "de": "Belgien", "zh": "比利时"},
    "CH": {"en": "Switzerland", "de": "Schweiz", "fr": "Suisse", "zh": "瑞士"},
    "SE": {"en": "Sweden", "zh": "瑞典"},
    "NO": {"en": "Norway", "zh": "挪威"},
    "DK": {"en": "Denmark", "zh": "丹麦"},
    "FI": {"en": "Finland", "zh": "芬兰"},
    "PL": {"en": "Poland", "zh": "波兰"},
    "AE": {"en": "United Arab Emirates", "zh": "阿联酋"},
}

# (stored value, English name, Chinese name). The stored value is what a local carrier reads.
_EXTRA_REGIONS = {
    "CN": [
        ("北京市", "Beijing", "北京市"),
        ("天津市", "Tianjin", "天津市"),
        ("河北省", "Hebei", "河北省"),
        ("山西省", "Shanxi", "山西省"),
        ("内蒙古自治区", "Inner Mongolia", "内蒙古自治区"),
        ("辽宁省", "Liaoning", "辽宁省"),
        ("吉林省", "Jilin", "吉林省"),
        ("黑龙江省", "Heilongjiang", "黑龙江省"),
        ("上海市", "Shanghai", "上海市"),
        ("江苏省", "Jiangsu", "江苏省"),
        ("浙江省", "Zhejiang", "浙江省"),
        ("安徽省", "Anhui", "安徽省"),
        ("福建省", "Fujian", "福建省"),
        ("江西省", "Jiangxi", "江西省"),
        ("山东省", "Shandong", "山东省"),
        ("河南省", "Henan", "河南省"),
        ("湖北省", "Hubei", "湖北省"),
        ("湖南省", "Hunan", "湖南省"),
        ("广东省", "Guangdong", "广东省"),
        ("广西壮族自治区", "Guangxi", "广西壮族自治区"),
        ("海南省", "Hainan", "海南省"),
        ("重庆市", "Chongqing", "重庆市"),
        ("四川省", "Sichuan", "四川省"),
        ("贵州省", "Guizhou", "贵州省"),
        ("云南省", "Yunnan", "云南省"),
        ("西藏自治区", "Tibet", "西藏自治区"),
        ("陕西省", "Shaanxi", "陕西省"),
        ("甘肃省", "Gansu", "甘肃省"),
        ("青海省", "Qinghai", "青海省"),
        ("宁夏回族自治区", "Ningxia", "宁夏回族自治区"),
        ("新疆维吾尔自治区", "Xinjiang", "新疆维吾尔自治区"),
    ],
    "HK": [
        ("香港島", "Hong Kong Island", "香港岛"),
        ("九龍", "Kowloon", "九龙"),
        ("新界", "New Territories", "新界"),
    ],
    "MO": [
        ("澳門半島", "Macau Peninsula", "澳门半岛"),
        ("氹仔", "Taipa", "氹仔"),
        ("路環", "Coloane", "路环"),
    ],
    "TW": [
        ("臺北市", "Taipei City", "台北市"),
        ("新北市", "New Taipei", "新北市"),
        ("桃園市", "Taoyuan", "桃园市"),
        ("臺中市", "Taichung", "台中市"),
        ("臺南市", "Tainan", "台南市"),
        ("高雄市", "Kaohsiung", "高雄市"),
        ("基隆市", "Keelung", "基隆市"),
        ("新竹市", "Hsinchu City", "新竹市"),
        ("嘉義市", "Chiayi City", "嘉义市"),
        ("新竹縣", "Hsinchu County", "新竹县"),
        ("苗栗縣", "Miaoli", "苗栗县"),
        ("彰化縣", "Changhua", "彰化县"),
        ("南投縣", "Nantou", "南投县"),
        ("雲林縣", "Yunlin", "云林县"),
        ("嘉義縣", "Chiayi County", "嘉义县"),
        ("屏東縣", "Pingtung", "屏东县"),
        ("宜蘭縣", "Yilan", "宜兰县"),
        ("花蓮縣", "Hualien", "花莲县"),
        ("臺東縣", "Taitung", "台东县"),
        ("澎湖縣", "Penghu", "澎湖县"),
        ("金門縣", "Kinmen", "金门县"),
        ("連江縣", "Lienchiang", "连江县"),
    ],
    "AU": [
        ("NSW", "New South Wales", "新南威尔士"),
        ("VIC", "Victoria", "维多利亚"),
        ("QLD", "Queensland", "昆士兰"),
        ("SA", "South Australia", "南澳"),
        ("WA", "Western Australia", "西澳"),
        ("TAS", "Tasmania", "塔斯马尼亚"),
        ("NT", "Northern Territory", "北领地"),
        ("ACT", "Australian Capital Territory", "首都领地"),
    ],
    "KR": [
        ("서울특별시", "Seoul", "首尔"),
        ("부산광역시", "Busan", "釜山"),
        ("대구광역시", "Daegu", "大邱"),
        ("인천광역시", "Incheon", "仁川"),
        ("광주광역시", "Gwangju", "光州"),
        ("대전광역시", "Daejeon", "大田"),
        ("울산광역시", "Ulsan", "蔚山"),
        ("세종특별자치시", "Sejong", "世宗"),
        ("경기도", "Gyeonggi", "京畿"),
        ("강원특별자치도", "Gangwon", "江原"),
        ("충청북도", "North Chungcheong", "忠北"),
        ("충청남도", "South Chungcheong", "忠南"),
        ("전북특별자치도", "North Jeolla", "全北"),
        ("전라남도", "South Jeolla", "全南"),
        ("경상북도", "North Gyeongsang", "庆北"),
        ("경상남도", "South Gyeongsang", "庆南"),
        ("제주특별자치도", "Jeju", "济州"),
    ],
    "AE": [
        ("Abu Dhabi", "Abu Dhabi", "阿布扎比"),
        ("Dubai", "Dubai", "迪拜"),
        ("Sharjah", "Sharjah", "沙迦"),
        ("Ajman", "Ajman", "阿治曼"),
        ("Umm Al Quwain", "Umm Al Quwain", "乌姆盖万"),
        ("Ras Al Khaimah", "Ras Al Khaimah", "拉斯海玛"),
        ("Fujairah", "Fujairah", "富查伊拉"),
    ],
    "IN": [
        ("Andhra Pradesh", "Andhra Pradesh", "安得拉"),
        ("Arunachal Pradesh", "Arunachal Pradesh", "阿鲁纳恰尔"),
        ("Assam", "Assam", "阿萨姆"),
        ("Bihar", "Bihar", "比哈尔"),
        ("Chhattisgarh", "Chhattisgarh", "恰蒂斯加尔"),
        ("Goa", "Goa", "果阿"),
        ("Gujarat", "Gujarat", "古吉拉特"),
        ("Haryana", "Haryana", "哈里亚纳"),
        ("Himachal Pradesh", "Himachal Pradesh", "喜马偕尔"),
        ("Jharkhand", "Jharkhand", "贾坎德"),
        ("Karnataka", "Karnataka", "卡纳塔克"),
        ("Kerala", "Kerala", "喀拉拉"),
        ("Madhya Pradesh", "Madhya Pradesh", "中央邦"),
        ("Maharashtra", "Maharashtra", "马哈拉施特拉"),
        ("Manipur", "Manipur", "曼尼普尔"),
        ("Meghalaya", "Meghalaya", "梅加拉亚"),
        ("Mizoram", "Mizoram", "米佐拉姆"),
        ("Nagaland", "Nagaland", "那加兰"),
        ("Odisha", "Odisha", "奥迪沙"),
        ("Punjab", "Punjab", "旁遮普"),
        ("Rajasthan", "Rajasthan", "拉贾斯坦"),
        ("Sikkim", "Sikkim", "锡金"),
        ("Tamil Nadu", "Tamil Nadu", "泰米尔纳德"),
        ("Telangana", "Telangana", "特伦甘纳"),
        ("Tripura", "Tripura", "特里普拉"),
        ("Uttar Pradesh", "Uttar Pradesh", "北方邦"),
        ("Uttarakhand", "Uttarakhand", "北阿坎德"),
        ("West Bengal", "West Bengal", "西孟加拉"),
        ("Delhi", "Delhi", "德里"),
        ("Jammu and Kashmir", "Jammu and Kashmir", "查谟和克什米尔"),
        ("Ladakh", "Ladakh", "拉达克"),
        ("Chandigarh", "Chandigarh", "昌迪加尔"),
        ("Puducherry", "Puducherry", "本地治里"),
    ],
}


def _lang_key(lang):
    text = str(lang or "en").lower().replace("_", "-")
    if text.startswith("zh-hant") or text.startswith("zh-tw") or text.startswith("zh-hk"):
        return "zh-Hant"
    if text.startswith("zh"):
        return "zh"
    return text.split("-", 1)[0]


def _words(lang, code):
    table = _TEXT.get(lang) or {}
    if code in table:
        return table[code]
    home = _DEST_LANG.get(code)
    if home and home in _TEXT and code in _TEXT[home]:
        return _TEXT[home][code]
    generic = _GENERIC.get(lang) or _GENERIC["en"]
    labels = dict(zip(_KEYS, generic))
    extra = (_LABELS.get(lang) or {}).get(code) or (_LABELS.get("en") or {}).get(code) or {}
    labels.update(extra)
    return tuple(labels[key] for key in _KEYS)


def _hint(lang, code):
    table = _HINT.get(lang) or {}
    return table.get(code) or table.get("*") or _HINT["en"].get(code) or _HINT["en"]["*"]


def _place(lang, code):
    row = _PLACE.get(code) or {}
    return row.get(lang) or row.get("en") or ""


def field_order(country):
    code = (country or "").strip().upper()
    return list(ORDER.get(code) or DEFAULT_ORDER)


def required_keys(country):
    """Checkout fields this country actually writes. Hidden lines are not required."""
    order = field_order(country)
    keys = ["email", "name", "address", "phone", "ship_country"]
    if "city" in order:
        keys.append("city")
    if "region" in order:
        keys.append("region")
    if "postal" in order:
        keys.append("postal")
    return keys


def extra_required(country):
    order = field_order(country)
    keys = []
    if "number" in order:
        keys.append("street_number")
    if "district" in order:
        keys.append("district")
    return keys


def formats_for(lang):
    key = _lang_key(lang)
    packed = {}
    for code, order in ORDER.items():
        labels = dict(zip(_KEYS, _words(key, code)))
        entry = {"order": list(order), "labels": labels, "hint": _hint(key, code)}
        place = _place(key, code)
        if place:
            entry["place"] = place
        if code == "CA":
            french = _TEXT["fr"]["CA"]
            entry["regions"] = {"QC": dict(zip(_KEYS, french if key == "fr" else _words(key, code)))}
        packed[code] = entry
    packed["*"] = {
        "order": list(DEFAULT_ORDER),
        "labels": dict(zip(_KEYS, _GENERIC.get(key) or _GENERIC["en"])),
        "hint": _hint(key, "*"),
    }
    return packed


def extra_regions(country, lang=""):
    """Province list for countries that have no city file. Empty when divisions.json covers it."""
    rows = _EXTRA_REGIONS.get((country or "").strip().upper()) or []
    key = _lang_key(lang)
    out = []
    for value, en_name, zh_name in rows:
        if key == "zh":
            name = zh_name or en_name
        elif key == "zh-Hant":
            name = value if any("\u4e00" <= ch <= "\u9fff" for ch in value) else (zh_name or en_name)
        else:
            name = en_name or value
        out.append({"code": value, "name": name, "en": en_name or value})
    return out


def compose_street(country, street, number, district):
    street = (street or "").strip()
    number = (number or "").strip()
    district = (district or "").strip()
    country = (country or "").upper()
    order = field_order(country)
    if country == "BR":
        line = f"{street}, {number}" if street and number else street or number
        if district:
            line = f"{line}\n{district}" if line else district
        return line
    if number and "number" in order:
        street = f"{street} {number}".strip() if street else number
    if district and "district" in order:
        if country == "MX":
            return f"{street}\n{district}" if street else district
        return f"{district}\n{street}" if street else district
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
    elif country == "CN":
        lines = [name, phone, f"{region}{city}", street, postal]
    elif country == "HK":
        lines = [name, " ".join(part for part in (region, street) if part), phone]
    elif country == "TW":
        lines = [postal, f"{city}", street, name, phone]
    elif country == "SG":
        lines = [name, street, " ".join(part for part in (city or "Singapore", postal) if part), phone]
    elif country == "US":
        lines = [name, street, " ".join(part for part in (f"{city}, {region}".strip(", "), postal) if part), phone]
    elif country == "CA":
        lines = [name, street, " ".join(part for part in (city, region, postal) if part), phone]
    elif country == "GB":
        lines = [name, street, city, postal, phone]
    elif country in {"DE", "AT", "CH", "NL", "BE", "FR"}:
        lines = [name, street, " ".join(part for part in (postal, city) if part), phone]
    elif country in {"ES", "PT", "IT", "PL", "SE", "NO", "DK", "FI"}:
        lines = [name, street, " ".join(part for part in (postal, city) if part), region, phone]
    elif country == "BR":
        lines = [name, street, " - ".join(part for part in (city, region) if part), postal, phone]
    elif country == "MX":
        lines = [name, street, ", ".join(part for part in (city, region) if part), postal, phone]
    elif country == "AU":
        lines = [name, street, " ".join(part for part in (city, region, postal) if part), phone]
    elif country == "KR":
        lines = [f"{postal}" if postal else "", f"{region} {city}".strip(), street, name, phone]
    else:
        lines = [name, street, " ".join(part for part in (city, region, postal) if part), phone]
    return [line for line in lines if line]
