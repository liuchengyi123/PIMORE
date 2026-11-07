# Harbor 独立站转化改造 · Cursor 执行方案

> 用途：把本文件丢给 Cursor（或分任务粘贴），按编号逐项执行。
> 背景：低价引流品（$1.99 级）+ 满 $25 包邮凑单模型。北极星指标：AOV ≥ $25、凑单率 ≥ 60%。
> 结构：P0 后台手动配置（不需要 Cursor）→ P1 代码补丁（5 个任务）→ P2 系统级（4 个任务，含依赖）。
> 重要约束：购物车 cookie 是 `httponly`，**前端 JS 读不到购物车内容**，一切购物车状态必须由后端注入 `data-*` 属性。

---

## P0 · 后台手动配置（先做，当天上线）

| # | 项目 | 位置 | 改成 |
|---|---|---|---|
| 0.1 | 售价倍率 sale_rate | 后台「定价规则」（admin.html:88） | 1.1 → 1.3 |
| 0.2 | 原价倍率 list_rate | 后台「定价规则」（admin.html:87） | 1.3 → 1.6 |
| 0.3 | 包邮门槛 | 后台促销（admin.html:702） | 3900 → 2500（$25） |
| 0.4 | 不满包邮运费 | 后台促销 | USCA 600→499、EU 800→599、JP 700→599、MXBR 900→699 |
| 0.5 | 满减档 tiers | 后台促销 | [[3000,300],[5000,700]] |
| 0.6 | 引流品 campaign | 后台 campaign | newcomer 放 4 个 $1.99 品（约 5 折），seckill 轮换 |
| 0.7 | 同步默认值 | `shop/seed.py:88-94` PROMOS | 与上面一致，保证新库一致 |

---

## P1 · 代码补丁

### 任务 1：引流品放行（低价品不再被拦截）

**文件**：`shop/alibaba.py`、`shop/package.py`、`shop/db.py`、`shop/app.py`、`shop/templates/card.html`

**1a. `shop/alibaba.py` `sku_price()`（约 481 行）**

现状签名：
```python
def sku_price(source_cents, weight, label, list_rate, sale_rate, grams_per_dollar=30, hold_percent=20):
```
改为增加 `lure=False` 参数，并在 hold 判定后放行：
```python
def sku_price(source_cents, weight, label, list_rate, sale_rate, grams_per_dollar=30, hold_percent=20, lure=False):
    del label
    source = int(source_cents)
    grams = grams_from_weight(weight)
    by_cost = markup_cents(source, sale_rate)
    by_weight = weight_floor_cents(grams, grams_per_dollar)
    sale = max(by_cost, by_weight)
    original = max(markup_cents(source, list_rate), sale)
    gap = Decimal(str(hold_percent))
    hold = by_cost > 0 and Decimal(by_weight) * 100 >= Decimal(by_cost) * (Decimal(100) + gap)
    # 引流品例外：重量价 ≤ $3 且 ≤ 120g 的轻小件放行（保住低价位，又不至于亏运费）
    if lure and by_weight <= 300 and grams <= 120:
        hold = False
    return {
        "grams": int(grams.quantize(Decimal("1"), rounding=ROUND_HALF_UP)),
        "price_cents": sale,
        "original_cents": original,
        "hold": hold,
    }
```

**1b. `shop/package.py` 传参链路**（让导入时知道哪些是引流品）

- `preview_sheets(blobs, list_rate, sale_rate, grams_per_dollar=30, hold_percent=20)` → 加 `lure_skus=None`；
- `read_package(raw, list_rate, sale_rate, grams_per_dollar=30, hold_percent=20, skip_held_images=False)` → 加 `lure_skus=None`；
- `_preview_zip(...)`、`_products(raw, pictures, list_rate, sale_rate, seen, grams_per_dollar=30, hold_percent=20)` → 加 `lure_skus=None`；
- `_products()` 内调用 `sku_price(...)` 处（约 332 行），传入：
```python
code = _text(cell(first, "资料编码"))
lure = bool(lure_skus) and (code in lure_skus or sku in lure_skus)
priced = sku_price(source, _text(cell(row, "重量")), label, list_rate, sale_rate,
                   grams_per_dollar, hold_percent, lure=lure)
```

**1c. `shop/db.py` SCHEMA**：`products` 表（52-69 行）加字段：
```sql
is_lure integer not null default 0
```
已有库补列（SQLite）：`alter table products add column is_lure integer not null default 0;`（用 try/except 包住，已存在则跳过）。

**1d. `shop/app.py` 导入流程**

- 找到 `run_upload` / `run_commit`（约 4277 / 4321 行）里的 `read_package(...)` / `preview_sheets(...)` 调用，新增参数：`lure_skus={...}`，值来自表单字段 `lure_skus`（逗号或换行分隔的 SKU/资料编码列表，set 化）；
- 找到 `insert into products` 语句，插入 `is_lure` 列（1/0）；
- 后台 admin 模板的导入表单加一个文本域："引流品 SKU 列表（逗号分隔）"。

**1e. 前台展示**：`present_card()` / `present()`（app.py 约 960 / 1021 行）输出 `"is_lure": int(row.get("is_lure") or 0)`；`card.html` 商品卡加角标（如 `Lure · 今日特价`）。

**验收**：导入一个供货 ¥1、30g 的品，勾为引流品后能正常上架；非引流品同参数仍被拦截。

---

### 任务 2：人工置顶权重（7000 品不再平铺）

**文件**：`shop/db.py`、`shop/app.py`、`shop/templates/admin.html`

**2a. `shop/db.py` SCHEMA**：`products` 表加：
```sql
priority integer not null default 0
```

**2b. `shop/app.py` 排序三处**（listing 1277 行、home 1373 行、分类 rail 1388/1394 行附近），在 `promoted` 之后插入 priority：

```python
rows.sort(key=lambda row: (
    0 if row["sku"] in promoted else 1,
    -int(row.get("priority") or 0),        # ← 新增：人工置顶 0-100
    rank(row, ctx["country"]),
    -heat(row, ctx["country"]),
))
```
home() 和 rail 的排序同理（无 promoted 时从 priority 开始）。

**2c. 后台编辑**：`admin.html` 商品管理面板加"置顶权重"输入列 + 对应 POST 路由（`update products set priority=? where sku=?`）。

**2d.（可选增强）国家适配批量标记**：`shop/markets.py` 已有 `judge_batch`（AI 判断 10 国适配）+ `push_line`。给 7000 品批量跑一次，`rank()` 会把适配款自动排前。

**验收**：后台设某 SKU priority=100，前台 featured 排到最前（除广告位外）。

---

### 任务 3：组合凑单推荐（2~3 件一键补差）

**文件**：`shop/suggest.py`（新增函数）、`shop/app.py`（购物车页）、`shop/templates/cart.html`、`shop/i18n.py`（文案）

**3a. `shop/suggest.py` 新增**：
```python
def combo_for(items, *, exclude, budget, allow_over=1.10, limit=3):
    """缺口 budget 内找 2-3 件组合，总价最贴近 budget（允许略超 10%）。"""
    pool = [
        item for item in items
        if item["sku"] not in exclude and item["stock"] > 0
        and item["price_cents"] <= budget
    ]
    pool.sort(key=lambda item: item["price_cents"])
    best, best_sum = None, None
    def better(sum_cents, combo):
        nonlocal best, best_sum
        if best_sum is None or abs(sum_cents - budget) < abs(best_sum - budget):
            best, best_sum = combo, sum_cents
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            s = pool[i]["price_cents"] + pool[j]["price_cents"]
            if s <= int(budget * allow_over):
                better(s, (pool[i], pool[j]))
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            for k in range(j + 1, len(pool)):
                s = pool[i]["price_cents"] + pool[j]["price_cents"] + pool[k]["price_cents"]
                if s <= int(budget * allow_over):
                    better(s, (pool[i], pool[j], pool[k]))
    return best
```

**3b. `shop/app.py` 购物车页 `cart()`**（约 1775 行）：`budget = nudge["need"]` 已有，追加：
```python
combo = None
if budget:
    combo = combo_for(
        shelf, exclude={line["sku"] for line in shown},
        budget=budget,
    )
```
`ctx.update(...)` 里加 `"combo": cards_for(ctx, combo) if combo else []`。

**3c. `cart.html`**：在 `picks` 区块上方加"帮你配好了"组合区——两/三张商品卡 + "一键加购全部"按钮。

**3d. 一键加购全部**：新增端点（`app.py`，放在 `/cart/add` 附近）：
```python
@app.post("/cart/add-many")
async def add_many(request: Request):
    form = await request.form()
    country = str(form.get("country") or "US")
    skus = form.getlist("sku")
    lines = load_lines(request.cookies.get("cart"))
    for sku in skus:
        offer = chosen_offer(sku, "")
        if offer is None:
            continue
        code = sell_code(sku, offer)
        if stock_ok(code, 1):
            lines = merge_line(lines, code, 1)
    response = redirect("/cart", country, cart=dump_lines(lines))
    return response
```
表单里放多个 `<input type="hidden" name="sku">`。注意 `chosen_offer` 对多规格 SKU 返回 None（跳去商品页），只有单规格品进组合——符合预期。

**3e. `shop/i18n.py`**：各语言补 `combo_title`（"帮你配好了"）、`combo_add_all`（"一键加购"）等 key。

**验收**：购物车差 $15，页面出现 2-3 件组合，总价 ≤ $16.5，一键加购后缺口清零。

---

### 任务 4：商品页包邮缺口通栏

**文件**：`shop/app.py`（view() 与 product()）、`shop/templates/base.html`、`shop/templates/product.html`、`shop/i18n.py`

**4a. `shop/app.py view()`**（约 849-855 行，已算 merchandise）加：
```python
free_cents = int(promos["free_shipping_cents"])
ctx["cart_gap_cents"] = (free_cents - merchandise) if (merchandise > 0 and merchandise < free_cents) else 0
```

**4b. `base.html` body 标签（35 行）**加属性：
```html
data-cart-gap="{{ cart_gap_cents|default(0) }}"
```

**4c. `product.html`** 在商品信息上方加通栏：
```html
{% if cart_gap_cents and cart_gap_cents > 0 %}
<section class="cart-gap-bar">
  <span>购物车还差 <strong>{{ (cart_gap_cents / 100)|round(2) }} USD</strong> 免运费</span>
  {% if item.price_cents >= cart_gap_cents %}<span class="gap-fit">加购这件正好凑够 →</span>{% endif %}
  <a href="{{ href('/cart', country) }}">去购物车</a>
</section>
{% endif %}
```
（金额展示请用 `money()` 辅助函数换算当地币种，不要硬编码 USD；样式加到 `shop.css`。）

**4d. `shop/i18n.py`**：补 `cart_gap_line`、`cart_gap_fit`、`cart_gap_go` 各语言 key。

**验收**：加购 1 件后访问任意商品页，顶部出现"还差 $X 免运费"。

---

### 任务 5：改造弃购弹窗（现有骨架，不重写）

> 现状：`base.html` 已有完整 exit-intent 机制 —— `mouseout` 触发 `showLeave()`（421 行）、8 秒后 popstate 兜底（426 行）、弹窗 `pop-hold`（空车留客）/ `pop-ship`（有车送 $1 品）/ `pop-desk`（桌面 PWA 引导）。**不要重写这套逻辑**，只加一个"还差 $X 免邮"弹层并排优先级。

**文件**：`shop/templates/base.html`、`shop/app.py`

**5a. `base.html`** 在 `pop-ship` 弹层（161-179 行）后加：
```html
{% if cart_gap_cents and cart_gap_cents > 0 %}
<div class="pop-ship" id="pop-ship-gap" hidden>
  <div class="pop-ship-slip" role="dialog" aria-modal="true" aria-labelledby="gap-title">
    <button class="pop-x" type="button" data-gap-close aria-label="{{ t.pop_close }}">×</button>
    <p class="pop-kicker">Free shipping</p>
    <h2 id="gap-title">还差 <strong data-gap-amount>{{ (cart_gap_cents / 100)|round(2) }} USD</strong> 免运费</h2>
    <p class="pop-note">凑满 $25 全场包邮，去购物车看看推荐吧。</p>
    <a class="btn" href="{{ href('/cart', country) }}">去凑单 →</a>
  </div>
</div>
{% endif %}
```

**5b. `base.html` `showLeave()`（390-403 行）**改为优先弹免邮：
```js
var cart = Number(document.body.getAttribute("data-cart") || "0");
var gap = Number(document.body.getAttribute("data-cart-gap") || "0");
if (cart > 0 && gap > 0) {
  var gapPop = document.getElementById("pop-ship-gap");
  if (gapPop) { gapPop.hidden = false; return; }
}
if (cart > 0) { var ship = document.getElementById("pop-ship"); if (ship) ship.hidden = false; return; }
var hold = document.getElementById("pop-hold");
if (hold) hold.hidden = false; else showDesk(false);
```
`popupOpen()` 数组（371 行）加 `"pop-ship-gap"`，关闭按钮注册在 `shipClose` 附近加 `data-gap-close` 监听。文案走 `i18n.py` 各语言 key，不要硬编码英文（上面代码仅为示意，最终用 `{{ t.xxx }}`）。

**5c.（可选 P2 前置）停留超时弹窗**：`dwell` 已是 8 秒，需要"90 秒无操作弹凑单"时，另加一个 `setTimeout(90_000)` 且购物车 gap>0 时弹 `pop-ship-gap`（注意与 exit-intent 用 sessionStorage 各控一次频，避免连环弹）。

**验收**：加购 1 件后把鼠标移到浏览器顶部再移出，弹"还差 $X 免运费"；凑满 $25 后不再弹。

---

## P2 · 系统级

### 任务 6：购物车落库（邮件挽回的前提，必须先做）

**文件**：`shop/db.py`、`shop/app.py`

**6a. `shop/db.py` SCHEMA 加**：
```sql
create table if not exists cart_items (
    email text not null,
    sku text not null,
    qty integer not null,
    updated_at text not null,
    sent_at text,
    primary key (email, sku)
);
```

**6b. `shop/app.py` `add_cart()`（约 1676 行）**，写库成功、且 `buyer_email(request)` 非空时 upsert：
```python
email = buyer_email(request)
if email:
    conn.execute(
        "insert into cart_items (email, sku, qty, updated_at, sent_at) values (?, ?, ?, ?, NULL) "
        "on conflict (email, sku) do update set qty = excluded.qty, updated_at = excluded.updated_at",
        (email, code, qty, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
```
`update_cart`（1740 行附近）删除行时同步删除 cart_items 对应行；下单成功后（grep `status = 'paid'` 或 orders 插入处）清空该 email 的 cart_items。

> 简化口径：只对"已登录/留过邮箱"的会话落库——邮件挽回本来就需要邮箱，未登录访客先不追。

**验收**：登录状态下加购后，`select * from cart_items` 有记录；下单后清空。

---

### 任务 7：邮件挽回（新文件 ×2 + 调度）

**文件**：`shop/mail.py`（新）、`shop/recover.py`（新）、`shop/db.py`、环境变量

**7a. `shop/mail.py`（新文件）**：
```python
"""SMTP 邮件发送。环境变量：SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS / SMTP_FROM。"""
import os
import smtplib
from email.message import EmailMessage


def send(subject, html, to):
    host = os.environ.get("SMTP_HOST") or ""
    if not host:
        return False
    port = int(os.environ.get("SMTP_PORT") or "587")
    user = os.environ.get("SMTP_USER") or ""
    password = os.environ.get("SMTP_PASS") or ""
    sender = os.environ.get("SMTP_FROM") or user
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = to
    message.set_content("Please view this email in HTML.")
    message.add_alternative(html, subtype="html")
    try:
        with smtplib.SMTP(host, port, timeout=15) as client:
            client.starttls()
            if user:
                client.login(user, password)
            client.send_message(message)
        return True
    except Exception:
        return False
```

**7b. `shop/recover.py`（新文件）**——选"1~24h 前有购物车、未发过挽回、无支付订单"的邮箱发信：
```python
"""弃购挽回：python -m shop.recover"""
from datetime import datetime, timedelta, timezone

from shop.db import connect
from shop.mail import send


def run(db_path="data/shop.db", hours_min=1, hours_max=24):
    conn = connect(db_path)
    since = (datetime.now(timezone.utc) - timedelta(hours=hours_max)).isoformat()
    before = (datetime.now(timezone.utc) - timedelta(hours=hours_min)).isoformat()
    rows = conn.execute(
        """
        select email, sum(price_cents * qty) as total
        from cart_items join products on products.sku = cart_items.sku
        where cart_items.sent_at is null
          and cart_items.updated_at between ? and ?
        group by email
        """,
        (since, before),
    ).fetchall()
    free_cents = 2500  # 与后台包邮门槛一致
    sent = 0
    for row in rows:
        email = row["email"]
        paid = conn.execute(
            "select count(*) as n from orders where email = ? and status != 'cancelled'",
            (email,),
        ).fetchone()["n"]
        if paid:
            conn.execute("update cart_items set sent_at = ? where email = ?", (datetime.now(timezone.utc).isoformat(), email))
            continue
        gap = max(0, free_cents - int(row["total"]))
        html = (
            "<h2>Your cart is still here</h2>"
            f"<p>You are <b>${gap / 100:.2f}</b> away from free shipping.</p>"
            "<p>Complete your order within 24h and get <b>$2 off</b>.</p>"
            "<p><a href='https://your-shop.com/cart'>Back to cart</a></p>"
        )
        if send("Your cart is waiting", html, email):
            conn.execute(
                "update cart_items set sent_at = ? where email = ?",
                (datetime.now(timezone.utc).isoformat(), email),
            )
            conn.commit()
            sent += 1
    return sent


if __name__ == "__main__":
    print("sent:", run())
```
（`orders` 表字段以实际为准，先 `grep "create table orders"` 核对列名。）

**7c. 调度**：Windows 计划任务每天 2~3 次：`cd D:\1010 && .venv\Scripts\python.exe -m shop.recover`；也可挂到 `start.bat` 后台循环。

**验收**：造一条 2 小时前的弃购记录（cart_items 有 email），跑 `python -m shop.recover`，收到挽回邮件；再跑不重发（sent_at 已置）。

---

### 任务 8：转化漏斗统计（迭代包邮门槛/引流品的依据）

**文件**：`shop/db.py`、`shop/app.py`（`_track`）、`admin.html`

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
- 找到 `def _track`（app.py），扩展写库：event 取值 `view / add_cart / checkout_start / pay_ok / pay_fail`，`cart()` 与 `checkout_page()` 分别埋 `add_cart`（已有 `_track(request, "cart", ...)`，可加 `checkout_start`）。
- `admin.html` 加"漏斗"面板：加购率 = add_cart 数 / view 数、结算启动率、支付成功率、**凑单率** = 购物车达 2500¢ 的会话占比（可用 cart_items.total ≥ 2500 计算）。

**验收**：后台能看到最近 7 天漏斗数字。

---

### 任务 9：下单后复购/邀评邮件（摊薄 CAC 的最后一环）

**文件**：`shop/mail.py` 复用、下单完成处、`reviews` 表（已存在）

- 支付成功 24h 后发"发货中"邮件；签收期后发邀评邮件（`reviews` 表 `unique(email, sku)` 防重复，先查再发）；
- 日用百货复购窗口：首单后第 14 天发"上次买的快用完了吧"补货邮件（可用 `remind reorder` 按钮数据）。

---

## 改完自检清单

- [ ] P0 六项后台配置已改，`seed.py` 默认值同步
- [ ] 引流品能上架（任务 1），非引流品拦截逻辑不变
- [ ] 首页/列表按 priority 排序生效（任务 2）
- [ ] 购物车组合凑单出现且一键加购有效（任务 3）
- [ ] 商品页显示缺口通栏，金额按当地币种（任务 4）
- [ ] exit-intent 优先弹"还差 $X 免邮"，凑满后不再弹（任务 5）
- [ ] 登录会话购物车落库、下单清空（任务 6）
- [ ] `python -m shop.recover` 发信且不重发（任务 7）
- [ ] 漏斗面板数字正确（任务 8）
- [ ] 全站回归：`pytest` 跑一遍 `tests/` 不破坏现有用例
