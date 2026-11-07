# Harbor 独立站 · Cursor 代码需求（拼单转化改造）

> 交付对象：Cursor。本文档是唯一需求来源，按 R1→R9 顺序执行，逐项验收。
> 业务模型：低价引流品（$1.99 级）吸引进店 → 满 $25 包邮凑单 → AOV 拉过 $25，凑单率 ≥60% 为盈利生死线。
> 明确范围外（**不要动**）：定价倍率计算、商品重量价 hold 拦截逻辑、现有 exit-intent 弹窗骨架（pop-hold/pop-ship/pop-desk 与 showLeave 机制）、支付/结算主流程。

---

## 全局约束（每条都违反不得交付）

1. **购物车 cookie 是 `httponly`，前端 JS 读不到**。所有购物车状态（件数、缺口金额）必须由后端在 Jinja 渲染时注入 `data-*` 属性，JS 只读属性，不得尝试读 cookie。
2. **现有 exit-intent 机制禁止重写**：`base.html` 的 `mouseout` 触发 `showLeave()`、`popupOpen()` 弹层数组、8 秒 popstate 兜底已存在且工作正常。只允许**新增弹层 + 调整优先级**。
3. **不动定价与拦截逻辑**：`shop/alibaba.py` 的 `sku_price()` hold 判定、`grams_per_dollar`、倍率计算一律不改。
4. **多语言**：所有新增文案进 `shop/i18n.py` 各语言 key，模板里用 `{{ t.xxx }}`，禁止硬编码英文。
5. **兼容现有数据**：新增数据库字段必须 `try/except` 包裹 `alter table`，已存在的库不重建。
6. 改完全量回归：`pytest tests/` 通过，现有用例不得破坏。

---

## R1 · 人工置顶权重（priority）

**目标**：7000 个品不再按上传顺序平铺，运营可把主推品手动置顶。

**文件**：`shop/db.py`、`shop/app.py`、`shop/templates/admin.html`

**改动**：
- `db.py` SCHEMA（products 表，约 52-69 行）加：`priority integer not null default 0`，并补 `alter table`。
- `app.py` 排序三处（listing 约 1277、home 约 1373、分类 rail 约 1388/1394 附近），在 `promoted` 判断之后插入 priority：
  ```python
  rows.sort(key=lambda row: (
      0 if row["sku"] in promoted else 1,
      -int(row.get("priority") or 0),
      rank(row, ctx["country"]),
      -heat(row, ctx["country"]),
  ))
  ```
  （home 与 rail 无 promoted 时从 priority 起排。）
- `admin.html` 商品管理面板加"置顶权重 0-100"输入列 + 对应 POST 路由：`update products set priority=? where sku=?`。

**验收**：后台给某 SKU 设 100，前台首页/列表/分类该品排在最前（广告位除外）；改回 0 恢复原序。

---

## R2 · 组合凑单推荐 + 一键加购 + 组合价锚定

**目标**：差 $23 到包邮时，系统给出 2-3 件组合并一键加购，且展示"组合价 vs 单买价省 $X"锚定。

**文件**：`shop/suggest.py`（新增函数）、`shop/app.py`（cart 视图 + 新端点）、`shop/templates/cart.html`、`shop/i18n.py`

**改动**：
- `suggest.py` 新增 `combo_for(items, *, exclude, budget, allow_over=1.10, limit=3)`：在预算（缺口）内枚举 2-3 件组合，总价最贴近 budget 且不超 budget×1.10；每件要求单件价 ≤ budget、有库存、不在 exclude 中；排除多规格品（`chosen_offer` 返回 None 的 SKU 不进组合）。
- `app.py` 的 `cart()`（约 1775 行）：`budget = nudge["need"]` 后追加 `combo = combo_for(...)`，结果经 `cards_for(ctx, ...)` 转卡片，`ctx` 增加 `combo` 与 **组合省多少** `combo_save_cents`（组合总价 vs 各单买价之和）。
- 新端点 `POST /cart/add-many`：表单 `sku` 多值，逐 SKU 走与 `/cart/add` 相同的 `chosen_offer → sell_code → stock_ok → merge_line` 逻辑，一次性写回购物车 cookie 并 302 到 `/cart`。
- `cart.html`：`picks` 区块上方新增"帮你配好了"组合区——2-3 张商品卡 + 组合价标注"3 件 $12.99（单买 $15.50，省 $2.50）" + "一键加购全部"按钮（form 提交到 `/cart/add-many`）。
- `i18n.py` 补：`combo_title` / `combo_add_all` / `combo_save`（含金额占位）。

**验收**：购物车差 $15 时页面出现 2-3 件组合，标注省 $X；点一键加购后购物车新增全部组合件且缺口归零；多规格品不出现在组合里。

---

## R3 · 跳档推荐（缺口目标升级）

**目标**：现在 `gap()` 只取"最近目标"，客户永远卡在 $25 线。改为当商品能一步跳档时，组合推荐直接奔满减档（$30/$50）。

**文件**：`shop/suggest.py`（`gap()` 或新 `jump_gap()`）、`shop/app.py`（cart 视图）

**改动**：
- 在现有 `gap()` 逻辑（满减档 / 包邮线 / 下一张优惠券取最近）之外，新增跳档目标：当 `merchandise` 距下一个满减档 ≤ $10 时，组合预算取该满减档 - merchandise（而不是包邮线 - merchandise），并标注"再买 $X 可减 $Y"。
- 展示优先级：能跳档时组合推荐展示"跳档版"（凑 $30 减 $3），同时保留"补差版"（凑 $25 免邮）；两条都显示，各自带金额锚定。
- 优惠券目标保持现有逻辑不动。

**验收**：购物车 $22（距 $25 差 $3、距 $30 差 $8）时，页面出现"再买 $8 满 $30 减 $3"的跳档组合，且仍显示"再买 $3 免邮"补差项；两项分别可一键加购。

---

## R4 · 免邮缺口全局化（全站进度条）

**目标**：免邮钩子从购物车页扩展到全站——任何页面都让客户知道"还差 $X 免邮"。

**文件**：`shop/app.py`（`view()` 注入）、`shop/templates/base.html`、`shop/templates/product.html`、`shop/i18n.py`、CSS

**改动**：
- `view()`（约 849-855 行，已算 `merchandise`）追加：
  ```python
  free_cents = int(promos["free_shipping_cents"])
  ctx["cart_gap_cents"] = (free_cents - merchandise) if (merchandise > 0 and merchandise < free_cents) else 0
  ```
- `base.html` body 标签（35 行）加 `data-cart-gap="{{ cart_gap_cents|default(0) }}"`。
- `base.html` 顶部（header 下方）加**全局免邮进度条**（`{% if cart_gap_cents and cart_gap_cents > 0 %}` 才渲染）：文字"还差 $X 免运费" + 横向进度条（已完成部分占 merchandise/free_cents 百分比），点击跳 `/cart`。
- `product.html` 商品信息上方加通栏：购物车有缺口时显示"还差 $X 免运费"，本商品价格 ≥ 缺口时加注"加购这件正好凑够"。
- 金额一律经现有 `money()` 辅助换算当地币种显示；样式进 `shop.css`；`i18n.py` 补 `ship_gap_line` / `ship_gap_fit` / `ship_gap_go`。

**验收**：加购 1 件后访问首页/商品页/购物车，顶部进度条与商品页通栏均显示正确缺口；凑满 $25 后全站不再显示。

---

## R5 · 弃购弹窗改造：免邮差 + 限时券

**目标**：现有弹窗送 $1 品刺激弱，改为"差 $X 免邮 + 限时券"驱动凑单。

**文件**：`shop/templates/base.html`、`shop/app.py`（view 注入）、`shop/campaigns.py`（发券）、`shop/i18n.py`

**改动**：
- `base.html` 在 `pop-ship` 弹层（约 161 行）后新增 `pop-ship-gap` 弹层：标题"还差 **$X** 免运费"、副文案"现在下单立减 $2（24 小时有效）"、按钮"去凑单 →"。仅当 `cart_gap_cents > 0` 时渲染。
- `showLeave()`（约 390-403 行）优先级调整：`cart > 0 且 gap > 0` → 优先弹 `pop-ship-gap`；`cart > 0 且 gap == 0` → 维持现有 `pop-ship`；空车 → 维持 `pop-hold`。`popupOpen()` 数组（约 371 行）加入新弹层 id，关闭按钮注册与现有 `shipClose` 同模式。
- **限时券（复用现有券机制，禁止新建表）**：在后台 `/admin/coupons` 建一张弃购券（kind 取 `abandon`，threshold=2500，amount=200）；弹窗/邮件发券统一调用 `campaigns.py` 现有 grant 逻辑（参照 `grant_templates` / `coupon_grants` 写入方式，先 `grep "create table coupons"` 核对字段：有无 expiry、code 等列再按列填）。
- 弹窗显示券时需判断"该邮箱已领过"（`coupon_grants` 查重），领过则只显示免邮缺口不重复给券。

**验收**：加购 1 件后鼠标移出浏览器顶部，弹"还差 $X 免运费 + 立减 $2（24h）"；凑满 $25 不再弹；同一邮箱不重复发券；未登录访客弹窗不含券只含缺口。

---

## R6 · 购物车落库（邮件挽回前提）

**目标**：购物车目前只存在 httponly cookie 里，服务器不知道谁弃购了。落库后才能做挽回。

**文件**：`shop/db.py`、`shop/app.py`

**改动**：
- `db.py` 加：
  ```sql
  create table if not exists cart_items (
      email text not null,
      sku text not null,
      qty integer not null,
      updated_at text not null,
      sent_step integer not null default 0,
      primary key (email, sku)
  );
  ```
- `add_cart()`（约 1676 行）：`buyer_email(request)` 非空时 upsert 该 email 的购物车行（on conflict 更新 qty/updated_at）。
- `update_cart()`（约 1734 行附近）：删行时同步删 `cart_items`。
- 下单成功处（找到订单落库/状态变 paid 的视图，grep `status.*paid` 附近）：删除该 email 的 `cart_items`。

**验收**：登录/留过邮箱的会话加购后 `select * from cart_items` 有记录；删减同步；下单成功后清空。

---

## R7 · 弃购邮件挽回三连（1h / 24h / 72h）

**目标**：弃购邮件是独立站回收率最高的渠道，三封递进、终封带券。

**文件**：`shop/mail.py`（新）、`shop/recover.py`（新）、`shop/campaigns.py`（发券复用）、环境变量

**改动**：
- `shop/mail.py`（新文件）：SMTP 发送封装。环境变量 `SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM`，`starttls` + 登录 + `send_message`，失败返回 False 不抛异常。支持 HTML 正文。
- `shop/recover.py`（新文件，`python -m shop.recover` 运行）：
  - 按 `cart_items.updated_at` 分桶 + `sent_step` 防重：
    - `sent_step=0` 且 1~24h 前弃购 → 首封"购物车还在"（提示还差 $X 免邮），置 `sent_step=1`；
    - `sent_step=1` 且 24~72h → 二封"免邮优惠快到期"，置 `sent_step=2`；
    - `sent_step=2` 且 >72h → 终封"为你保留 $3 券"（调用现有 grant 机制给券，threshold=2500，amount=300），置 `sent_step=3`；
  - 每封发前先查 `orders`（grep "create table orders" 核对 email/status 列名）该 email 有无非 cancelled 订单，有则清空 `cart_items` 停止；
  - 邮箱为空或已发完（sent_step≥3）跳过；邮件链接域名用环境变量 `SHOP_DOMAIN`（默认 your-shop.com，上线前必须替换真实域名）。
- 调度：Windows 计划任务每天 2-3 次运行 `python -m shop.recover`；说明写入文档注释。

**验收**：造一条 2 小时前弃购记录，跑 recover 收到首封；再跑不重发；24h 后跑收到二封；72h 后终封带券；有 paid 订单的邮箱被清空不再发。

---

## R8 · 支付后换购（Post-purchase Upsell）

**目标**：支付成功页是全场转化率最高的位置——"再加 $2 拿 XX"无需重填信息，直接拉客单。

**文件**：`shop/app.py`（支付成功/订单确认视图）、对应模板（先 grep "thank" / "bought" / 订单完成页模板定位）、`shop/i18n.py`

**改动**：
- 找到支付成功/订单确认视图（订单状态置 paid 后的展示页），在其模板顶部加"你的订单已完成，再加一件？"换购区。
- 换购品选择：2 个与该订单同品类/价格 $2-8 的轻小件（库存充足、单规格优先），价格标注"加购价 $X"（可用订单后 15 分钟限时价）。
- 交互：点换购 → 复用 `/cart/add-many`（或对换购 SKU 单独调 `add_cart` 逻辑）加入购物车，不打断订单完成流程；按钮变"已加入"。
- 展示文案走 i18n。

**验收**：支付完成后页面出现 2 个换购品；点击后购物车新增对应件且页面即时反馈"已加入"；不影响订单本身状态。

---

## R9 · 转化漏斗统计（数据决策前提）

**目标**：没有漏斗数据前，包邮门槛/满减档/引流品全靠拍脑袋。埋点后每两周按数据调一次。

**文件**：`shop/db.py`、`shop/app.py`（`_track`）、`shop/templates/admin.html`

**改动**：
- `db.py` 加：
  ```sql
  create table if not exists events (
      id integer primary key,
      event text not null,
      sku text,
      qty integer,
      country text,
      created_at text not null
  );
  ```
- 扩展现有 `_track`（grep `def _track` 定位）：event 取值 `view / add_cart / checkout_start / pay_ok`，分别埋点在商品页浏览、`/cart/add`、结算页、支付成功处；`country` 取自请求。
- `admin.html` 新增"漏斗"面板：最近 7 天加购率（add_cart/view）、结算启动率、支付成功率、**凑单率**（购物车缺口归零后成交的会话占比，可用 cart_items 总额 ≥2500¢ 的会话/总成交估算，口径在面板注明）。

**验收**：后台能看到最近 7 天四个环节数字与转化率；埋点不改变任何页面行为。

---

## 自检清单

- [ ] R1 置顶生效且可回退
- [ ] R2 组合出现、锚定金额正确、一键加购成功
- [ ] R3 跳档组合与补差项并存、各自可加购
- [ ] R4 全站进度条 + 商品页通栏，金额按当地币种，凑满消失
- [ ] R5 弹窗优先级正确、券不重复发放、未登录无券
- [ ] R6 落库/同步/清空三条路径都对
- [ ] R7 三封邮件按时序发送且防重、有单即停、域名已换真实值
- [ ] R8 换购可加购且不干扰订单
- [ ] R9 漏斗数字可读、口径注明
- [ ] `pytest tests/` 全量通过
