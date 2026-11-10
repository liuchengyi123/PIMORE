# Buyer theme contract (v1)

Harbor shopper surfaces share one active theme pack. The shop stores the
active pack id and serves this JSON. harbor-web (H5 and desktop) applies it.
Native iOS (`harbor-ios`) and Android (`harbor-android`) should call the same
endpoint and map these keys. Do not invent a second palette in the client.

Admin and the CS desktop are not buyer surfaces. They do not read this pack.
The dropped uni-app (`harbor-app`) is not a client of this contract.

Raster hero, poster, and product photos keep their baked-in pixels. This
contract is chrome: buttons, bars, cards, type, chips, prices, and badges.

## Request

`GET /api/buyer-theme`

No auth. The shop sends this with the same `Cache-Control: no-store` policy as
its other dynamic responses, so the next fetch sees a newly selected pack.
A missing or unknown stored id falls back to `coral-market`.

```json
{
  "ok": true,
  "version": 1,
  "activeId": "coral-market",
  "pack": {
    "id": "coral-market",
    "name": "Coral Market",
    "tokens": {
      "color.primary": "#FF6A3D",
      "color.primarySoft": "#FFD4C4",
      "color.page": "#FFF4F0",
      "color.ink": "#2C2623",
      "color.muted": "#6E5E58",
      "color.onPrimary": "#FFFFFF",
      "color.surface": "#FFFFFF",
      "color.sale": "#C41E16",
      "color.badge": "#9F1239"
    },
    "derived": {
      "color.primaryHover": "#E05D36",
      "color.primaryPressed": "#C75330",
      "color.primaryDisabled": "#FFB29A"
    }
  },
  "packs": [
    { "id": "coral-market", "name": "Coral Market" }
  ]
}
```

`version` is the contract version. Ignore unknown keys. A `version` greater
than the one a client knows should still paint `pack.tokens` if the keys
above are present.

`packs` lists ids and names only. The colors to paint are always `pack`, the
active one. Adding a pack later does not change these keys.

## Authored tokens

| Key | Coral Market | Apply to |
| --- | --- | --- |
| `color.primary` | `#FF6A3D` | Primary CTAs (add to cart, buy now, checkout, login/register submit). Selected tab icon and label. Switches that are on. Key links. Progress fills. Coupon highlight border. Selected chip/filter/size border. |
| `color.primarySoft` | `#FFD4C4` | Selected chip, filter, and size fills. Coupon and countdown soft wells. Light badges. |
| `color.page` | `#FFF4F0` | Shopper page canvas, including the desktop gutters outside the centered column. |
| `color.ink` | `#2C2623` | Titles and product names. |
| `color.muted` | `#6E5E58` | Secondary text. Compare-at and strikethrough prices. Idle tab labels. |
| `color.onPrimary` | `#FFFFFF` | Text and icons on a `color.primary` fill. |
| `color.surface` | `#FFFFFF` | Product and order cards, search and header bars, sheets (including the add-to-cart sheet), and the tab bar background. |
| `color.sale` | `#C41E16` | Sale price text. Not a button fill. |
| `color.badge` | `#9F1239` | Discount / “% off” badge fill, with `color.onPrimary` as the badge label. Not a button fill. |

Selected chips use a `color.primarySoft` fill, `color.primary` text, and a
`color.primary` border when the control already has a border. That keeps the
chip from looking like a primary button.

`color.sale` and `color.badge` stay distinct from `color.primary` so a
discount never matches Add to cart.

Hairlines are not a token. Clients that need a border may mix 14%
`color.ink` into `color.surface`. Success, error, star ratings, and shipping
status colors are not part of this pack.

## Derived states

`pack.derived` is computed by the server. Clients may use it or recompute.
For version 1 the mix is in sRGB byte space (not linear light), round half up:

- `color.primaryHover` = mix(`color.primary`, `#000000`, 0.12)
- `color.primaryPressed` = mix(`color.primary`, `#000000`, 0.22)
- `color.primaryDisabled` = mix(`color.primary`, `color.surface`, 0.48)

Hover and pressed keep `color.onPrimary` as the label. The disabled fill is
light, so its label is `color.ink`, not `color.onPrimary`.

## harbor-web variables

The web client copies the hex values onto these custom properties. Native
apps do not need the names. They exist so one stylesheet update repaints H5
and the desktop column together.

| Token | CSS variable |
| --- | --- |
| `color.primary` | `--hb-primary` |
| `color.primarySoft` | `--hb-primary-soft` |
| `color.page` | `--hb-page` |
| `color.ink` | `--hb-ink` |
| `color.muted` | `--hb-muted` |
| `color.onPrimary` | `--hb-on-primary` |
| `color.surface` | `--hb-surface` |
| `color.sale` | `--hb-sale` |
| `color.badge` | `--hb-badge` |
| `color.primaryHover` | `--hb-primary-hover` |
| `color.primaryPressed` | `--hb-primary-pressed` |
| `color.primaryDisabled` | `--hb-primary-disabled` |

Older `--hb-coral`, `--hb-paper`, `--fn-*` names in harbor-web point at these
variables. They are aliases, not extra tokens.

## Admin

`/admin/appearance` (administrator role) selects the active pack id and stores
it in the `settings` row `buyer_theme`. Only packs shipped in
`shop/buyer_theme.py` can be selected. Coral Market is the only pack in v1.
A new pack is a new entry there plus a version note if the keys change.
