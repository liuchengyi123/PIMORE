# Harbor iOS

Native SwiftUI storefront for Harbor. It follows Figma **Function · App** (page 24, frames A01–A30): sand canvas, navy / teal / amber, a floating Home · Browse · Cart · Me tab bar, and square product photos.

这是 Harbor 的原生 SwiftUI 店面，对齐 Figma「Function · App」第 24 页 A01–A30：沙色底、海军蓝 / 青绿 / 琥珀、悬浮标签栏（首页 / 分类 / 购物车 / 我的），商品图为 1:1 方图。我的页仍是原生界面。帮助中心是原生列表；条款、隐私、配送、联系、注销账号，以及支付方式和地址里的「管理」，在应用内 WKWebView 打开，带原生返回栏。不提交 App Store。

## Open in Xcode

Requirements: Xcode 16 or newer, iOS 16+.

```bash
open Harbor.xcodeproj
```

Pick an iPhone simulator and run the **Harbor** scheme. For a physical device, set your Team under Signing & Capabilities.

用 Xcode 16+ 打开 `Harbor.xcodeproj`，选一台 iPhone 模拟器，运行 Harbor。真机需要在 Signing 里选择开发团队。

This environment has no Xcode or iOS Simulator, so the project was not compiled here. It is a complete app target (`PBXFileSystemSynchronizedRootGroup`) and is meant to build on a Mac.

当前环境没有 Xcode / 模拟器，因此没有在这里编译。工程是完整的 App target，应在 Mac 上构建。

## Screens

| Frame | Screen |
| --- | --- |
| A01 | Home, 10 items at a time, pull / tap to load 10 more |
| A02 | Browse, sand square category tiles |
| A03 | Search results, Best / Price ↑ / Newest |
| A04 | Category, sub-filters, Filter |
| A05 | Product, tab bar hidden, CS / Add / Buy |
| A06 / A21 | Cart with back, or empty cart |
| A07 / A18 | Checkout preview and payment success. Place order does not charge anyone |
| A08 / A17 | Orders tabs and order detail |
| A09 / A10 | Me, signed in or guest |
| A11 / A12 | Sign in / register dialog on Me |
| A13 | Country and currency (CNY / JPY are display rates on USD prices) |
| A14 | Wishlist |
| A15 / A16 / A24 | Coupons, balance + check-in, invite. Back returns Home |
| A19 | Sale, New, Flash |
| A20 | Customer-service chat stub. No AI badge |
| A22–A26, A29–A30 | Addresses and payment methods (native screens; manage on the shop), history, compare, help, return request |
| A27 | Offline |
| A28 | Sold out + Notify me, when a product is out of stock |

Add to cart opens a half-sheet with the SKU image, pack choices, and quantity. Buy now uses the same sheet, then checkout.

加入购物车会弹出半屏：SKU 图片、规格、数量。立即购买走同一张半屏，然后进入结算。优惠券、签到、余额、邀请的返回键回到首页。结算是本地预览，不会发起真实支付。

Sign in with any email and a password of at least 4 characters. `alex@example.com` shows Alex Miller, matching the Me frame. Me and the sign-in dialog offer Apple, Facebook, and X. There is no Google button and no separate Instagram button. Continuing shows Terms and Privacy, which open inside the app on a native back bar.

任意邮箱 + 至少 4 位密码即可登录。`alex@example.com` 会显示为 Alex Miller。登录框和「我的」页提供 Apple、Facebook、X，没有 Google，也没有单独的 Instagram 按钮。继续前会看到条款和隐私链接，在应用内打开 Pimo 的线上页面，并用原生返回栏回到登录。

## Language and currency

The language picker lists the same eight shop languages: English, 简体中文, 繁體中文, 日本語, Deutsch, Français, Español, Português. Changing language changes labels only. Currency is read from the shop’s geo country on linkiip.com (IP), then kept separate from language.

语言列表与店铺一致，共 8 种。改语言只改界面文案。货币按 IP/地理位置决定，不随语言改变。

## Customer service chat

The chat matches the Function · Chat suite: emoji, My orders, and Visited above the composer; order and visited half-sheets send cards; a product card opens Add to cart / Buy now; an order card opens the order popup. Opened from a product, a sendable offer bar sits above the input.

客服聊天对齐 Figma 聊天套件：输入框上方有表情、我的订单、浏览记录；半屏可把订单或商品发进对话；点商品卡弹出加购/立即购买，点订单卡弹出订单。从商品页进入时，输入框上方有可发送的商品条。

## Social sign-in and share

Placeholders live in `Config/Debug.xcconfig` (Release includes that file). Empty or `YOUR_*` values still compile. The buttons explain which key is missing instead of crashing.

| Key | Used for |
| --- | --- |
| `DEVELOPMENT_TEAM` | Apple Team ID. Required for Sign in with Apple on a device. |
| `FACEBOOK_APP_ID` | Meta app ID. Also the `fb{APP_ID}` URL scheme. |
| `FACEBOOK_CLIENT_TOKEN` | Meta client token. |
| `TWITTER_CLIENT_ID` | X OAuth 2.0 public client (PKCE, no client secret in the app). |
| `TWITTER_REDIRECT_URI` | Defaults to `harbor://oauth/x`. Register that URI on the X app. |
| `INSTAGRAM_APP_ID` | Unused by the sign-in buttons. Meta sign-in is the Facebook button. |
| `INSTAGRAM_REDIRECT_URI` | Unused. Defaults to `harbor://oauth/instagram`. |

How to fill them:

1. Apple: set `DEVELOPMENT_TEAM` to the 10-character Team ID. In the Apple Developer portal, enable Sign in with Apple for `com.harbor.app`. Xcode picks up `Harbor/Harbor.entitlements`.
2. Facebook: create a Meta app, add Facebook Login for iOS, bundle ID `com.harbor.app`, and paste the app ID and client token. This is the only Meta button.
3. X: create an OAuth 2.0 app with a public client, callback `harbor://oauth/x`, scopes `tweet.read` and `users.read`. Paste the client ID. Do not put a client secret in the app.
4. Do not add a Google or Instagram button. The visible providers are Apple, Facebook, and X.

On success the app `POST`s `/api/auth/social` with `provider`, `token`, `name`, `email`, and `userID` (`apple`, `facebook`, or `x`). The same base URL rules apply (release `https://linkiip.com`, simulator debug `http://127.0.0.1:8787`). If that route is missing or not JSON, the app still stores a local session.

Share uses `UIActivityViewController`. A product shares `https://linkiip.com/p/{id}?country=US`. Invite shares `https://linkiip.com/?invite=HARBOR-AM7`. Opening `harbor://p/{id}` or `https://linkiip.com/p/{id}` routes to that product.

密钥写在 `Config/Debug.xcconfig`。保持 `YOUR_*` 也能编译运行；未配置时按钮会提示缺哪一项，不会崩溃。Apple 需要填写 Team ID 并打开 Sign in with Apple。Facebook 用 Meta 的 Facebook Login SDK。没有单独的 Instagram 或 Google 按钮。X 用 PKCE + `ASWebAuthenticationSession`，回调 `harbor://oauth/x`。登录成功会请求 `POST /api/auth/social`，接口不存在时仍在本机记下登录态。商品和邀请页通过系统分享面板发出 `https://linkiip.com/...` 链接。

## API

`URLSession` client:

- `GET /api/home`
- `GET /api/products`
- `GET /api/products/{id}`
- `POST /api/auth/social`
- `GET https://linkiip.com/api/legal` for Help, Privacy, Terms, Shipping, Contact, and account deletion. This call always uses the live host. If it fails, the app opens the canonical paths (`/help`, `/policies/privacy`, `/policies/terms`, `/policies/shipping`, `/contact`, `/help#account-deletion`).
- Those pages open in `InAppWebScreen`, a `WKWebView` under the native `HarborTitleBar` back button. Help itself stays a native hub (Shipping, Returns, Privacy, Terms, Contact / Chat, Delete account, then history, addresses, payments, and compare). The Me tab stays SwiftUI. The app does not use `SFSafariViewController` or hand these URLs to Safari. X sign-in still uses `ASWebAuthenticationSession`.
- Payment methods and addresses stay native screens on the Me path. Each shows an empty state, a short note, and a Privacy link from `LegalUrls`. **Manage payment methods** opens `https://linkiip.com/account/payments` and **Manage addresses** opens `https://linkiip.com/account/addresses`, both in that same in-app web screen. Only Manage and Privacy leave the empty state, and they stay inside the app. The app never collects a full card number. The shop stores only the card brand and the last 4 digits.

Release base URL: `https://linkiip.com`. The home screen name is Pimo. The bundle id stays `com.harbor.app`.

Debug builds on the **simulator** use `http://127.0.0.1:8787` instead. `NSAllowsLocalNetworking` is set so that loopback HTTP is allowed.

正式版请求 `https://linkiip.com`。模拟器的 Debug 包改为 `http://127.0.0.1:8787`。

支付方式和地址仍是原生页面（我的页可进入，不是整页 WebView）。空状态和说明在 App 里。隐私链接和管理按钮在应用内 WKWebView 打开 `https://linkiip.com/policies/privacy`、`https://linkiip.com/account/payments` 和 `https://linkiip.com/account/addresses`，顶栏是原生返回。App 不收集完整卡号，店铺只保存卡组织和末 4 位。帮助中心的配送、退货、隐私、条款、联系和注销账号同样留在这个 WebView 里。

The catalog routes are not on the public site today (they return HTML 404). The client treats a non-JSON or failed response as a miss and decodes `Harbor/Resources/MockCatalog.json`. That file is the live Harbor catalog scraped from linkiip.com: card titles, prices, and image URLs such as `https://linkiip.com/static/catalog/...`. Photos load with `AsyncImage` into square frames. When the JSON API is up, the same decoder accepts `id` / `title` (or `name`) / `price` / `image` plus optional SKUs.

公开站目前没有这几个 JSON 接口。请求失败时会退回内置目录，目录里的标题、价格和图片都来自 linkiip.com 的真实商品卡。接口恢复后，同一套解码器会直接吃线上数据。

## Design tokens

| Token | Hex |
| --- | --- |
| Navy | `#0F2744` |
| Teal | `#0E7490` |
| Amber | `#B45309` |
| Sand | `#F7F4EF` |

Icons are light-weight SF Symbols (stroke-like). The system font stands in for Inter.

图标使用细线 SF Symbols。字体用系统字体对应设计里的 Inter。

## Android parity

Behavior lines up with the Harbor Android storefront: tabbed `NavigationStack`, the same shop loop, SKU sheet, mock checkout, Me account tools, and the three catalog endpoints with a mock fallback. Legal and account pages match Android PR #2 (`9ffd5a2`): the help hub stays native, and Help, Privacy, Terms, Shipping, Contact, account deletion, and Manage on payments and addresses stay inside the app with a native back bar. This repo does not contain Android code.

交互与 Harbor Android 店面对齐：标签页、商品回路、SKU 半屏、模拟下单、我的页工具，以及三个目录接口和失败回退。条款和账户页对齐 Android PR #2（`9ffd5a2`）：帮助中心仍是原生列表，帮助、隐私、条款、配送、联系、注销账号，以及支付方式和地址的管理，都在应用内打开并带原生返回。本仓库不含 Android 代码。
