# Harbor 独立站改造需求 V2 —— 基于全文逐行审计

> 本版替代 `cursor-requirements.md`（R1–R9 已冻结）。旧版所有验收数字按「满 $25 包邮」写，与线上不一致，作废。
> 本版每个结论都附源码位置，可直接交给 Cursor 按行核实。

---

## 0. 审读范围与线上真值

### 0.1 已逐行读完的文件（Cursor 改前请以线上库为准复核）

| 文件 | 行数 | 说明 |
|---|---|---|
| `shop/app.py` | 4789 | 全部路由/渲染/会话/支付跳转 |
| `shop/db.py` | 335 | SCHEMA + migrate |
| `shop/checkout.py` | 504 | 购物车/下单/库存/Outbox |
| `shop/pay.py` | 737 | 支付三实现/发券/退款/发货/提现 |
| `shop/alibaba.py` | 599 | 定价核心 sku_price + hold 拦截 |
| `shop/package.py` | 391 | 聚水潭数据包解析 + 定价应用 |
| `shop/seed.py` | 171 | 默认配置（PROMOS/COUPONS/活动） |
| `shop/campaigns.py` | 185 | 活动/特价/缺口目标券 |
| `shop/ops.py` | 218 | 运营统计 board() |
| `shop/suggest.py` | 90 | 凑单打分 |
| `shop/markets.py` / `hot.py` / `ads.py` / `rewards.py` / `pricing.py` / `locale.py` | 全部 | 排序/热销/广告位/返佣/报价/国家分组 |
| 模板 16 个 | — | base/cart/checkout/product/order/payment/home/listing/card/pick/goal/sale/new/campaign/account/admin/admin_board |

未逐行读（对改造无实质影响）：`i18n.py`（多语言文案字典）、次要模板、`tests/` 30 个（覆盖 package/checkout/pay/pricing/campaigns/ops/suggest/hot/markets 等）。

### 0.2 线上真值（验收基准，全部来自代码默认 + 你审查确认）

| 项 | 线上现值 | 来源 |
|---|---|---|
| 包邮门槛 | **$39**（3900¢） | seed.py:90 + 后台 promos |
| 满减档 | **满 $30 减 $4、满 $60 减 $8** | seed.py:89 |
| 运费四档 | **US/CA $6、EU $8、JP $7、MX/BR $9** | seed.py:91 |
| 售价倍率 | 代码默认 **sale_rate=1.1**（后台 settings 可覆盖） | app.py:2822-2826 |
| 重量地板 | 30g/$1，重量价高出成本价 20% 即 hold | alibaba.py sku_price |
| 返佣 | 自购返 5%、直邀返 10% | seed.py:92-93 + rewards.py |
| 券 kind | 仅 public/first/share/desktop/checkin 5 种 | seed.py:97-101 + admin.html 白名单 |

> ⚠️ **第 5 行注意（用户裁定：不改倍率）**：代码默认 sale_rate=**1.1**，与「RMB ×1.3 = 美金售价」口径不同。但这是**改价**不是对齐——线上 DB 若已存过其他值，**以线上存量值为准**；倍率一律不动，只读确认现值即可（属 P0-A3 的 DB 快照范围）。

### 0.3 红线（本次改造一律不碰）

- 定价倍率与重量 hold 拦截逻辑（`alibaba.sku_price`、`package.py`）——你已裁定「超重要亏钱」，不动。
- 商品排序主键 `(promoted, rank, -heat)`——已够用（见 1.3）。
- 现有券玩法（share/desktop/checkin/checkin 签到、PWA 安装送券、邀请返佣）——已完整，不动。

---

## 1. 先纠正：这套系统已经有什么（旧方案错判的部分）

逐行读完后，旧方案 R1–R9 里有 **5 条其实已存在或部分存在**，不应再当作「要新建」：

| 旧需求 | 现状 | 证据 |
|---|---|---|
| R1 商品置顶权重 | **已存在**：排序是 `(0 if sponsored else 1, rank(country), -heat(country))`，商品页还有 markets 列做国家主推 | app.py:1276-1279（listing）、1373（home）、1386-1392（rails）、1393-1396（deal） |
| R3 跳档提示 | **已存在**：`nudge_for` 用 `suggest.gap()` 全量计算「满减下一档 + 包邮差距 + 券缺口」四合一，生成进度条与「还差 $X」文案 | app.py:1160-1187、suggest.py:1-11 |
| R9 漏斗统计 | **已存在**：`visits` 表（page/product/cart/order/sale/paid/refund/return 已埋点）+ `ops.board()` + `/admin/stats` 面板 | db.py:237-249、ops.py、app.py:2632 |
| 凑单推荐链路 | **已存在**：加购后 cart_picks（suggest.choose 打分：口味×2/同品类+6/贴近×8/预算内+40~60）、bundle_groups 品类弹层、gap_pick 一键补款、结算页 addons、商品页 related+picks、首页 foryou/recent/deals | app.py:1745-1818、suggest.py:64-90 |
| 离站挽留骨架 | **已存在**：pop-hold（$0.5-2 低价品）、pop-ship（买就送 gift）、pop-desk（PWA）、checkin/share 发券（grant_templates 唯一入口） | base.html、app.py:2505-2527、pay.py:717-732 |

**结论**：你问的四条主线里，**排序基本不用改，凑单/包邮提示/挽留骨架都已在线**。真正要补的是下面的「真缺口」。

---

## 2. 真缺口清单（改什么）

### P0-A 前提条件（不改代码，先办，否则下面几条验收过不了）

| # | 事项 | 为什么是前提 |
|---|---|---|
| A1 | **接通连连支付**（配 LIANLIAN_MERCHANT_ID/SUB/PRIVATE_KEY/PUBLIC_KEY/ENV/COUNTRY） | 现在没配密钥时兜底是 `MemoryStripe`：create_checkout 返回无 url → 渲染 payment.html awaiting → **订单永远 pending，永远到不了 paid**（app.py:2066-2121、pay.py:20-47）。R8 也依赖 paid 落地页 |
| A2 | **SMTP 服务商 + 真实公网域名** | 全站邮件目前只进内存 `Outbox`（checkout.py:25-31，append 即完事），**连密码重置都发不出去**。邮件相关改动（B4/P1-3）全部依赖真实发信 |
| A3 | **线上 DB 只读快照**：确认 settings（sale_rate/list_rate/hold_percent/grams_per_dollar）、promos、coupons、在架商品数 | 验收数字按 0.2 的现值；若线上 settings 已被改过，以线上为准 |

### P0-B 安全小改（低风险，建议第一批交给 Cursor）

| # | 缺口 | 现状（证据） | 改动点 | 验收 |
|---|---|---|---|---|
| B1 | **pending 订单超时释放库存**（你指出的系统级风险） | 下单即扣库存（checkout.py:371-375），只有手动 cancel（431-469）/refund 才释放，**无超时机制**，未付单永久占库存 | 新增一次性脚本（Linux cron 或 systemd timer，与 R7 同一套调度）调 `cancel_order`：status=pending 且 created_at 超过 N 分钟（建议 30）自动取消释放 | 模拟下单一笔不支付，30 分钟后库存恢复、订单变 cancelled；后台可见 |
| B2 | **后台运费四档不可编辑** | admin.html 促销表单只有满减+包邮门槛，运费仅展示（admin.html:692-694）；要改只能改 DB/seed | promos 表单加 4 个运费输入框 + POST 保存（读/写 shipping 字典，格式与现有 tiers 一致） | 后台把 USCA 运费改成 500，前台结算 US 订单运费显示 $5 |
| B3 | **券 kind 增加 `abandon`**（弃购挽回券） | 后台建券白名单只有 5 种，非白名单强制转 public（admin.html:560、app.py:3958） | 枚举加一项 `abandon`；`list_coupons`/`allowed_coupon` 已天然按 grant 型处理非 public/first kind（checkout.py:168-225），无需改校验；`next_coupon_goal` 已支持（campaigns.py:104-135） | 后台能建 kind=abandon 的券；未 grant 的账号用不了，grant 后能用 |
| B4 | **真实邮件发送**（全站 0 能力） | Outbox 是内存列表（checkout.py:25-31） | 加 SMTP 发送实现（配置读环境变量：SMTP_HOST/PORT/USER/PASS/FROM），`outbox.send` 改为真发信；失败落日志不阻塞下单 | 触发密码重置，能收到真实邮件 |
| B5 | **漏斗补 checkout_start 事件 + 凑单率指标** | visits 已埋 cart/order，缺结算页进入事件；/admin/stats 无凑单率 | 结算页 GET 时 `_track("checkout_start")`（参考现有点位 app.py:1704/2036）；ops.board 加「凑单率 = 满包邮订单数 ÷ 已支付订单数」「平均客单」 | /admin/stats 出现两指标，数字与 DB 一致。**（渠道追踪/U referrer 部分暂缓：等投流启动前再做，见运营文档 §4）** |

### P1 运营增强（中等改动，第二批）

| # | 对应旧需求 | 改动点 | 验收（按线上真值） |
|---|---|---|---|
| P1-1 | R5 弃购弹窗 v2 | 复用现有离站弹窗骨架（base.html pop 系 + showLeave），新增变体：「还差 $X 包邮，领券再减 $Y」——差值读 `promos.free_shipping_cents` 动态值（**不写死 $25**）；领券走 `grant_templates(conn, email, kind, day)`（pay.py:717，day 可传 "once"）；游客点领券 → 引导留邮箱（弹窗内嵌邮箱输入，复用 claim 样式） | 购物车有货、未满 $39 时离站弹出，显示「还差 $6.4」；留邮箱后 coupon_grants 出现记录；结算可用 |
| P1-2 | R4 全局免邮进度条 | 现在只有 cart/checkout 有 goal 进度条，首页/商品页只有 promise_line 纯文字（base.html:42） | 把 promise_line 区块升级为轻量进度条组件（读后台 free_shipping_cents），home/product 均可见 | 首页显示「还差 $X 免邮」+ 进度条，改后台门槛后数字联动 |
| P1-3 | R7 邮件三连 | 基于 B4 真发信：① 下单即发「订单确认」；② 弃购挽回（cart 落库用户，下单后 1h/24h 两封，含差额+券）；③ 复购唤醒（paid 后 7 天，基于历史订单） | 调度用 **Linux cron/systemd**（站跑 Linux，不是 Windows 计划任务）；只对**已登录/留过邮箱**的会话有效（这是硬限制，访客购物车是 cookie 追不到） | 留邮箱用户弃购后收到两封挽回邮件，邮件内券可核销 |
| P1-4 | R6 购物车落库 | 购物车只存 cookie（checkout.py:56-73 解析），换设备即丢 | 新建 `carts` 表 + 登录/留邮箱用户落库（buyer_email 已有，app.py:1070-1075）；登录时 cookie 车与库合并 | 登录用户换设备购物车还在；访客行为不受影响 |

### P2 冻结 / 不做（写明理由）

| # | 旧需求 | 结论 | 理由 |
|---|---|---|---|
| P2-1 | R8 支付后换购 | **冻结**，解锁条件：A1 连连接通、订单能到 paid | 现在订单永远 pending，没有 paid 落地页可挂。解锁后落点在 order.html 的 paid 分支（已确认该页存在） |
| P2-2 | R1 商品置顶 | **不做** | 排序已有 promoted+国家主推+热销三级（1.3 证据），在架约 700+ 品，再加置顶列只会挤后台 |
| P2-3 | 组合包/锚定（R2 的 bundle deal） | **暂不建表** | 先用现有 seckill/newcomer 活动特价承载「组合促销」（运营配置，不改代码）；若后续验证凑单率仍上不去，再加 bundle 表 |

---

## 3. 给 Cursor 的实施顺序与验证

1. 改前：`pytest`（30 个测试）跑一遍留基线；确认线上 DB 快照（A3）。
2. 按 P0-B（B1→B2→B3→B4→B5）→ P1（P1-1→P1-2→P1-3→P1-4）顺序实施；每项独立提交，便于回滚。**B5 的渠道追踪部分暂缓，投流启动前再做。**
3. 回归：pytest 全绿；本机起站（`uvicorn shop.app:app`，**注意 start.bat 启动的是 app/main.py 的工具项目，不是商店**）手动过一遍：加购→凑单提示→结算→（配密钥后）支付→订单页。
4. 调度类（B1 超时释放、P1-3 邮件三连）在**生产 Linux** 上配 cron/systemd，不写进 Windows 计划任务。

---

## 4. 与运营打法配合的配置建议（不改代码）

- **引流品**：你的 $1.99 级单品用 seckill 特价承载（campaigns 后台可配 4-8 个秒杀品，价格任意）+ 广告位 sponsored 置顶；不碰 alibaba 定价。
- **凑单率生死线 60%**：P1-1/P1-2 上线后，用 B5 的凑单率指标看每周走势；低于 60% 时先调「差 X 包邮送券」的面额/门槛，再考虑组合包。
- **复购摊 CAC**：rewards 返佣（自购 5%/直邀 10%）+ P1-3 复购邮件 + buy_again 按钮（已存在）三件套。
- **数据闭环**：/admin/stats 漏斗（访问→加购→下单→支付）看转化瓶颈在哪一段，逐档调。

---

## 5. 验收口径提醒（防旧坑）

- 所有页面数字验收按 **$39 包邮、满 $30-$4、满 $60-$8、运费 $6/$8/$7/$9**，任何改动不得写死 $25/$30-$3。
- 涉及「差多少包邮」的 UI，一律读 `promos.free_shipping_cents` / `tiers` 动态值。
- 定价倍率、重量拦截、排序主键、现有券玩法：**改之前先问，默认不动**。
