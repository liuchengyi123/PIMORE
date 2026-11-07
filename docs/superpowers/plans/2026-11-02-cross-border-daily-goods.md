# 跨境日用百货买家前台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按 `docs/superpowers/specs/2026-11-02-cross-border-daily-goods-design.md` 做出一个能浏览、按当地货币结算、收款、发货并承受投放读流量的独立网站。

**Architecture:** 新目录 `shop/`，不改 `liveroom/`。纯函数负责语言、货币、运费档、结算和返利。FastAPI 渲染页面并写 PostgreSQL。Redis 只放商品列表缓存、当小时汇率和结算提交号。价格页不进 PWA 缓存。

**Tech Stack:** Python 3.12、FastAPI、Jinja2、PostgreSQL、Redis、httpx、Stripe、Frankfurter、GeoLite2、pytest。

**范围：** 规格太大，不能在一个任务里写完。下面按顺序做。每一段结束时网站都能启动，测试都绿。不要提前做下一段。

| 段 | 做完能验证什么 |
| --- | --- |
| 1 | 40 美元示例得到 4200 日元；日本是日语和日元；库存和欧洲运费档正确 |
| 2 | 首页、分类、搜索、商品详情按规格的区块顺序打开 |
| 3 | 购物车、结算、待支付订单、余额锁定、邮件和重置密码 |
| 4 | Stripe 收款、退款、发货、推荐返利、券、签到、桌面券 |
| 5 | 后台、广告位、优点生成、评价、500 并发读 |

执行本文件时只做第 1 段。第 2 段及以后在上一段测试通过后再写进各自的任务，不在第 1 段里搭空页面。

---

### Task 1: 结算纯函数

**Files:**
- Create: `shop/pricing.py`
- Test: `tests/test_shop_pricing.py`

- [ ] **Step 1: 写失败测试**

```python
from shop.pricing import quote

def test_japan_example_locks_4200_yen():
    result = quote(
        merchandise_cents=4000,
        tiers=[(3000, 400), (6000, 800)],
        coupon_cents=300,
        coupon_threshold_cents=2000,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=500,
        use_balance=True,
        units_per_usd=150,
        minor_units=0,
    )
    assert result.discount_cents == 400
    assert result.coupon_cents == 300
    assert result.shipping_cents == 0
    assert result.balance_cents == 500
    assert result.due_cents == 2800
    assert result.due_local == 4200


def test_japan_under_threshold_adds_7_dollars_shipping():
    result = quote(
        merchandise_cents=2500,
        tiers=[(3000, 400)],
        coupon_cents=0,
        coupon_threshold_cents=2000,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=0,
        use_balance=False,
        units_per_usd=150,
        minor_units=0,
    )
    assert result.shipping_cents == 700
    assert result.due_cents == 3200
    assert result.due_local == 4800


def test_highest_tier_only_and_balance_cannot_pay_shipping():
    result = quote(
        merchandise_cents=6000,
        tiers=[(3000, 400), (6000, 800)],
        coupon_cents=0,
        coupon_threshold_cents=0,
        free_shipping_cents=3900,
        shipping_cents=700,
        balance_cents=100000,
        use_balance=True,
        units_per_usd=1,
        minor_units=2,
    )
    assert result.discount_cents == 800
    assert result.balance_cents == 5200
    assert result.due_cents == 0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_shop_pricing.py -v`
Expected: FAIL，`shop.pricing` 不存在

- [ ] **Step 3: 实现**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Quote:
    discount_cents: int
    coupon_cents: int
    shipping_cents: int
    balance_cents: int
    due_cents: int
    due_local: int

def quote(*, merchandise_cents, tiers, coupon_cents, coupon_threshold_cents,
          free_shipping_cents, shipping_cents, balance_cents, use_balance,
          units_per_usd, minor_units):
    hit = [off for threshold, off in tiers if merchandise_cents >= threshold]
    discount = max(hit) if hit else 0
    coupon = coupon_cents if merchandise_cents >= coupon_threshold_cents else 0
    ship = 0 if merchandise_cents >= free_shipping_cents else shipping_cents
    goods_after = max(0, merchandise_cents - discount - coupon)
    balance = min(balance_cents, goods_after) if use_balance else 0
    due = goods_after + ship - balance
    factor = 10 ** minor_units
    local = int((due * units_per_usd * factor) / 100 + 0.5)
    return Quote(discount, coupon, ship, balance, due, local)
```

日元 `minor_units=0` 时，2800 美分 × 150 / 100 = 4200。有小数的货币把 `minor_units` 设为 2。

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_shop_pricing.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shop/pricing.py tests/test_shop_pricing.py
git commit -m "feat: quote checkout in usd cents then local currency"
```

### Task 2: 国家、语言、货币和运费档

**Files:**
- Create: `shop/locale.py`
- Test: `tests/test_shop_locale.py`

- [ ] **Step 1: 写失败测试**

```python
from shop.locale import resolve, shipping_tier

def test_japan_and_germany():
    assert resolve("JP") == ("ja", "JPY")
    assert resolve("DE") == ("de", "EUR")
    assert resolve("BR") == ("pt", "BRL")
    assert resolve("MX") == ("es", "MXN")
    assert resolve("GB") == ("en", "GBP")
    assert resolve("CA") == ("en", "CAD")
    assert resolve("US") == ("en", "USD")
    assert resolve("ZZ") == ("en", "USD")

def test_shipping_tiers():
    assert shipping_tier("JP") == "JP"
    assert shipping_tier("US") == "USCA"
    assert shipping_tier("CA") == "USCA"
    assert shipping_tier("MX") == "MXBR"
    assert shipping_tier("BR") == "MXBR"
    assert shipping_tier("DE") == "EU"
    assert shipping_tier("GB") == "EU"
    assert shipping_tier("CH") == "EU"
    assert shipping_tier("AU") == "USCA"
```

国家名单以规格「语言和货币」和「欧洲档」全文为准，测试再覆盖西班牙、法国、葡萄牙、奥地利。`shipping_tier` 的欧洲集合把规格里的 31 个国家都写进去，不许写成「欧盟」这种会变的判断。

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_shop_locale.py -v`
Expected: FAIL

- [ ] **Step 3: 实现 `resolve` 和 `shipping_tier`**

两个函数都只查表，不访问网络。未知国家：语言 `en`，货币 `USD`，运费档 `USCA`。

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_shop_locale.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add shop/locale.py tests/test_shop_locale.py
git commit -m "feat: map country to language, currency, and shipping tier"
```

### Task 3: 返利和库存占用

**Files:**
- Create: `shop/rewards.py`
- Test: `tests/test_shop_rewards.py`

- [ ] **Step 1: 写失败测试**

```python
from shop.rewards import rebate, apply_refund

def test_self_and_direct_referrer():
    own, direct = rebate(base_cents=3300, self_rate=0.05, direct_rate=0.10, referrer="d@x.com", buyer="e@x.com")
    assert own == 165
    assert direct == 330

def test_own_link_does_not_pay_twice():
    own, direct = rebate(base_cents=3300, self_rate=0.05, direct_rate=0.10, referrer="e@x.com", buyer="e@x.com")
    assert (own, direct) == (165, 0)

def test_refund_claws_back_only_available_balance():
    assert apply_refund(rebate_cents=500, available_cents=200) == 0
    assert apply_refund(rebate_cents=500, available_cents=800) == 300
```

基数是优惠后、扣余额前的商品金额。`apply_refund` 返回扣回后的可用余额，不低于 0。

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_shop_rewards.py -v`
Expected: FAIL

- [ ] **Step 3: 实现两个函数**
- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: Commit**

```bash
git add shop/rewards.py tests/test_shop_rewards.py
git commit -m "feat: compute direct rebate and refund clawback"
```

### Task 4: 数据库和 36 件示例商品

**Files:**
- Create: `shop/db.py`
- Create: `shop/seed.py`
- Test: `tests/test_shop_seed.py`

表：`products`（sku、品类、美元分、库存、六种语言的名称、4 条优点、详情、规格 JSON）、`rates`、`accounts`、`balances`、`orders`、`order_lines`、`coupons`、`coupon_grants`、`promos`、`ads`、`reviews`、`referrals`、`withdrawals`。

- [ ] **Step 1: 写失败测试**

```python
def test_seed_has_36_products_and_known_prices(db):
    rows = db.execute("select count(*) as n from products").fetchone()["n"]
    assert rows == 36
    rack = db.execute("select price_cents, stock from products where sku='drain-rack'").fetchone()
    assert rack["price_cents"] == 1200
    assert rack["stock"] == 100
    clip = db.execute("select price_cents from products where sku='binder-clip'").fetchone()
    assert clip["price_cents"] == 300
```

单价按规格「示例商品」清单：沥水架 12 美元，长尾夹 3 美元，其余同清单。sku 用英文短横线。

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_shop_seed.py -v`
Expected: FAIL

- [ ] **Step 3: 建表和种子**

测试使用 SQLite 内存库，生产配置指向 PostgreSQL。SQL 只用两边都支持的语句。种子同时写入规格里的满减、包邮、四档运费、五张券和 5%、10% 返利。

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: Commit**

```bash
git add shop/db.py shop/seed.py tests/test_shop_seed.py
git commit -m "feat: seed 36 catalog items and opening promos"
```

### Task 5: 当小时汇率

**Files:**
- Create: `shop/fx.py`
- Test: `tests/test_shop_fx.py`

- [ ] **Step 1: 写失败测试**

假 httpx 传输返回 Frankfurter 的 JSON。`rate_for("JPY", now)` 在同一小时返回同一数字。第二次调用不访问网络。这一小时请求失败时返回上一小时的值，并带 `stale=True`。没有任何历史时抛 `NoRate`。

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_shop_fx.py -v`
Expected: FAIL

- [ ] **Step 3: 实现**

向 `https://api.frankfurter.app/latest?from=USD&to=JPY,EUR,GBP,BRL,MXN,CAD` 取数。结果按协调世界时小时写入 `rates`。美元对美元是 1，不请求。

- [ ] **Step 4: 跑测试确认通过**
- [ ] **Step 5: Commit**

```bash
git add shop/fx.py tests/test_shop_fx.py
git commit -m "feat: cache frankfurter rates for one utc hour"
```

第 1 段到这里结束。运行：

```bash
pytest tests/test_shop_pricing.py tests/test_shop_locale.py tests/test_shop_rewards.py tests/test_shop_seed.py tests/test_shop_fx.py -v
```

Expected: 全部 PASS。然后停下来，再开始第 2 段。

---

## 第 2 段：页面骨架

做这些文件：`shop/app.py`、`shop/templates/*.html`、`shop/static/shop.css`、`tests/test_shop_pages.py`。

页面必须包含规格「页面」和「页面结构」里的区块，先用空数据渲染，交互放到第 3 段。

- [x] 首页含顶栏、搜索框、六个品类横滑的标题、商品网格
- [x] `GET /?country=JP` 响应是日语，价格带日元符号，沥水架显示由 12 美元换算的金额。没有 `country` 时用 GeoLite2，库不存在则按美国
- [x] 结算金额等于 `quote` 的当地货币结果，不另加税
- [x] `GET /?country=DE` 是德语和欧元
- [x] 商品详情含面包屑、购买区、4 条优点、详情、规格、评价区。无评价时 HTML 里没有星级字符
- [x] 分类和搜索有排序参数 `featured|price_asc|price_desc|newest` 和品类、价格筛选
- [x] 结算页和支付页模板不含广告槽标记 `data-ad`
- [x] 其余买家页和后台页都能 200，后台页在没有口令时 401
- [x] 视觉：白底、深色实心按钮、正文不小于 16px、按钮最小高度 44px。字体链接 Schibsted Grotesk 和 Noto Sans JP

测试用 FastAPI `TestClient`，汇率在测试里写成 150，不访问 Frankfurter。

## 第 3 段：购物车、结算、账号

- [x] 购物车存在浏览器 cookie。立即购买把单件写进 `checkout_line` cookie，不清空购物车
- [x] 商品页和购物车的运费用访问国家。结算提交用收货国家，订单里写入重算后的运费
- [x] 提交用表单里的 `submit_id`。相同 id 返回同一订单
- [x] 扣余额的事务锁住该邮箱余额行
- [x] 下单把库存减掉。库存不足返回结算页并标出商品。取消待支付订单把库存加回
- [x] 订单邮件和 30 分钟重置链接。测试用内存邮箱，不断言真实 SMTP
- [x] 不注册也能下单。结果页能设密码，之后 `POST /login` 能看到该订单

## 第 4 段：收款、券、推荐、签到、桌面

- [x] Stripe Checkout 使用订单上的货币。测试用 Stripe 的模拟事件把订单打成已支付，返利进入可用余额
- [x] 未支付只有待结算。自己的链接不产生第二笔。上一级邮箱余额不变
- [x] 后台退款调用 Stripe 退款后，状态为已退款，可用余额按 `apply_refund` 减少，库存加回
- [x] 分享券每个邮箱每个协调世界时日期每张模板最多一张。桌面券每个邮箱一次。签到券每个已登录邮箱每天一次
- [x] 第一次打开的推荐码写进浏览器一年。之后别的码不替换。第二次下单不再带链接也返给原推荐人
- [x] 提现低于 1000 美分被拒绝。达到后写入 `withdrawals` 并从可用余额划出
- [x] 已支付订单可填承运商和运单号。已发货买家可对每个商品写一条评价

## 第 5 段：后台、广告、优点、并发

- [x] 管理员口令来自环境变量。改价、改促销、改券后删除 Redis 商品缓存键
- [x] 广告位没有素材时响应里不出现空的 `data-ad` 容器。赞助商品带当前语言的赞助词。结算页没有广告位
- [x] 优点生成只接收名称、品类、材质、尺寸、重量。测试用假模型返回固定 4 条，确认评价表没有新增行
- [x] PWA manifest 和 service worker 只缓存 `/static/`。商品页请求带 `Cache-Control: no-store`
- [x] 压力：本机用 pytest 或一个小脚本对首页和商品页各打 500 个并发，错误率低于 1%。两个相同 `submit_id` 的并发结算只有一笔订单

## 规格对照

规格里的假评价、阿里巴巴采集、拼团、砍价、级差和团队奖不出现在任何任务里。优点只写商品文案。评价只允许已发货订单。

自检：第 1 段的测试数字和第 2 到第 5 段的清单覆盖规格里的页面、汇率、促销、推荐、账号、退款、广告、PWA 和并发。没有把「以后再写」留给结算公式。
