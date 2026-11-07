import json

from shop.campaigns import ensure_campaigns
from shop.db import migrate
from shop.staff import ensure_admin
from shop.taxonomy import fill_subs, rehome

NAMES = {
    "oil-sprayer": {"en": "Oil sprayer", "es": "Pulverizador de aceite", "de": "Ölsprüher", "fr": "Vaporisateur d'huile", "pt": "Borrifador de óleo", "ja": "オイルスプレー"},
    "drain-rack": {"en": "Dish rack", "es": "Escurridor de platos", "de": "Geschirrständer", "fr": "Égouttoir à vaisselle", "pt": "Escorredor de pratos", "ja": "水切りラック"},
    "silicone-spatula": {"en": "Silicone spatula", "es": "Espátula de silicona", "de": "Silikonspatel", "fr": "Spatule en silicone", "pt": "Espátula de silicone", "ja": "シリコンヘラ"},
    "seasoning-box": {"en": "Seasoning box", "es": "Especiero", "de": "Gewürzbox", "fr": "Boîte à épices", "pt": "Porta-temperos", "ja": "調味料ケース"},
    "measuring-spoons": {"en": "Measuring spoons", "es": "Cucharas medidoras", "de": "Messlöffel", "fr": "Cuillères doseuses", "pt": "Colheres medidoras", "ja": "計量スプーン"},
    "sink-strainer": {"en": "Sink strainer", "es": "Filtro de fregadero", "de": "Abflusssieb", "fr": "Filtre d'évier", "pt": "Filtro de pia", "ja": "排水口ゴミ受け"},
    "lint-roller": {"en": "Lint roller", "es": "Rodillo quitapelusas", "de": "Fusselroller", "fr": "Rouleau anti-peluches", "pt": "Rolo tira-pelos", "ja": "粘着クリーナー"},
    "gap-brush": {"en": "Gap brush", "es": "Cepillo para rendijas", "de": "Fugenbürste", "fr": "Brosse pour interstices", "pt": "Escova para frestas", "ja": "すき間ブラシ"},
    "sponge-refill": {"en": "Sponge refill", "es": "Recambio de esponja", "de": "Schwamm-Nachfüllpack", "fr": "Recharge d'éponge", "pt": "Refil de esponja", "ja": "スポンジ詰め替え"},
    "cleaning-cloth": {"en": "Cleaning cloth", "es": "Paño de limpieza", "de": "Reinigungstuch", "fr": "Chiffon de nettoyage", "pt": "Pano de limpeza", "ja": "掃除クロス"},
    "pot-brush": {"en": "Pot brush", "es": "Cepillo para ollas", "de": "Topfbürste", "fr": "Brosse à casseroles", "pt": "Escova para panelas", "ja": "鍋ブラシ"},
    "dustpan-set": {"en": "Dustpan set", "es": "Recogedor con escoba", "de": "Kehrset", "fr": "Pelle et balayette", "pt": "Pá com vassoura", "ja": "ほうき・ちりとり"},
    "adhesive-hooks": {"en": "Adhesive hooks", "es": "Ganchos adhesivos", "de": "Klebehaken", "fr": "Crochets adhésifs", "pt": "Ganchos adesivos", "ja": "貼ってはがせるフック"},
    "vacuum-bag": {"en": "Vacuum storage bag", "es": "Bolsa al vacío", "de": "Vakuumbeutel", "fr": "Sac de compression", "pt": "Saco a vácuo", "ja": "圧縮袋"},
    "drawer-divider": {"en": "Drawer divider", "es": "Separador de cajón", "de": "Schubladenteiler", "fr": "Séparateur de tiroir", "pt": "Divisor de gaveta", "ja": "引き出し仕切り"},
    "gap-shelf": {"en": "Gap shelf", "es": "Estante para huecos", "de": "Nischenregal", "fr": "Étagère pour interstice", "pt": "Prateleira para vão", "ja": "すき間ラック"},
    "closet-organizer": {"en": "Closet hanging organizer", "es": "Organizador colgante", "de": "Hängender Schrank-Organizer", "fr": "Organiseur à suspendre", "pt": "Organizador de pendurar", "ja": "吊り下げ収納"},
    "folding-bin": {"en": "Folding storage bin", "es": "Caja plegable", "de": "Faltbox", "fr": "Bac pliable", "pt": "Caixa dobrável", "ja": "折りたたみ収納ボックス"},
    "comb": {"en": "Comb", "es": "Peine", "de": "Kamm", "fr": "Peigne", "pt": "Pente", "ja": "くし"},
    "hair-clips": {"en": "Hair clips", "es": "Horquillas", "de": "Haarklammern", "fr": "Pinces à cheveux", "pt": "Prendedores de cabelo", "ja": "ヘアクリップ"},
    "bath-sponge": {"en": "Bath sponge", "es": "Esponja de baño", "de": "Badeschwamm", "fr": "Éponge de bain", "pt": "Esponja de banho", "ja": "ボディスポンジ"},
    "nail-clipper": {"en": "Nail clipper", "es": "Cortaúñas", "de": "Nagelknipser", "fr": "Coupe-ongles", "pt": "Cortador de unhas", "ja": "爪切り"},
    "cotton-pad-box": {"en": "Cotton pad box", "es": "Caja para discos de algodón", "de": "Box für Wattepads", "fr": "Boîte à cotons", "pt": "Caixa para discos de algodão", "ja": "コットンケース"},
    "toothbrush-holder": {"en": "Toothbrush holder", "es": "Portacepillos", "de": "Zahnbürstenhalter", "fr": "Porte-brosses à dents", "pt": "Porta-escovas", "ja": "歯ブラシスタンド"},
    "pet-lint-roller": {"en": "Pet lint roller", "es": "Rodillo quitapelos de mascota", "de": "Fusselroller für Tierhaare", "fr": "Rouleau anti-poils d'animaux", "pt": "Rolo tira-pelos de pet", "ja": "ペット用粘着クリーナー"},
    "waste-bag-holder": {"en": "Waste bag holder", "es": "Dispensador de bolsas", "de": "Beutelspender", "fr": "Distributeur de sacs", "pt": "Porta-sacos", "ja": "マナー袋ホルダー"},
    "folding-bowl": {"en": "Folding pet bowl", "es": "Cuenco plegable", "de": "Faltnapf", "fr": "Gamelle pliable", "pt": "Tigela dobrável", "ja": "折りたたみフードボウル"},
    "lick-mat": {"en": "Lick mat", "es": "Alfombra para lamer", "de": "Schleckmatte", "fr": "Tapis à lécher", "pt": "Tapete de lamber", "ja": "リックマット"},
    "toy-ball": {"en": "Toy ball", "es": "Pelota", "de": "Spielball", "fr": "Balle", "pt": "Bola", "ja": "おもちゃボール"},
    "grooming-glove": {"en": "Grooming glove", "es": "Guante de cepillado", "de": "Fellpflegehandschuh", "fr": "Gant de toilettage", "pt": "Luva de escovação", "ja": "グルーミンググローブ"},
    "pen-cup": {"en": "Pen cup", "es": "Portalápices", "de": "Stifteköcher", "fr": "Pot à crayons", "pt": "Porta-canetas", "ja": "ペンスタンド"},
    "binder-clip": {"en": "Binder clips", "es": "Pinzas", "de": "Foldbackklammern", "fr": "Pinces double clip", "pt": "Prendedores", "ja": "バインダークリップ"},
    "phone-stand": {"en": "Phone stand", "es": "Soporte para móvil", "de": "Handyhalter", "fr": "Support de téléphone", "pt": "Suporte para celular", "ja": "スマホスタンド"},
    "desk-organizer": {"en": "Desk organizer", "es": "Organizador de escritorio", "de": "Schreibtisch-Organizer", "fr": "Organiseur de bureau", "pt": "Organizador de mesa", "ja": "デスクオーガナイザー"},
    "cable-clip": {"en": "Cable clips", "es": "Clips para cables", "de": "Kabelclips", "fr": "Clips pour câbles", "pt": "Clipes de cabo", "ja": "ケーブルクリップ"},
    "note-holder": {"en": "Note holder", "es": "Soporte para notas", "de": "Zettelhalter", "fr": "Porte-notes", "pt": "Porta-recados", "ja": "メモスタンド"},
}

PRODUCTS = [
    ("oil-sprayer", "kitchen", 800),
    ("drain-rack", "kitchen", 1200),
    ("silicone-spatula", "kitchen", 600),
    ("seasoning-box", "kitchen", 900),
    ("measuring-spoons", "kitchen", 500),
    ("sink-strainer", "kitchen", 400),
    ("lint-roller", "cleaning", 700),
    ("gap-brush", "cleaning", 600),
    ("sponge-refill", "cleaning", 500),
    ("cleaning-cloth", "cleaning", 400),
    ("pot-brush", "cleaning", 500),
    ("dustpan-set", "cleaning", 800),
    ("adhesive-hooks", "storage", 600),
    ("vacuum-bag", "storage", 900),
    ("drawer-divider", "storage", 800),
    ("gap-shelf", "storage", 1100),
    ("closet-organizer", "storage", 1000),
    ("folding-bin", "storage", 1300),
    ("comb", "personal", 500),
    ("hair-clips", "personal", 400),
    ("bath-sponge", "personal", 300),
    ("nail-clipper", "personal", 400),
    ("cotton-pad-box", "personal", 600),
    ("toothbrush-holder", "personal", 700),
    ("pet-lint-roller", "pet", 700),
    ("waste-bag-holder", "pet", 600),
    ("folding-bowl", "pet", 800),
    ("lick-mat", "pet", 700),
    ("toy-ball", "pet", 400),
    ("grooming-glove", "pet", 600),
    ("pen-cup", "office", 800),
    ("binder-clip", "office", 300),
    ("phone-stand", "office", 700),
    ("desk-organizer", "office", 1000),
    ("cable-clip", "office", 500),
    ("note-holder", "office", 400),
]

LANGS = ("en", "es", "de", "fr", "pt", "ja")

PROMOS = {
    "tiers": [[4000, 300], [5000, 500], [10000, 1000], [20000, 2000]],
    "free_shipping_cents": 1900,
    "shipping": {"USCA": 600, "EU": 800, "JP": 700, "MXBR": 900},
    "self_rate": 0.05,
    "direct_rate": 0.10,
}

COUPONS = [
    ("Public", "public", 2000, 300),
    ("First order", "first", 2500, 200),
    ("Share", "share", 2000, 400),
    ("Home screen", "desktop", 1000, 200),
    ("Check-in", "checkin", 1000, 100),
]


def localize_catalog(conn):
    for sku, copy in NAMES.items():
        row = conn.execute("select names, description from products where sku = ?", (sku,)).fetchone()
        if row is None:
            continue
        names = json.loads(row["names"])
        if names.get("en") != copy["en"]:
            continue
        if names.get("ja") not in (None, "", names.get("en"), copy["en"]):
            continue
        description = json.loads(row["description"])
        untouched = all(
            description.get(lang) in (None, "", names.get("en"), copy["en"]) for lang in LANGS
        )
        conn.execute(
            "update products set names = ?, description = ? where sku = ?",
            (
                json.dumps(copy, ensure_ascii=False),
                json.dumps(copy if untouched else description, ensure_ascii=False),
                sku,
            ),
        )


def _write_offer_schedule(conn):
    done = conn.execute("select value from settings where key = 'offer_schedule'").fetchone()
    if done is not None:
        return
    conn.execute(
        "update promos set value = ? where key = 'free_shipping_cents'",
        (json.dumps(PROMOS["free_shipping_cents"]),),
    )
    conn.execute(
        "update promos set value = ? where key = 'tiers'",
        (json.dumps(PROMOS["tiers"]),),
    )
    conn.execute(
        "update coupons set threshold_cents = ?, amount_cents = ? where kind = 'first'",
        (2500, 200),
    )
    conn.execute("insert into settings (key, value) values ('offer_schedule', ?)", (json.dumps("1900"),))


def seed(conn):
    migrate(conn)
    existing = conn.execute("select count(*) as n from products").fetchone()["n"]
    configured = conn.execute("select count(*) as n from promos").fetchone()["n"]
    if not existing and not configured:
        for sku, category, price in PRODUCTS:
            copy = NAMES[sku]
            conn.execute(
                """
                insert into products
                    (sku, category, price_cents, stock, names, bullets, description, specs)
                values (?, ?, ?, 100, ?, ?, ?, ?)
                """,
                (
                    sku,
                    category,
                    price,
                    json.dumps(copy, ensure_ascii=False),
                    json.dumps({lang: [] for lang in LANGS}),
                    json.dumps(copy, ensure_ascii=False),
                    json.dumps({"material": "", "size": "", "weight": ""}),
                ),
            )
        for key, value in PROMOS.items():
            conn.execute(
                "insert into promos (key, value) values (?, ?)",
                (key, json.dumps(value)),
            )
        for name, kind, threshold, amount in COUPONS:
            conn.execute(
                """
                insert into coupons (name, kind, threshold_cents, amount_cents, enabled)
                values (?, ?, ?, ?, 1)
                """,
                (name, kind, threshold, amount),
            )
        conn.execute(
            "insert into settings (key, value) values ('platform_guarantees', ?)",
            (json.dumps({"late_delivery_credit_cents": 500, "return_days": 30, "checkout_min_cents": 0}),),
        )
    localize_catalog(conn)
    _write_offer_schedule(conn)
    ensure_admin(conn)
    ensure_campaigns(conn)
    rehome(conn)
    fill_subs(conn)
    conn.commit()
