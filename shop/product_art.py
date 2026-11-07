from pathlib import Path

OUT = Path(__file__).resolve().parent / "static" / "products"

PAPER = "#f4f0e8"
SHADOW = "#e4dacb"
INK = "#243044"
STEEL = "#8b97a3"
CREAM = "#f7f4ee"
SAGE = "#2f6f4e"
LEAF = "#3e8f63"
TEAL = "#1d6d74"
CLAY = "#c65a3a"
OAK = "#c4a36a"
NAVY = "#243044"
BRASS = "#c6a15b"
BLUSH = "#e7b7b0"
WHITE = "#fbfaf7"


def wrap(body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="480" height="480" viewBox="0 0 480 480">
  <rect width="480" height="480" fill="{PAPER}"/>
  <ellipse cx="240" cy="404" rx="128" ry="14" fill="{SHADOW}"/>
  {body}
</svg>
"""


ART = {
    "oil-sprayer": f"""
      <rect x="198" y="168" width="84" height="176" rx="30" fill="{SAGE}"/>
      <rect x="212" y="184" width="56" height="128" rx="16" fill="{LEAF}"/>
      <rect x="216" y="132" width="48" height="42" rx="8" fill="{NAVY}"/>
      <rect x="232" y="92" width="16" height="46" fill="{STEEL}"/>
      <circle cx="240" cy="84" r="16" fill="{BRASS}"/>
      <path d="M256 108h78" stroke="{STEEL}" stroke-width="8" stroke-linecap="round"/>
      <circle cx="338" cy="108" r="6" fill="{BRASS}"/>
    """,
    "drain-rack": f"""
      <path d="M118 286h244l-18 28H136z" fill="{STEEL}"/>
      <rect x="132" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="160" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="188" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="216" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="244" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="272" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="300" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <rect x="328" y="168" width="10" height="122" rx="3" fill="#d5dbe1"/>
      <ellipse cx="176" cy="196" rx="34" ry="46" fill="{CREAM}" stroke="#d7d1c6" stroke-width="8"/>
      <ellipse cx="292" cy="188" rx="30" ry="42" fill="#efe7da" stroke="#d3c6b4" stroke-width="8"/>
    """,
    "silicone-spatula": f"""
      <g transform="rotate(-28 240 240)">
        <rect x="214" y="86" width="28" height="168" rx="12" fill="{OAK}"/>
        <path d="M176 250h104l-18 78c-8 28-60 28-68 0z" fill="{CLAY}"/>
        <path d="M196 262h64l-10 40H206z" fill="#e7d3c4"/>
      </g>
    """,
    "seasoning-box": f"""
      <rect x="124" y="168" width="232" height="156" rx="16" fill="{CREAM}" stroke="{NAVY}" stroke-width="8"/>
      <path d="M201 168v156M278 168v156" stroke="{NAVY}" stroke-width="6"/>
      <circle cx="162" cy="230" r="18" fill="{CLAY}"/>
      <circle cx="240" cy="246" r="16" fill="{SAGE}"/>
      <circle cx="318" cy="226" r="18" fill="{BRASS}"/>
      <rect x="150" y="146" width="36" height="16" rx="4" fill="{NAVY}"/>
      <rect x="226" y="146" width="36" height="16" rx="4" fill="{NAVY}"/>
      <rect x="302" y="146" width="36" height="16" rx="4" fill="{NAVY}"/>
    """,
    "measuring-spoons": f"""
      <circle cx="240" cy="168" r="16" fill="{BRASS}"/>
      <path d="M240 184c-70 20-90 70-78 108" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
      <ellipse cx="150" cy="300" rx="42" ry="26" fill="{CREAM}" stroke="{NAVY}" stroke-width="7"/>
      <path d="M240 184c0 70 10 100 46 124" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
      <ellipse cx="300" cy="312" rx="34" ry="22" fill="#efe7da" stroke="{NAVY}" stroke-width="7"/>
      <path d="M240 184c70 8 104 40 112 86" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
      <ellipse cx="360" cy="262" rx="26" ry="18" fill="{CREAM}" stroke="{NAVY}" stroke-width="7"/>
    """,
    "sink-strainer": f"""
      <ellipse cx="240" cy="250" rx="108" ry="36" fill="#d7dee4"/>
      <path d="M132 250c0 70 48 118 108 118s108-48 108-118" fill="{STEEL}"/>
      <ellipse cx="240" cy="250" rx="78" ry="24" fill="#c5ced6"/>
      <circle cx="210" cy="300" r="6" fill="{NAVY}"/>
      <circle cx="240" cy="318" r="6" fill="{NAVY}"/>
      <circle cx="270" cy="300" r="6" fill="{NAVY}"/>
      <circle cx="240" cy="276" r="6" fill="{NAVY}"/>
      <rect x="214" y="118" width="52" height="14" rx="6" fill="{BRASS}"/>
    """,
    "lint-roller": f"""
      <rect x="168" y="168" width="144" height="150" rx="72" fill="#f7f7f5" stroke="{NAVY}" stroke-width="8"/>
      <path d="M188 210h104M188 242h104M188 274h104" stroke="#d5d8dc" stroke-width="6"/>
      <rect x="214" y="308" width="52" height="64" rx="10" fill="{TEAL}"/>
    """,
    "gap-brush": f"""
      <rect x="214" y="96" width="36" height="150" rx="12" fill="{TEAL}"/>
      <rect x="168" y="230" width="144" height="28" rx="8" fill="{NAVY}"/>
      <path d="M184 258v70M208 258v86M232 258v78M256 258v90M280 258v72" stroke="{SAGE}" stroke-width="6" stroke-linecap="round"/>
    """,
    "sponge-refill": f"""
      <rect x="150" y="214" width="180" height="78" rx="14" fill="#f0c24b"/>
      <rect x="162" y="168" width="180" height="70" rx="14" fill="{LEAF}"/>
      <rect x="174" y="128" width="180" height="64" rx="14" fill="#e7d7b1"/>
      <path d="M196 150h130" stroke="#f7f1e4" stroke-width="8" stroke-linecap="round"/>
    """,
    "cleaning-cloth": f"""
      <path d="M132 150h200l28 40-36 150H150z" fill="#d7ebe4"/>
      <path d="M150 190h196" stroke="{TEAL}" stroke-width="10"/>
      <path d="M146 230c40 16 80 16 120 0s80-8 110 8" stroke="{TEAL}" stroke-width="8" fill="none"/>
      <path d="M160 280c50 18 90 8 140-8" stroke="#9fcfc2" stroke-width="8" fill="none"/>
    """,
    "pot-brush": f"""
      <circle cx="240" cy="236" r="78" fill="{SAGE}"/>
      <circle cx="214" cy="214" r="10" fill="#d7ecdf"/>
      <circle cx="246" cy="200" r="10" fill="#d7ecdf"/>
      <circle cx="274" cy="226" r="10" fill="#d7ecdf"/>
      <circle cx="230" cy="256" r="10" fill="#d7ecdf"/>
      <circle cx="266" cy="258" r="10" fill="#d7ecdf"/>
      <rect x="214" y="300" width="52" height="62" rx="12" fill="{OAK}"/>
    """,
    "dustpan-set": f"""
      <path d="M118 250h150l28 78H146z" fill="{TEAL}"/>
      <path d="M128 250h120" stroke="{NAVY}" stroke-width="8"/>
      <rect x="292" y="120" width="16" height="180" rx="6" fill="{OAK}"/>
      <path d="M276 292h48M284 308h36M292 324h24" stroke="{SAGE}" stroke-width="6" stroke-linecap="round"/>
    """,
    "adhesive-hooks": f"""
      <rect x="150" y="150" width="52" height="78" rx="8" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
      <path d="M166 228c0 28 20 36 20 58" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
      <rect x="214" y="168" width="52" height="78" rx="8" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
      <path d="M230 246c0 28 20 36 20 58" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
      <rect x="278" y="150" width="52" height="78" rx="8" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
      <path d="M294 228c0 28 20 36 20 58" stroke="{STEEL}" stroke-width="8" fill="none" stroke-linecap="round"/>
    """,
    "vacuum-bag": f"""
      <path d="M150 140h180l-16 210H166z" fill="#d9e4ea" stroke="{NAVY}" stroke-width="6"/>
      <rect x="196" y="196" width="88" height="28" rx="14" fill="{NAVY}"/>
      <circle cx="240" cy="210" r="6" fill="{BRASS}"/>
      <path d="M190 250h100M186 280h108" stroke="#b7c6cf" stroke-width="6"/>
    """,
    "drawer-divider": f"""
      <rect x="118" y="160" width="244" height="168" rx="14" fill="{OAK}"/>
      <rect x="132" y="174" width="104" height="64" rx="8" fill="{CREAM}"/>
      <rect x="246" y="174" width="100" height="64" rx="8" fill="{CREAM}"/>
      <rect x="132" y="248" width="214" height="62" rx="8" fill="{CREAM}"/>
    """,
    "gap-shelf": f"""
      <rect x="150" y="150" width="28" height="190" rx="6" fill="{NAVY}"/>
      <rect x="302" y="150" width="28" height="190" rx="6" fill="{NAVY}"/>
      <rect x="150" y="168" width="180" height="16" rx="4" fill="{OAK}"/>
      <rect x="150" y="236" width="180" height="16" rx="4" fill="{OAK}"/>
      <rect x="168" y="190" width="46" height="28" rx="4" fill="{CREAM}"/>
      <rect x="176" y="258" width="70" height="22" rx="4" fill="{TEAL}"/>
    """,
    "closet-organizer": f"""
      <rect x="168" y="108" width="144" height="14" rx="6" fill="{NAVY}"/>
      <path d="M176 122h128v150H176z" fill="#e7e1d6"/>
      <path d="M176 200h128" stroke="{OAK}" stroke-width="6"/>
      <rect x="190" y="272" width="40" height="78" rx="8" fill="{TEAL}"/>
      <rect x="250" y="272" width="40" height="78" rx="8" fill="{SAGE}"/>
    """,
    "folding-bin": f"""
      <path d="M132 168h216l-24 168H156z" fill="#dfe7ea" stroke="{NAVY}" stroke-width="8"/>
      <path d="M156 220h168M164 268h152" stroke="#b7c4cb" stroke-width="8"/>
      <rect x="168" y="146" width="144" height="18" rx="8" fill="{OAK}"/>
    """,
    "comb": f"""
      <path d="M150 168h180v36H150z" fill="{BLUSH}"/>
      <path d="M162 204v96M186 204v120M210 204v96M234 204v120M258 204v96M282 204v120M306 204v96" stroke="{NAVY}" stroke-width="8" stroke-linecap="round"/>
    """,
    "hair-clips": f"""
      <g transform="rotate(-18 180 230)">
        <rect x="120" y="210" width="140" height="28" rx="14" fill="{CLAY}"/>
        <rect x="132" y="198" width="116" height="14" rx="7" fill="#e7b2a4"/>
      </g>
      <g transform="rotate(16 300 250)">
        <rect x="230" y="236" width="140" height="28" rx="14" fill="{NAVY}"/>
        <rect x="242" y="224" width="116" height="14" rx="7" fill="{STEEL}"/>
      </g>
    """,
    "bath-sponge": f"""
      <ellipse cx="240" cy="250" rx="110" ry="78" fill="#f2c9b0"/>
      <ellipse cx="210" cy="230" rx="46" ry="28" fill="#f8e1d2"/>
      <circle cx="268" cy="268" r="16" fill="#e7b197"/>
      <circle cx="300" cy="230" r="10" fill="#e7b197"/>
    """,
    "nail-clipper": f"""
      <g transform="rotate(-20 240 240)">
        <rect x="150" y="214" width="180" height="36" rx="16" fill="{STEEL}"/>
        <rect x="168" y="196" width="120" height="18" rx="8" fill="#d5dbe0"/>
        <circle cx="300" cy="232" r="16" fill="{NAVY}"/>
        <path d="M150 214c-20 18-20 36 0 36" fill="{STEEL}"/>
      </g>
    """,
    "cotton-pad-box": f"""
      <rect x="140" y="170" width="200" height="150" rx="16" fill="{CREAM}" stroke="{NAVY}" stroke-width="8"/>
      <ellipse cx="200" cy="230" rx="28" ry="16" fill="{WHITE}" stroke="#e4ddd4" stroke-width="4"/>
      <ellipse cx="248" cy="246" rx="28" ry="16" fill="{WHITE}" stroke="#e4ddd4" stroke-width="4"/>
      <ellipse cx="292" cy="224" rx="28" ry="16" fill="{WHITE}" stroke="#e4ddd4" stroke-width="4"/>
    """,
    "toothbrush-holder": f"""
      <path d="M176 190h128l-14 140H190z" fill="{CREAM}" stroke="{NAVY}" stroke-width="8"/>
      <rect x="198" y="128" width="12" height="78" rx="4" fill="{TEAL}"/>
      <rect x="226" y="116" width="12" height="90" rx="4" fill="{CLAY}"/>
      <rect x="254" y="136" width="12" height="70" rx="4" fill="{SAGE}"/>
      <circle cx="204" cy="124" r="8" fill="#9fd0c8"/>
      <circle cx="232" cy="110" r="8" fill="#f0c2b6"/>
      <circle cx="260" cy="132" r="8" fill="#b7d7c4"/>
    """,
    "pet-lint-roller": f"""
      <rect x="168" y="176" width="144" height="132" rx="66" fill="#f7f7f5" stroke="{CLAY}" stroke-width="10"/>
      <path d="M214 214c8 16 28 16 36 0M230 246c10 8 22 8 32-2" stroke="{CLAY}" stroke-width="6" fill="none" stroke-linecap="round"/>
      <rect x="216" y="300" width="48" height="62" rx="10" fill="{NAVY}"/>
    """,
    "waste-bag-holder": f"""
      <rect x="176" y="128" width="128" height="36" rx="16" fill="{NAVY}"/>
      <path d="M196 164c-8 40 8 150 44 150s52-110 44-150" fill="#d7ebe4" stroke="{TEAL}" stroke-width="6"/>
      <circle cx="240" cy="146" r="8" fill="{BRASS}"/>
    """,
    "folding-bowl": f"""
      <ellipse cx="240" cy="210" rx="110" ry="28" fill="#f2d2c4"/>
      <path d="M130 214c8 86 48 130 110 130s102-44 110-130" fill="{CLAY}"/>
      <ellipse cx="240" cy="214" rx="78" ry="18" fill="#e8b8a6"/>
      <path d="M150 260h180M160 292h160" stroke="#a8442e" stroke-width="6" opacity=".45"/>
    """,
    "lick-mat": f"""
      <rect x="132" y="150" width="216" height="180" rx="28" fill="{SAGE}"/>
      <circle cx="190" cy="210" r="16" fill="#d7ecdf"/>
      <circle cx="240" cy="236" r="16" fill="#d7ecdf"/>
      <circle cx="290" cy="210" r="16" fill="#d7ecdf"/>
      <circle cx="214" cy="278" r="16" fill="#d7ecdf"/>
      <circle cx="270" cy="278" r="16" fill="#d7ecdf"/>
    """,
    "toy-ball": f"""
      <circle cx="240" cy="246" r="92" fill="{CLAY}"/>
      <path d="M168 210c40 16 104 16 144-8" stroke="#e7b2a4" stroke-width="10" fill="none"/>
      <path d="M176 286c48-20 96-16 136 10" stroke="#a8442e" stroke-width="10" fill="none"/>
      <circle cx="206" cy="214" r="10" fill="{CREAM}"/>
    """,
    "grooming-glove": f"""
      <path d="M160 250c0-70 36-110 70-90 10-28 40-36 52-8 22-18 52-4 52 28 20 8 28 40 16 70-20 70-48 92-96 92-62 0-94-36-94-92z" fill="{TEAL}"/>
      <circle cx="196" cy="230" r="7" fill="{NAVY}"/>
      <circle cx="230" cy="214" r="7" fill="{NAVY}"/>
      <circle cx="264" cy="214" r="7" fill="{NAVY}"/>
      <circle cx="292" cy="236" r="7" fill="{NAVY}"/>
    """,
    "pen-cup": f"""
      <path d="M176 196h128l-16 140H192z" fill="{NAVY}"/>
      <rect x="206" y="120" width="10" height="92" fill="{CLAY}"/>
      <rect x="228" y="104" width="10" height="108" fill="{BRASS}"/>
      <rect x="250" y="132" width="10" height="80" fill="{TEAL}"/>
      <rect x="196" y="140" width="8" height="70" transform="rotate(-8 200 170)" fill="{CREAM}"/>
    """,
    "binder-clip": f"""
      <rect x="140" y="210" width="200" height="54" rx="8" fill="{NAVY}"/>
      <path d="M168 210c20-48 40-48 52 0M260 210c12-48 36-48 56 0" stroke="{STEEL}" stroke-width="10" fill="none"/>
      <rect x="168" y="224" width="144" height="12" fill="{BRASS}"/>
    """,
    "phone-stand": f"""
      <path d="M150 300h180l-20 28H176z" fill="{OAK}"/>
      <rect x="196" y="128" width="110" height="176" rx="14" fill="{NAVY}" transform="rotate(-12 250 216)"/>
      <rect x="208" y="146" width="84" height="130" rx="6" fill="#d7ebe8" transform="rotate(-12 250 210)"/>
    """,
    "desk-organizer": f"""
      <rect x="118" y="176" width="244" height="140" rx="12" fill="{NAVY}"/>
      <rect x="132" y="190" width="70" height="110" rx="8" fill="{CREAM}"/>
      <rect x="212" y="190" width="70" height="110" rx="8" fill="#e7e1d6"/>
      <rect x="292" y="190" width="54" height="110" rx="8" fill="{TEAL}"/>
      <rect x="148" y="150" width="8" height="48" fill="{CLAY}"/>
      <rect x="164" y="138" width="8" height="60" fill="{BRASS}"/>
    """,
    "cable-clip": f"""
      <path d="M120 250h240" stroke="{STEEL}" stroke-width="8" stroke-linecap="round"/>
      <rect x="150" y="214" width="46" height="52" rx="16" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
      <rect x="217" y="214" width="46" height="52" rx="16" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
      <rect x="284" y="214" width="46" height="52" rx="16" fill="{CREAM}" stroke="{NAVY}" stroke-width="6"/>
    """,
    "note-holder": f"""
      <path d="M170 300h150l-16 28H186z" fill="{OAK}"/>
      <rect x="176" y="140" width="128" height="160" rx="8" fill="{CREAM}" stroke="{NAVY}" stroke-width="6" transform="rotate(-6 240 220)"/>
      <path d="M198 190h84M198 214h70M198 238h78" stroke="#d9d0c4" stroke-width="6" stroke-linecap="round" transform="rotate(-6 240 220)"/>
    """,
}


def write_all():
    OUT.mkdir(parents=True, exist_ok=True)
    for sku, body in ART.items():
        (OUT / f"{sku}.svg").write_text(wrap(body), encoding="utf-8")


if __name__ == "__main__":
    write_all()
