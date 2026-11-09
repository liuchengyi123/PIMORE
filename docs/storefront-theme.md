# Shopper storefront theme

The buyer site can use either the current Harbor pages or the Figma Pimo shopper UI. Shipping stays **$0**. There is no express / standard / economy choice. Minimum order, tier discounts, and coupons stay on their existing admin pages.

## Switch

1. Open **后台 → 增长 → 店铺外观** (`/admin/appearance`).
2. Choose:
   - `legacy` — current Harbor HTML (header, home, footer, tab bar).
   - `pimo` — Figma Pimo home plus shared chrome (header, search, desktop nav, phone tab bar).
3. Save. The next storefront response uses that theme.

The value is the `storefront_theme` row in the `settings` table (`legacy` or `pimo`). HTTP middleware copies it onto `request.state.storefront_theme`. Templates read `storefront_theme`.

Default is `legacy`, including when the row is missing or not one of those two names.

## What `pimo` changes

- **Home** follows Figma file `eptrtDM0XUICi87bqapjQb`:
  - PC Home (`102:2`) at wide widths
  - H5 Home (`169:2`) from 760px to 1099px
  - App Home (`1:5`) under 760px, including the bottom tab bar
- **Header and search** are real controls. Search submits to `/search`. The locale pill opens `/locale`. Cart opens `/cart` and shows the live count.
- **Product cards** use the live catalog (name, price, photo). The coral add button posts to `/cart/add` with `ajax=1` and updates the cart count.
- **Other shopper pages** keep their current body and pick up the Pimo header, search, footer, and phone tab bar.
- Copy on the home hero says free shipping, no speed tiers. Checkout still uses the existing quote, which charges $0 shipping.

`legacy` does not load `pimo.css` and does not change those pages.
