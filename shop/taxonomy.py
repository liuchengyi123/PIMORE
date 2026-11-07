import re

from shop.i18n import CATEGORIES

HOME_FACE = ("kitchen", "tableware", "cleaning", "storage", "personal", "pet", "daily")

ZH = {
    "daily": "居家日用",
    "kitchen": "厨房烹饪",
    "tableware": "餐饮具",
    "storage": "收纳整理",
    "cleaning": "家居清洁",
    "paper": "纸品卫生香氛",
    "personal": "个人护理",
    "beauty": "美容护肤",
    "makeup": "彩妆香水",
    "textile": "家纺布艺",
    "decor": "家居软饰",
    "appliance": "家居电器",
    "hardware": "五金工具",
    "pet": "宠物用品",
    "office": "文化办公学习",
    "party": "节庆装饰礼品",
}

CHILDREN = {
    "daily": ("hangers", "rain", "warmth", "shoecare", "gloves"),
    "kitchen": ("cookware", "gadgets", "bakeware", "drinkware", "foodkeep"),
    "tableware": ("dishes", "cutlery", "teaware"),
    "storage": ("boxes", "closet", "hooks", "drawers", "shelves"),
    "cleaning": ("cleantools", "laundry", "bathclean", "trash"),
    "paper": ("tissue", "sanitary", "scent", "repellent"),
    "personal": ("bath", "hair", "oral", "shave"),
    "beauty": ("skin", "mask", "body"),
    "makeup": ("color", "perfume", "mtools"),
    "textile": ("towel", "bedding", "curtain", "cushion"),
    "decor": ("ornament", "wall", "vase"),
    "appliance": ("fan", "humidity", "heat"),
    "hardware": ("handtool", "lock", "measure", "tape"),
    "pet": ("feeding", "toys", "groom", "waste", "beds"),
    "office": ("writing", "notepaper", "files", "correct", "organize", "light", "stands", "cables"),
    "party": ("holiday", "giftbox", "festive"),
}

LABELS = {
    "zh": {
        "hangers": "衣架晾晒", "rain": "雨具", "warmth": "暖贴热水袋", "shoecare": "鞋护理", "gloves": "手套防护",
        "cookware": "锅具", "gadgets": "厨具小件", "bakeware": "烘焙", "drinkware": "杯壶", "foodkeep": "保鲜盒",
        "dishes": "碗盘", "cutlery": "筷勺", "teaware": "茶咖具",
        "boxes": "收纳盒", "closet": "衣柜", "hooks": "挂钩", "drawers": "抽屉", "shelves": "置物架",
        "cleantools": "清洁工具", "laundry": "洗衣", "bathclean": "浴室清洁", "trash": "垃圾",
        "tissue": "纸品湿巾", "sanitary": "卫生巾", "scent": "香薰除味", "repellent": "驱蚊",
        "bath": "沐浴", "hair": "头发", "oral": "口腔", "shave": "剃须",
        "skin": "护肤", "mask": "面膜", "body": "精油美体",
        "color": "彩妆", "perfume": "香水", "mtools": "美妆工具",
        "towel": "毛巾浴巾", "bedding": "床品", "curtain": "窗帘", "cushion": "坐垫桌布",
        "ornament": "摆件", "wall": "挂画", "vase": "花器",
        "fan": "风扇", "humidity": "加湿器", "heat": "小电热",
        "handtool": "手动工具", "lock": "锁具配件", "measure": "测量", "tape": "胶带",
        "feeding": "喂食", "toys": "玩具", "groom": "护理", "waste": "排泄", "beds": "窝垫",
        "writing": "书写", "notepaper": "纸本", "files": "文件", "correct": "修正",
        "organize": "桌面整理", "light": "灯", "stands": "支架", "cables": "线材",
        "holiday": "节日布置", "giftbox": "包装礼盒", "festive": "派对用品",
    },
    "en": {
        "hangers": "Hangers", "rain": "Rain", "warmth": "Warmers", "shoecare": "Shoe care", "gloves": "Gloves",
        "cookware": "Cookware", "gadgets": "Utensils", "bakeware": "Bakeware", "drinkware": "Drinkware", "foodkeep": "Food storage",
        "dishes": "Bowls and plates", "cutlery": "Chopsticks", "teaware": "Tea and coffee",
        "boxes": "Boxes", "closet": "Closet", "hooks": "Hooks", "drawers": "Drawers", "shelves": "Shelves",
        "cleantools": "Cleaning tools", "laundry": "Laundry", "bathclean": "Bathroom", "trash": "Trash",
        "tissue": "Paper", "sanitary": "Sanitary", "scent": "Fragrance", "repellent": "Repellent",
        "bath": "Bath", "hair": "Hair", "oral": "Oral", "shave": "Shave",
        "skin": "Skin", "mask": "Masks", "body": "Body oil",
        "color": "Color", "perfume": "Perfume", "mtools": "Makeup tools",
        "towel": "Towels", "bedding": "Bedding", "curtain": "Curtains", "cushion": "Cushions",
        "ornament": "Ornaments", "wall": "Wall art", "vase": "Vases",
        "fan": "Fans", "humidity": "Humidity", "heat": "Heaters",
        "handtool": "Hand tools", "lock": "Locks", "measure": "Measuring", "tape": "Tape",
        "feeding": "Feeding", "toys": "Toys", "groom": "Grooming", "waste": "Waste", "beds": "Beds",
        "writing": "Writing", "notepaper": "Paper", "files": "Files", "correct": "Corrections",
        "organize": "Organizers", "light": "Lighting", "stands": "Stands", "cables": "Cables",
        "holiday": "Holiday", "giftbox": "Gift wrap", "festive": "Party",
    },
    "es": {
        "hangers": "Perchas", "rain": "Lluvia", "warmth": "Calentadores", "shoecare": "Calzado", "gloves": "Guantes",
        "cookware": "Menaje", "gadgets": "Utensilios", "bakeware": "Repostería", "drinkware": "Bebida", "foodkeep": "Conservación",
        "dishes": "Vajilla", "cutlery": "Palillos", "teaware": "Té y café",
        "boxes": "Cajas", "closet": "Armario", "hooks": "Ganchos", "drawers": "Cajones", "shelves": "Estantes",
        "cleantools": "Limpieza", "laundry": "Lavado", "bathclean": "Baño", "trash": "Basura",
        "tissue": "Papel", "sanitary": "Higiene", "scent": "Aroma", "repellent": "Antimosquitos",
        "bath": "Baño", "hair": "Cabello", "oral": "Boca", "shave": "Afeitado",
        "skin": "Piel", "mask": "Mascarillas", "body": "Aceite corporal",
        "color": "Maquillaje", "perfume": "Perfume", "mtools": "Brochas",
        "towel": "Toallas", "bedding": "Ropa de cama", "curtain": "Cortinas", "cushion": "Cojines",
        "ornament": "Adornos", "wall": "Cuadros", "vase": "Jarrones",
        "fan": "Ventiladores", "humidity": "Humedad", "heat": "Calefacción",
        "handtool": "Herramientas", "lock": "Cerraduras", "measure": "Medición", "tape": "Cinta",
        "feeding": "Comida", "toys": "Juguetes", "groom": "Aseo", "waste": "Residuos", "beds": "Camas",
        "writing": "Escritura", "notepaper": "Papel", "files": "Archivadores", "correct": "Correcciones",
        "organize": "Organizadores", "light": "Luz", "stands": "Soportes", "cables": "Cables",
        "holiday": "Fiestas", "giftbox": "Envoltorio", "festive": "Celebración",
    },
    "de": {
        "hangers": "Bügel", "rain": "Regen", "warmth": "Wärmer", "shoecare": "Schuhpflege", "gloves": "Handschuhe",
        "cookware": "Kochgeschirr", "gadgets": "Utensilien", "bakeware": "Backen", "drinkware": "Trinken", "foodkeep": "Aufbewahrung",
        "dishes": "Geschirr", "cutlery": "Stäbchen", "teaware": "Tee und Kaffee",
        "boxes": "Boxen", "closet": "Schrank", "hooks": "Haken", "drawers": "Schubladen", "shelves": "Regale",
        "cleantools": "Reinigung", "laundry": "Wäsche", "bathclean": "Bad", "trash": "Abfall",
        "tissue": "Papier", "sanitary": "Hygiene", "scent": "Duft", "repellent": "Mückenschutz",
        "bath": "Bad", "hair": "Haar", "oral": "Mund", "shave": "Rasur",
        "skin": "Haut", "mask": "Masken", "body": "Körperöl",
        "color": "Make-up", "perfume": "Parfum", "mtools": "Pinsel",
        "towel": "Handtücher", "bedding": "Bettwäsche", "curtain": "Vorhänge", "cushion": "Kissen",
        "ornament": "Deko", "wall": "Wandbild", "vase": "Vasen",
        "fan": "Ventilatoren", "humidity": "Luftfeuchte", "heat": "Heizung",
        "handtool": "Handwerkzeug", "lock": "Schlösser", "measure": "Messen", "tape": "Klebeband",
        "feeding": "Futter", "toys": "Spielzeug", "groom": "Pflege", "waste": "Abfall", "beds": "Betten",
        "writing": "Schreiben", "notepaper": "Papier", "files": "Ablage", "correct": "Korrektur",
        "organize": "Ordnen", "light": "Licht", "stands": "Ständer", "cables": "Kabel",
        "holiday": "Fest", "giftbox": "Geschenk", "festive": "Party",
    },
    "fr": {
        "hangers": "Cintres", "rain": "Pluie", "warmth": "Chaufferettes", "shoecare": "Chaussures", "gloves": "Gants",
        "cookware": "Cuisson", "gadgets": "Ustensiles", "bakeware": "Pâtisserie", "drinkware": "Boisson", "foodkeep": "Conservation",
        "dishes": "Vaisselle", "cutlery": "Baguettes", "teaware": "Thé et café",
        "boxes": "Boîtes", "closet": "Placard", "hooks": "Crochets", "drawers": "Tiroirs", "shelves": "Étagères",
        "cleantools": "Nettoyage", "laundry": "Linge", "bathclean": "Salle de bain", "trash": "Poubelle",
        "tissue": "Papier", "sanitary": "Hygiène", "scent": "Parfum d'intérieur", "repellent": "Anti-moustiques",
        "bath": "Bain", "hair": "Cheveux", "oral": "Bouche", "shave": "Rasage",
        "skin": "Peau", "mask": "Masques", "body": "Huile corporelle",
        "color": "Maquillage", "perfume": "Parfum", "mtools": "Pinceaux",
        "towel": "Serviettes", "bedding": "Linge de lit", "curtain": "Rideaux", "cushion": "Coussins",
        "ornament": "Objets", "wall": "Tableaux", "vase": "Vases",
        "fan": "Ventilateurs", "humidity": "Humidité", "heat": "Chauffage",
        "handtool": "Outils", "lock": "Serrures", "measure": "Mesure", "tape": "Ruban",
        "feeding": "Repas", "toys": "Jouets", "groom": "Toilettage", "waste": "Déchets", "beds": "Couchage",
        "writing": "Écriture", "notepaper": "Papier", "files": "Classement", "correct": "Correction",
        "organize": "Rangement", "light": "Lumière", "stands": "Supports", "cables": "Câbles",
        "holiday": "Fêtes", "giftbox": "Cadeaux", "festive": "Soirée",
    },
    "pt": {
        "hangers": "Cabides", "rain": "Chuva", "warmth": "Aquecedores", "shoecare": "Calçados", "gloves": "Luvas",
        "cookware": "Panelas", "gadgets": "Utensílios", "bakeware": "Forno", "drinkware": "Bebidas", "foodkeep": "Potes",
        "dishes": "Pratos", "cutlery": "Hashi", "teaware": "Chá e café",
        "boxes": "Caixas", "closet": "Armário", "hooks": "Ganchos", "drawers": "Gavetas", "shelves": "Prateleiras",
        "cleantools": "Limpeza", "laundry": "Lavanderia", "bathclean": "Banheiro", "trash": "Lixo",
        "tissue": "Papel", "sanitary": "Higiene", "scent": "Aroma", "repellent": "Repelente",
        "bath": "Banho", "hair": "Cabelo", "oral": "Boca", "shave": "Barba",
        "skin": "Pele", "mask": "Máscaras", "body": "Óleo corporal",
        "color": "Maquiagem", "perfume": "Perfume", "mtools": "Pincéis",
        "towel": "Toalhas", "bedding": "Cama", "curtain": "Cortinas", "cushion": "Almofadas",
        "ornament": "Enfeites", "wall": "Quadros", "vase": "Vasos",
        "fan": "Ventiladores", "humidity": "Umidade", "heat": "Aquecimento",
        "handtool": "Ferramentas", "lock": "Fechaduras", "measure": "Medição", "tape": "Fita",
        "feeding": "Comedouro", "toys": "Brinquedos", "groom": "Higiene", "waste": "Resíduos", "beds": "Camas",
        "writing": "Escrita", "notepaper": "Papel", "files": "Pastas", "correct": "Correção",
        "organize": "Organizadores", "light": "Luz", "stands": "Suportes", "cables": "Cabos",
        "holiday": "Festas", "giftbox": "Embrulho", "festive": "Celebração",
    },
    "ja": {
        "hangers": "ハンガー", "rain": "雨具", "warmth": "カイロ", "shoecare": "靴ケア", "gloves": "手袋",
        "cookware": "鍋", "gadgets": "調理小物", "bakeware": "焼き菓子", "drinkware": "飲みもの", "foodkeep": "保存",
        "dishes": "碗皿", "cutlery": "箸", "teaware": "茶とコーヒー",
        "boxes": "ボックス", "closet": "クローゼット", "hooks": "フック", "drawers": "引き出し", "shelves": "棚",
        "cleantools": "掃除用品", "laundry": "洗濯", "bathclean": "浴室", "trash": "ごみ",
        "tissue": "紙", "sanitary": "衛生", "scent": "香り", "repellent": "防虫",
        "bath": "バス", "hair": "ヘア", "oral": "オーラル", "shave": "シェーブ",
        "skin": "スキン", "mask": "パック", "body": "ボディオイル",
        "color": "メイク", "perfume": "香水", "mtools": "ブラシ",
        "towel": "タオル", "bedding": "寝具", "curtain": "カーテン", "cushion": "クッション",
        "ornament": "置物", "wall": "ウォール", "vase": "花器",
        "fan": "扇風機", "humidity": "加湿器", "heat": "ヒーター",
        "handtool": "手工具", "lock": "錠", "measure": "測定", "tape": "テープ",
        "feeding": "ごはん", "toys": "おもちゃ", "groom": "ケア", "waste": "トイレ", "beds": "ベッド",
        "writing": "筆記", "notepaper": "紙", "files": "ファイル", "correct": "修正",
        "organize": "整理", "light": "照明", "stands": "スタンド", "cables": "ケーブル",
        "holiday": "季節", "giftbox": "ギフト", "festive": "パーティー",
    },
}

PARENT_RULES = (
    ("pet", ("宠物", "猫砂", "猫", "狗", "pet", "dog", "cat")),
    ("party", ("节庆", "婚礼", "派对", "圣诞", "气球", "礼盒", "party", "christmas")),
    ("makeup", ("彩妆", "口红", "眼影", "粉底", "香水", "化妆刷", "美妆", "makeup", "lipstick", "perfume")),
    ("beauty", ("护肤", "面膜", "精华", "精油", "乳液", "面霜", "skincare", "serum", "mask")),
    ("paper", ("卫生巾", "湿巾", "纸巾", "抽纸", "香薰", "驱蚊", "蚊香", "tissue", "wipes")),
    ("personal", ("沐浴", "洗发", "牙刷", "牙膏", "剃须", "个护", "shampoo", "tooth", "shave")),
    ("cleaning", ("清洁", "拖把", "扫把", "洗衣", "垃圾桶", "海绵", "抹布", "mop", "laundry", "sponge", "brush")),
    ("textile", ("毛巾", "浴巾", "床品", "四件套", "窗帘", "坐垫", "桌布", "towel", "curtain", "bedding")),
    ("decor", ("摆件", "挂画", "花瓶", "花器", "装饰画", "vase", "ornament")),
    ("appliance", ("风扇", "加湿器", "电热", "取暖器", "小家电", "fan", "humidifier", "heater")),
    ("hardware", ("五金", "扳手", "螺丝刀", "胶带", "锁具", "接头", "补漏", "tape", "wrench", "fitting")),
    ("office", ("文具", "中性笔", "铅笔", "笔记本", "文件夹", "桌面", "台灯", "支架", "理线", "pen", "notebook", "desk", "stationery")),
    ("tableware", ("碗", "盘", "筷", "勺", "餐具", "茶杯", "咖啡杯", "plate", "chopstick")),
    ("kitchen", ("锅", "铲", "烘焙", "厨房", "保鲜", "沥水", "kitchen", "cook", "spatula", "strainer", "sprayer")),
    ("storage", ("收纳", "置物", "挂钩", "抽屉", "衣柜", "storage", "hook", "drawer", "closet")),
    ("daily", ("衣架", "晾", "雨伞", "雨衣", "热水袋", "暖贴", "鞋垫", "手套", "hanger", "umbrella", "glove")),
)

RULES = (
    ("daily", "hangers", ("衣架", "晾", "hanger")),
    ("daily", "rain", ("雨伞", "雨衣", "雨披", "umbrella")),
    ("daily", "warmth", ("热水袋", "暖贴", "暖宝宝")),
    ("daily", "shoecare", ("鞋垫", "鞋刷", "鞋油")),
    ("daily", "gloves", ("手套", "glove")),
    ("kitchen", "cookware", ("锅", "煎锅", "炒锅", "cookware", "saucepan")),
    ("kitchen", "bakeware", ("烘焙", "烤盘", "模具", "bakeware", "baking")),
    ("kitchen", "drinkware", ("杯", "壶", "mug", "kettle", "bottle")),
    ("kitchen", "foodkeep", ("保鲜", "密封", "调味", "seasoning")),
    ("kitchen", "gadgets", ("铲", "刀", "夹", "漏", "滤", "喷", "spatula", "spoon", "strainer", "sprayer")),
    ("tableware", "teaware", ("茶", "咖啡", "tea", "coffee")),
    ("tableware", "cutlery", ("筷", "勺", "叉", "chopstick", "fork")),
    ("tableware", "dishes", ("碗", "盘", "碟", "plate", "bowl")),
    ("storage", "hooks", ("挂钩", "粘钩", "hook")),
    ("storage", "drawers", ("抽屉", "分隔", "drawer")),
    ("storage", "closet", ("衣柜", "挂袋", "closet", "hanging")),
    ("storage", "shelves", ("置物架", "层架", "shelf")),
    ("storage", "boxes", ("收纳盒", "收纳箱", "压缩", "bin", "box")),
    ("cleaning", "laundry", ("洗衣", "晾晒", "lint", "laundry")),
    ("cleaning", "trash", ("垃圾", "纸篓", "trash")),
    ("cleaning", "bathclean", ("浴室", "马桶", "toilet")),
    ("cleaning", "cleantools", ("拖把", "扫把", "刷", "海绵", "抹布", "brush", "sponge", "cloth", "dustpan")),
    ("paper", "sanitary", ("卫生巾", "护垫")),
    ("paper", "repellent", ("驱蚊", "蚊香", "防蚊")),
    ("paper", "scent", ("香薰", "除味", "香氛")),
    ("paper", "tissue", ("湿巾", "纸巾", "抽纸", "tissue", "wipe")),
    ("personal", "oral", ("牙刷", "牙膏", "tooth")),
    ("personal", "shave", ("剃须", "剃须刀", "shave")),
    ("personal", "hair", ("洗发", "头发", "发夹", "梳子", "hair", "comb", "shampoo")),
    ("personal", "bath", ("沐浴", "洗澡", "浴", "bath")),
    ("beauty", "mask", ("面膜", "mask")),
    ("beauty", "body", ("精油", "美体", "body oil")),
    ("beauty", "skin", ("护肤", "精华", "乳液", "面霜", "serum")),
    ("makeup", "perfume", ("香水", "perfume")),
    ("makeup", "mtools", ("化妆刷", "美妆工具", "粉扑", "brush")),
    ("makeup", "color", ("口红", "眼影", "粉底", "彩妆", "lipstick")),
    ("textile", "towel", ("毛巾", "浴巾", "towel")),
    ("textile", "bedding", ("床品", "四件套", "枕", "bedding")),
    ("textile", "curtain", ("窗帘", "curtain")),
    ("textile", "cushion", ("坐垫", "桌布", "靠垫", "cushion")),
    ("decor", "vase", ("花瓶", "花器", "vase")),
    ("decor", "wall", ("挂画", "装饰画", "wall")),
    ("decor", "ornament", ("摆件", "摆设", "ornament")),
    ("appliance", "fan", ("风扇", "fan")),
    ("appliance", "humidity", ("加湿", "humidifier")),
    ("appliance", "heat", ("电热", "取暖", "heater")),
    ("hardware", "tape", ("胶带", "补漏", "tape")),
    ("hardware", "lock", ("锁", "合页", "lock")),
    ("hardware", "measure", ("卷尺", "测量", "measure")),
    ("hardware", "handtool", ("扳手", "螺丝刀", "钳", "五金", "wrench")),
    ("pet", "toys", ("玩具", "球", "toy", "ball")),
    ("pet", "groom", ("梳毛", "护理", "手套", "groom", "glove")),
    ("pet", "waste", ("拾便", "猫砂", "排泄", "waste", "litter")),
    ("pet", "feeding", ("喂", "食盆", "水盆", "bowl", "lick")),
    ("pet", "beds", ("窝", "宠物床", "bed")),
    ("office", "cables", ("线", "理线", "cable")),
    ("office", "stands", ("支架", "手机架", "stand")),
    ("office", "light", ("台灯", "灯", "lamp", "light")),
    ("office", "correct", ("修正", "橡皮", "eraser")),
    ("office", "files", ("文件夹", "文件袋", "folder")),
    ("office", "notepaper", ("笔记本", "便签", "纸", "notebook", "note")),
    ("office", "writing", ("笔", "铅笔", "中性笔", "pen", "pencil")),
    ("office", "organize", ("笔筒", "收纳", "桌面", "organizer", "clip")),
    ("party", "giftbox", ("礼盒", "包装", "gift")),
    ("party", "holiday", ("圣诞", "春节", "节日", "christmas")),
    ("party", "festive", ("派对", "气球", "party", "balloon")),
)

MOVED = {
    ("kitchen", "tableware"): ("tableware", ""),
    ("personal", "skin"): ("beauty", "skin"),
    ("cleaning", "air"): ("paper", "scent"),
    ("stationery", "paper"): ("office", "notepaper"),
    ("stationery", "writing"): ("office", "writing"),
    ("stationery", "files"): ("office", "files"),
    ("stationery", "correct"): ("office", "correct"),
    ("desk", "organize"): ("office", "organize"),
    ("desk", "light"): ("office", "light"),
    ("desk", "stands"): ("office", "stands"),
    ("desk", "cables"): ("office", "cables"),
}

RETIRED = {"desk": "office", "stationery": "office"}


def children(category):
    return CHILDREN.get(category, ())


def known(category, slug):
    return slug in children(category)


def labels_for(lang):
    return LABELS.get(lang) or LABELS["en"]


def _has(hay, word):
    token = word.lower()
    if re.search(r"[a-z]", token):
        return re.search(rf"(?<![a-z]){re.escape(token)}(?![a-z])", hay) is not None
    return token in hay


def guess_parent(text):
    hay = str(text or "").lower()
    if not hay.strip():
        return ""
    for parent, words in PARENT_RULES:
        if any(_has(hay, word) for word in words):
            return parent
    return ""


def guess(category, text):
    hay = str(text or "").lower()
    if not hay.strip():
        return ""
    for parent, slug, words in RULES:
        if parent != category:
            continue
        if any(_has(hay, word) for word in words):
            return slug
    return ""


def rehome(conn):
    rows = conn.execute(
        "select sku, category, subcategory, names, source_zh from products"
    ).fetchall()
    for row in rows:
        category = row["category"] or ""
        sub = row["subcategory"] or ""
        moved = MOVED.get((category, sub))
        if moved:
            category, sub = moved
        elif category in RETIRED:
            category = RETIRED[category]
            sub = ""
        text = f"{row['source_zh'] or ''} {row['names'] or ''}"
        parent = guess_parent(text)
        if category not in CATEGORIES:
            category = parent or "daily"
            sub = ""
        elif category == "storage" and not sub:
            category = parent or "daily"
        elif category == "daily" and parent and parent != "daily":
            category = parent
            sub = ""
        if not known(category, sub):
            sub = guess(category, text)
        if category != (row["category"] or "") or sub != (row["subcategory"] or ""):
            conn.execute(
                "update products set category = ?, subcategory = ? where sku = ?",
                (category, sub, row["sku"]),
            )


def fill_subs(conn):
    rows = conn.execute(
        "select sku, category, names, source_zh from products where subcategory = ''"
    ).fetchall()
    for row in rows:
        slug = guess(row["category"], f"{row['source_zh'] or ''} {row['names'] or ''}")
        if not slug:
            continue
        conn.execute("update products set subcategory = ? where sku = ?", (slug, row["sku"]))
