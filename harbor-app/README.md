# Harbor App（uni-app）

跨境日用电商 Harbor（[linkiip.com](https://linkiip.com)）的移动端脚手架。  
技术栈：**uni-app · Vue3 · Vite · TypeScript**。视觉令牌对齐设计稿「Harbor App UI · 2026」。

## 本地运行（H5）

```bash
cd D:\1010\harbor-app
npm install
npm run dev:h5
```

生产构建：

```bash
npm run build:h5
```

## API_BASE / 代理

| 环境 | `apiRoot()` | 说明 |
|------|-------------|------|
| H5 `localhost` | `/harbor-api` | Vite 代理 → `https://linkiip.com`，并 `cookieDomainRewrite: ""` 让 `Set-Cookie` 落在本机 |
| App / 非本机 H5 | `https://linkiip.com` | 直连；`http.ts` 用本地 jar 镜像 `Set-Cookie` 再带回 `Cookie` 头 |

`VITE_HARBOR_ORIGIN`（默认 `https://linkiip.com`）写入 `.env`；**无密钥**。

本地 H5 的 **登录 / 账户** 也优先走 `/harbor-api`，这样 `buyer_session` 能落在 localhost，Me 页才能解析 `/account`。

## 现网端点（只读公开面）

| 能力 | Method | Path | 备注 |
|------|--------|------|------|
| 首页/分类 | GET | `/home/feed?partial=1&tab=&page=` | HTML cards |
| 商详 | GET | `/p/{sku}` | JSON-LD Product |
| 规格 | GET | `/p/{sku}/peek` | offer id + label |
| **加购** | POST | `/cart/add` | `Accept: application/json` 或 `ajax=1` → JSON rail + `Set-Cookie: cart=` |
| 改数量 | POST | `/cart/update` | form `sku`（可为 `sku~offer`）+ `qty` → 303 + cookie |
| 购物车页 | GET | `/cart` | HTML `cart-line`（刷新解析） |
| 结算 | GET | `/checkout` | App 内 webview / 系统浏览器交接 |
| 登录 | GET/POST | `/login` | `buyer_session` HttpOnly |
| 账户首页 | GET | `/account` | 订单计数 / 券 / 余额摘要 HTML |
| 订单列表 | GET | `/account/orders` | |
| 优惠券 | GET | `/account/coupons` | |
| 余额 | GET | `/account/balance` | |
| 签到 | GET/POST | `/check-in` | |
| 邀请 | GET | `/share` · `/r/{code}` | |
| 安装券 | GET | `/install` | PWA |
| 订单结果 | GET | `/orders/{id}` | 支付回跳落点 |
| PayPal 回跳 | GET | `/orders/{id}/paypal` | → `/orders/{id}` |
| 连连回跳 | GET/POST | `/orders/{id}/lianlian` | → `/orders/{id}` |
| 支付页 | GET | `/payment` | awaiting |

## Live vs mock / webview

| 屏幕 | 状态 |
|------|------|
| Home / Browse / PDP | **Live** catalog |
| PDP Add to cart | **Live** `/cart/add`；失败本地兜底 |
| Cart 行/数量/包邮条 | **Live**；失败 Local |
| Checkout | **Handoff** → linkiip.com（H5 form-POST 同步 cart cookie） |
| Me 摘要 | **Live parse** `/account`（需 `buyer_session`；否则 Guest + webview） |
| Me 四宫格 / 签到 / 邀请 / 安装 | **Deep-link webview** 到现网路径 |
| 支付成功 | 识别 `/orders/{id}/paypal|lianlian` 或 `?session_id=` → `pages/order-success`；H5 跨域 iframe 读不到 URL 时用顶栏 **Payment done** |
| 支付取消 | 顶栏 **Cancel → Cart**；落到 `/cart` 时自动回 Cart |

## Cookie / CORS

- 站上 **无** `Access-Control-Allow-Origin` → H5 必须走同域代理。
- `cart` cookie：`SameSite=lax`；加购响应非 HttpOnly，update 后可能变 HttpOnly。
- `buyer_session`：**HttpOnly**；本地 Me 解析依赖经 `/harbor-api/login` 登录，让 Set-Cookie 落在 localhost。
- **H5 checkout**：打开真实域前 form-POST `/cart/add` 同步行项目；支付完成后外跳回 `linkiip.com/orders/*`（跨域，iframe 不可读）→ 用 Done 按钮或日后 Universal Link。
- **Native**：`uni.request` + cookie jar；`web-view` URL 轮询分类回跳；必要时系统浏览器。

## 支付回跳 / Universal Link（Native 后续）

H5 现在靠 webview 顶栏 +（同域时）iframe `load` 读 location。Native App 上建议配置：

| 链接 | App 路由 |
|------|----------|
| `https://linkiip.com/orders/*` | `pages/order-success?id=` |
| `https://linkiip.com/account/*` | `pages/me` 或 webview |
| `https://linkiip.com/cart` | `pages/cart` |
| `https://linkiip.com/login` | webview login |

Associated Domains / App Links 未在本仓库配置（需证书与各商店后台）。

## 目录要点

```
src/api/http.ts          # cookie jar + harborRequest
src/api/cartApi.ts       # add / update / fetchCart
src/api/products.ts      # feed + PDP + offers
src/api/accountApi.ts    # /account HTML parse + deep-links
src/api/urls.ts          # classifyHarborUrl + handoff helpers
src/composables/cart.ts
src/pages/webview/       # checkout/login handoff + return detect
src/pages/order-success/ # in-app post-payment screen
src/pages/me/            # retention tiles → live / webview
```

未改 `D:\1010\shop`；不读 `shop/.env`。
