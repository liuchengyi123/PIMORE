import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from shop.checkout import email_lock, stock_parent
from shop.ops import note_paid, note_refund
from shop.rewards import apply_refund
from shop.seo import ORIGIN


class MemoryStripe:
    def __init__(self):
        self.checkouts = []
        self.refunds = []

    def create_checkout(self, *, order_id, amount, currency):
        row = {
            "order_id": int(order_id),
            "amount": int(amount),
            "currency": currency.lower(),
        }
        self.checkouts.append(row)
        return row

    def refund(self, *, order_id, amount, currency):
        row = {
            "order_id": int(order_id),
            "amount": int(amount),
            "currency": currency.lower(),
        }
        self.refunds.append(row)
        return row

    def find(self, order_id):
        for row in self.checkouts:
            if row["order_id"] == int(order_id):
                return row
        return None


class StripeError(Exception):
    pass


class LianLianError(StripeError):
    pass


def _drop_empty(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, child in value.items():
            if child is None or child == "":
                continue
            if isinstance(child, (dict, list)):
                child = _drop_empty(child)
                if child in ({}, []):
                    continue
            cleaned[key] = child
        return cleaned
    if isinstance(value, list):
        return [_drop_empty(item) for item in value if item is not None]
    return value


def sign_factor(value):
    if isinstance(value, dict):
        parts = []
        for key in sorted(value):
            child = value[key]
            if child is None:
                continue
            if isinstance(child, (dict, list)):
                inner = sign_factor(child)
                if inner:
                    parts.append(inner)
            else:
                parts.append(f"{key}={_sign_leaf(child)}")
        return "&".join(parts)
    if isinstance(value, list):
        parts = []
        for item in value:
            if item is None:
                continue
            if isinstance(item, (dict, list)):
                inner = sign_factor(item)
                if inner:
                    parts.append(inner)
            else:
                parts.append(_sign_leaf(item))
        return "&".join(parts)
    return _sign_leaf(value)


def _sign_leaf(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _money_text(amount, currency):
    places = 0 if str(currency).upper() == "JPY" else 2
    scale = 10 ** places
    value = int(amount) / scale
    if places == 0:
        return str(int(round(value)))
    return f"{value:.{places}f}"


def _pem(text, kind):
    body = (text or "").strip()
    if not body:
        raise LianLianError("key")
    if "BEGIN" in body:
        return body.encode()
    label = "PRIVATE KEY" if kind == "private" else "PUBLIC KEY"
    lines = [body[index:index + 64] for index in range(0, len(body), 64)]
    return ("-----BEGIN " + label + "-----\n" + "\n".join(lines) + "\n-----END " + label + "-----\n").encode()


def _private_key(text):
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    return load_pem_private_key(_pem(text, "private"), password=None)


def _public_key(text):
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    return load_pem_public_key(_pem(text, "public"))


def _rsa_sign(private_key, content):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    signed = private_key.sign(content.encode(), padding.PKCS1v15(), hashes.SHA1())
    return base64.b64encode(signed).decode()


def _rsa_verify(public_key, content, signature):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    try:
        public_key.verify(base64.b64decode(signature), content.encode(), padding.PKCS1v15(), hashes.SHA1())
    except (InvalidSignature, ValueError):
        return False
    return True


class LianLianCheckout:
    def __init__(self, conn, merchant_id, sub_merchant_id, private_key, public_key="", sandbox=True, country="CN"):
        self.conn = conn
        self.merchant_id = merchant_id.strip()
        self.sub_merchant_id = sub_merchant_id.strip()
        self.private_key = _private_key(private_key)
        self.public_key = _public_key(public_key) if public_key.strip() else None
        self.country = (country or "CN").strip().upper()[:2]
        host = "celer-api.LianLianpay-inc.com" if sandbox else "gpapi.lianlianpay.com"
        self.base = f"https://{host}"

    def create_checkout(self, *, order_id, amount, currency):
        order_id = int(order_id)
        amount = int(amount)
        currency = str(currency or "USD").upper()
        order = self.conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if order is None:
            raise LianLianError("order")
        stamp = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y%m%d%H%M%S")
        txn = f"h{order_id}t{stamp}"
        total = _money_text(amount, currency)
        name = (order["ship_name"] or "Customer").strip() or "Customer"
        parts = name.split()
        first, last = parts[0], parts[-1] if len(parts) > 1 else parts[0]
        payload = _drop_empty({
            "merchant_transaction_id": txn,
            "merchant_id": self.merchant_id,
            "sub_merchant_id": self.sub_merchant_id,
            "notification_url": f"{ORIGIN}/lianlian/notify",
            "redirect_url": f"{ORIGIN}/orders/{order_id}/lianlian",
            "cancel_url": f"{ORIGIN}/orders/{order_id}",
            "country": self.country,
            "merchant_order": {
                "merchant_order_id": str(order_id),
                "merchant_order_time": stamp,
                "order_description": f"Harbor order {order_id}",
                "order_amount": total,
                "order_currency_code": currency,
                "products": [{
                    "product_id": "harbor",
                    "name": f"Harbor order {order_id}",
                    "price": total,
                    "quantity": 1,
                    "sku": "harbor",
                    "url": ORIGIN,
                }],
            },
            "customer": {
                "customer_type": "I",
                "full_name": name,
                "first_name": first,
                "last_name": last,
                "email": order["email"],
            },
            "shipping": {
                "name": name,
                "first_name": first,
                "last_name": last,
                "phone": (order["phone"] or "").strip(),
                "address": {
                    "line1": (order["address"] or "").strip(),
                    "city": (order["city"] or "").strip(),
                    "state": (order["region"] or "").strip(),
                    "country": (order["ship_country"] or "US").strip().upper(),
                    "postal_code": (order["postal"] or "").strip(),
                },
            },
        })
        created = self._post(f"/v3/merchants/{self.merchant_id}/payments", payload)
        order_node = created.get("order") or {}
        url = str(order_node.get("payment_url") or created.get("payment_url") or "")
        ll_id = str(order_node.get("ll_transaction_id") or "")
        if not url:
            raise LianLianError(str(created.get("return_message") or "checkout")[:180])
        self.conn.execute(
            """
            insert into stripe_sessions (order_id, amount, currency, session_id, payment_intent)
            values (?, ?, ?, ?, ?)
            on conflict(order_id) do update set
                amount = excluded.amount,
                currency = excluded.currency,
                session_id = excluded.session_id,
                payment_intent = excluded.payment_intent
            """,
            (order_id, amount, currency.lower(), txn, ll_id),
        )
        self.conn.commit()
        return {"order_id": order_id, "amount": amount, "currency": currency.lower(), "url": url, "id": txn}

    def refund(self, *, order_id, amount, currency):
        raise LianLianError("refund")

    def find(self, order_id):
        row = self.conn.execute(
            "select order_id, amount, currency, session_id, payment_intent from stripe_sessions where order_id = ?",
            (int(order_id),),
        ).fetchone()
        if row is None:
            return None
        return {
            "order_id": int(row["order_id"]),
            "amount": int(row["amount"]),
            "currency": row["currency"],
            "session_id": row["session_id"],
            "payment_intent": row["payment_intent"],
        }

    def remember_intent(self, order_id, intent):
        self.conn.execute(
            "update stripe_sessions set payment_intent = ? where order_id = ?",
            (str(intent), int(order_id)),
        )
        self.conn.commit()

    def finish(self, order_id):
        row = self.find(order_id)
        if row is None or not row["session_id"]:
            return False
        return self._settle(row["session_id"])

    def accept_notify(self, raw, signature):
        try:
            payload = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return False
        if self.public_key:
            if not signature or not _rsa_verify(self.public_key, sign_factor(payload), signature):
                return False
        txn = str(payload.get("merchant_transaction_id") or "")
        if not txn:
            return False
        return self._settle(txn)

    def _settle(self, txn):
        saved = self.conn.execute(
            "select order_id, amount, currency from stripe_sessions where session_id = ?",
            (txn,),
        ).fetchone()
        if saved is None:
            return False
        order = self.conn.execute("select status from orders where id = ?", (saved["order_id"],)).fetchone()
        if order is None:
            return False
        if order["status"] != "pending":
            return order["status"] in {"paid", "shipped"}
        remote = self._get(f"/v3/merchants/{self.merchant_id}/payments/{txn}", {
            "merchant_id": self.merchant_id,
            "merchant_transaction_id": txn,
        })
        node = remote.get("order") if isinstance(remote.get("order"), dict) else remote
        data = node.get("payment_data") if isinstance(node.get("payment_data"), dict) else node
        status = str((data or {}).get("payment_status") or node.get("payment_status") or "")
        paid_amount = str((data or {}).get("payment_amount") or "")
        paid_currency = str((data or {}).get("payment_currency_code") or "").lower()
        if status != "PS":
            return False
        if paid_amount and paid_amount != _money_text(saved["amount"], saved["currency"]):
            return False
        if paid_currency and paid_currency != str(saved["currency"]).lower():
            return False
        ll_id = str(node.get("ll_transaction_id") or "")
        if ll_id:
            self.remember_intent(saved["order_id"], ll_id)
        return bool(mark_paid(self.conn, saved["order_id"]))

    def _post(self, path, payload):
        return self._send(path, payload, "POST")

    def _get(self, path, factors):
        return self._send(path, factors, "GET")

    def _send(self, path, payload, method):
        stamp = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y%m%d%H%M%S")
        signature = _rsa_sign(self.private_key, sign_factor(payload))
        body = None if method == "GET" else json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        request = Request(
            self.base + path,
            data=body,
            method=method,
            headers={
                "signature": signature,
                "timezone": "Asia/Hong_Kong",
                "timestamp": stamp,
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode())
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:180]
            raise LianLianError(detail or "lianlian") from exc



class PayPalError(StripeError):
    pass


class PayPalCheckout:
    """PayPal Business Checkout (Orders API v2 + Capture)."""

    def __init__(self, conn, client_id, client_secret, webhook_id="", sandbox=True):
        self.conn = conn
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.webhook_id = (webhook_id or "").strip()
        self.sandbox = bool(sandbox)
        host = "api-m.sandbox.paypal.com" if self.sandbox else "api-m.paypal.com"
        self.base = f"https://{host}"
        self._token_cache = {"access_token": "", "expires_at": 0}

    def create_checkout(self, *, order_id, amount, currency):
        order_id = int(order_id)
        amount = int(amount)
        currency = str(currency or "USD").upper()
        order = self.conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
        if order is None:
            raise PayPalError("order")
        total = _money_text(amount, currency)
        name = (order["ship_name"] or "Customer").strip() or "Customer"
        payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": str(order_id),
                "custom_id": str(order_id),
                "description": f"Harbor order {order_id}",
                "amount": {
                    "currency_code": currency,
                    "value": total,
                },
                "shipping": {
                    "name": {"full_name": name[:300]},
                    "address": {
                        "address_line_1": (order["address"] or "").strip()[:300] or "Address",
                        "admin_area_2": (order["city"] or "").strip()[:120] or "City",
                        "admin_area_1": (order["region"] or "").strip()[:120] or "N/A",
                        "postal_code": (order["postal"] or "").strip()[:60] or "00000",
                        "country_code": (order["ship_country"] or "US").strip().upper()[:2],
                    },
                },
            }],
            "application_context": {
                "brand_name": "Harbor",
                "landing_page": "LOGIN",
                "user_action": "PAY_NOW",
                "shipping_preference": "SET_PROVIDED_ADDRESS",
                "return_url": f"{ORIGIN}/orders/{order_id}/paypal",
                "cancel_url": f"{ORIGIN}/orders/{order_id}",
            },
        }
        created = self._api("POST", "/v2/checkout/orders", payload)
        pp_id = str(created.get("id") or "")
        url = ""
        for link in created.get("links") or []:
            if str(link.get("rel") or "") == "approve":
                url = str(link.get("href") or "")
                break
        if not pp_id or not url:
            raise PayPalError(str(created.get("message") or created.get("name") or "checkout")[:180])
        self.conn.execute(
            """
            insert into stripe_sessions (order_id, amount, currency, session_id, payment_intent)
            values (?, ?, ?, ?, '')
            on conflict(order_id) do update set
                amount = excluded.amount,
                currency = excluded.currency,
                session_id = excluded.session_id,
                payment_intent = excluded.payment_intent
            """,
            (order_id, amount, currency.lower(), pp_id),
        )
        self.conn.commit()
        return {"order_id": order_id, "amount": amount, "currency": currency.lower(), "url": url, "id": pp_id}

    def refund(self, *, order_id, amount, currency):
        row = self.find(order_id)
        capture_id = (row or {}).get("payment_intent") or ""
        if not capture_id:
            raise PayPalError("refund")
        currency = str(currency or "USD").upper()
        self._api("POST", f"/v2/payments/captures/{capture_id}/refund", {
            "amount": {
                "currency_code": currency,
                "value": _money_text(int(amount), currency),
            },
        })
        return {"order_id": int(order_id), "amount": int(amount), "currency": currency.lower()}

    def find(self, order_id):
        row = self.conn.execute(
            "select order_id, amount, currency, session_id, payment_intent from stripe_sessions where order_id = ?",
            (int(order_id),),
        ).fetchone()
        if row is None:
            return None
        return {
            "order_id": int(row["order_id"]),
            "amount": int(row["amount"]),
            "currency": row["currency"],
            "session_id": row["session_id"],
            "payment_intent": row["payment_intent"],
        }

    def remember_intent(self, order_id, intent):
        self.conn.execute(
            "update stripe_sessions set payment_intent = ? where order_id = ?",
            (str(intent), int(order_id)),
        )
        self.conn.commit()

    def finish(self, order_id, token=""):
        row = self.find(order_id)
        if row is None:
            return False
        pp_id = str(token or row["session_id"] or "").strip()
        if not pp_id:
            return False
        if pp_id != row["session_id"]:
            # PayPal return token should match the stored order id
            return False
        return self._settle(pp_id)

    def accept_notify(self, raw, headers):
        try:
            payload = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return False
        if self.webhook_id:
            if not self._verify_webhook(raw, headers, payload):
                return False
        event = str(payload.get("event_type") or "")
        resource = payload.get("resource") if isinstance(payload.get("resource"), dict) else {}
        pp_id = ""
        if event in {"CHECKOUT.ORDER.APPROVED", "CHECKOUT.ORDER.COMPLETED"}:
            pp_id = str(resource.get("id") or "")
        elif event in {"PAYMENT.CAPTURE.COMPLETED", "PAYMENT.CAPTURE.PENDING"}:
            # link back via supplementary_data / custom_id / related order
            supp = resource.get("supplementary_data") if isinstance(resource.get("supplementary_data"), dict) else {}
            related = supp.get("related_ids") if isinstance(supp.get("related_ids"), dict) else {}
            pp_id = str(related.get("order_id") or "")
            if not pp_id:
                custom = str(resource.get("custom_id") or "")
                if custom.isdigit():
                    saved = self.find(int(custom))
                    if saved:
                        pp_id = saved["session_id"]
        if not pp_id:
            return False
        return self._settle(pp_id)

    def _settle(self, pp_id):
        saved = self.conn.execute(
            "select order_id, amount, currency, session_id, payment_intent from stripe_sessions where session_id = ?",
            (pp_id,),
        ).fetchone()
        if saved is None:
            return False
        order = self.conn.execute("select status from orders where id = ?", (saved["order_id"],)).fetchone()
        if order is None:
            return False
        if order["status"] != "pending":
            return order["status"] in {"paid", "shipped"}
        try:
            remote = self._api("GET", f"/v2/checkout/orders/{pp_id}")
        except PayPalError:
            return False
        status = str(remote.get("status") or "")
        if status == "APPROVED":
            try:
                remote = self._api("POST", f"/v2/checkout/orders/{pp_id}/capture", {})
            except PayPalError:
                return False
            status = str(remote.get("status") or "")
        if status != "COMPLETED":
            return False
        paid_ok = False
        capture_id = ""
        for unit in remote.get("purchase_units") or []:
            ref = str(unit.get("reference_id") or unit.get("custom_id") or "")
            if ref and ref != str(saved["order_id"]):
                continue
            amount = unit.get("amount") if isinstance(unit.get("amount"), dict) else {}
            # capture response nests amount under payments.captures
            payments = unit.get("payments") if isinstance(unit.get("payments"), dict) else {}
            captures = payments.get("captures") if isinstance(payments.get("captures"), list) else []
            if captures:
                cap = captures[0] if isinstance(captures[0], dict) else {}
                capture_id = str(cap.get("id") or "")
                cap_status = str(cap.get("status") or "")
                amount = cap.get("amount") if isinstance(cap.get("amount"), dict) else amount
                if cap_status and cap_status not in {"COMPLETED", "PENDING"}:
                    continue
            value = str(amount.get("value") or "")
            code = str(amount.get("currency_code") or "").lower()
            if value and value != _money_text(saved["amount"], saved["currency"]):
                continue
            if code and code != str(saved["currency"]).lower():
                continue
            paid_ok = True
            break
        if not paid_ok:
            # fallback: top-level purchase unit amount on GET before nested captures
            units = remote.get("purchase_units") or []
            if len(units) == 1 and str(remote.get("status") or "") == "COMPLETED":
                amount = units[0].get("amount") if isinstance(units[0].get("amount"), dict) else {}
                value = str(amount.get("value") or "")
                code = str(amount.get("currency_code") or "").lower()
                if (not value or value == _money_text(saved["amount"], saved["currency"])) and (
                    not code or code == str(saved["currency"]).lower()
                ):
                    paid_ok = True
        if not paid_ok:
            return False
        if capture_id:
            self.remember_intent(saved["order_id"], capture_id)
        return bool(mark_paid(self.conn, saved["order_id"]))

    def _verify_webhook(self, raw, headers, payload):
        if not isinstance(headers, dict):
            headers = {}
        transmission_id = headers.get("paypal-transmission-id") or headers.get("PayPal-Transmission-Id") or ""
        timestamp = headers.get("paypal-transmission-time") or headers.get("PayPal-Transmission-Time") or ""
        cert_url = headers.get("paypal-cert-url") or headers.get("PayPal-Cert-Url") or ""
        auth_algo = headers.get("paypal-auth-algo") or headers.get("PayPal-Auth-Algo") or ""
        transmission_sig = headers.get("paypal-transmission-sig") or headers.get("PayPal-Transmission-Sig") or ""
        if not all([transmission_id, timestamp, cert_url, auth_algo, transmission_sig, self.webhook_id]):
            return False
        body = raw.decode() if isinstance(raw, bytes) else str(raw)
        try:
            result = self._api("POST", "/v1/notifications/verify-webhook-signature", {
                "transmission_id": transmission_id,
                "transmission_time": timestamp,
                "cert_url": cert_url,
                "auth_algo": auth_algo,
                "transmission_sig": transmission_sig,
                "webhook_id": self.webhook_id,
                "webhook_event": payload,
            })
        except PayPalError:
            return False
        return str(result.get("verification_status") or "") == "SUCCESS"

    def _token(self):
        now = time.time()
        if self._token_cache["access_token"] and self._token_cache["expires_at"] > now + 60:
            return self._token_cache["access_token"]
        auth = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        request = Request(
            self.base + "/v1/oauth2/token",
            data=b"grant_type=client_credentials",
            method="POST",
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                data = json.loads(response.read().decode())
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:180]
            raise PayPalError(detail or "token") from exc
        token = str(data.get("access_token") or "")
        if not token:
            raise PayPalError("token")
        expires = int(data.get("expires_in") or 300)
        self._token_cache = {"access_token": token, "expires_at": now + expires}
        return token

    def _api(self, method, path, payload=None):
        body = None
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "Content-Type": "application/json",
        }
        if method == "POST" and path.endswith("/capture"):
            headers["PayPal-Request-Id"] = secrets.token_hex(16)
        if payload is not None and method != "GET":
            body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
        request = Request(
            self.base + path,
            data=body,
            method=method,
            headers=headers,
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode()
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:180]
            raise PayPalError(detail or "paypal") from exc


class StripeCheckout:
    def __init__(self, conn, secret, webhook_secret=""):
        self.conn = conn
        self.secret = secret
        self.webhook_secret = webhook_secret or ""

    def create_checkout(self, *, order_id, amount, currency):
        order_id = int(order_id)
        amount = int(amount)
        currency = currency.lower()
        success = f"{ORIGIN}/orders/{order_id}?session_id={{CHECKOUT_SESSION_ID}}"
        cancel = f"{ORIGIN}/orders/{order_id}"
        payload = urlencode([
            ("mode", "payment"),
            ("success_url", success),
            ("cancel_url", cancel),
            ("client_reference_id", str(order_id)),
            ("metadata[order_id]", str(order_id)),
            ("line_items[0][quantity]", "1"),
            ("line_items[0][price_data][currency]", currency),
            ("line_items[0][price_data][unit_amount]", str(amount)),
            ("line_items[0][price_data][product_data][name]", f"Harbor order {order_id}"),
        ])
        created = self._post("/v1/checkout/sessions", payload)
        session_id = str(created.get("id") or "")
        url = str(created.get("url") or "")
        if not session_id or not url:
            raise StripeError("checkout")
        self.conn.execute(
            """
            insert into stripe_sessions (order_id, amount, currency, session_id, payment_intent)
            values (?, ?, ?, ?, '')
            on conflict(order_id) do update set
                amount = excluded.amount,
                currency = excluded.currency,
                session_id = excluded.session_id
            """,
            (order_id, amount, currency, session_id),
        )
        self.conn.commit()
        return {"order_id": order_id, "amount": amount, "currency": currency, "url": url, "id": session_id}

    def refund(self, *, order_id, amount, currency):
        row = self.find(order_id)
        intent = (row or {}).get("payment_intent") or ""
        if not intent:
            raise StripeError("refund")
        self._post("/v1/refunds", urlencode([
            ("payment_intent", intent),
            ("amount", str(int(amount))),
        ]))
        return {"order_id": int(order_id), "amount": int(amount), "currency": currency.lower()}

    def find(self, order_id):
        row = self.conn.execute(
            "select order_id, amount, currency, session_id, payment_intent from stripe_sessions where order_id = ?",
            (int(order_id),),
        ).fetchone()
        if row is None:
            return None
        return {
            "order_id": int(row["order_id"]),
            "amount": int(row["amount"]),
            "currency": row["currency"],
            "session_id": row["session_id"],
            "payment_intent": row["payment_intent"],
        }

    def remember_intent(self, order_id, intent):
        self.conn.execute(
            "update stripe_sessions set payment_intent = ? where order_id = ?",
            (str(intent), int(order_id)),
        )
        self.conn.commit()

    def confirm(self, session_id):
        session_id = str(session_id or "")
        if not session_id.startswith("cs_"):
            return False
        try:
            session = self._get(f"/v1/checkout/sessions/{session_id}")
        except StripeError:
            return False
        if session.get("payment_status") not in {"paid", "no_payment_required"}:
            return False
        return handle_event(self.conn, self, {
            "type": "checkout.session.completed",
            "data": {"object": session},
        })

    def valid_signature(self, payload, header):
        if not self.webhook_secret or not header:
            return False
        parts = {}
        signatures = []
        for item in str(header).split(","):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            if key == "v1":
                signatures.append(value)
            else:
                parts[key] = value
        timestamp = parts.get("t")
        if not timestamp or not signatures:
            return False
        try:
            if abs(time.time() - int(timestamp)) > 300:
                return False
        except ValueError:
            return False
        signed = f"{timestamp}.".encode() + payload
        expected = hmac.new(self.webhook_secret.encode(), signed, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, sig) for sig in signatures)

    def _post(self, path, body):
        return self._send(path, body.encode())

    def _get(self, path):
        return self._send(path, None)

    def _send(self, path, body):
        request = Request(
            "https://api.stripe.com" + path,
            data=body,
            method="POST" if body is not None else "GET",
            headers={
                "Authorization": f"Bearer {self.secret}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        try:
            with urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode())
        except HTTPError as exc:
            raise StripeError("stripe") from exc


def _credit(conn, email, cents):
    if not email or cents <= 0:
        return
    conn.execute(
        """
        insert into balances (email, available_cents) values (?, ?)
        on conflict(email) do update set available_cents = available_cents + excluded.available_cents
        """,
        (email, cents),
    )


def _locks_for(emails):
    return [email_lock(email) for email in sorted({email for email in emails if email})]


def mark_paid(conn, order_id):
    preview = conn.execute(
        "select email, referrer_email from orders where id = ?",
        (order_id,),
    ).fetchone()
    if preview is None:
        return False
    locks = _locks_for((preview["email"], preview["referrer_email"]))
    for lock in locks:
        lock.acquire()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            order = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
            if order is None or order["status"] != "pending":
                conn.rollback()
                return False
            conn.execute("update orders set status = 'paid' where id = ?", (order_id,))
            _credit(conn, order["email"], order["self_rebate_cents"])
            _credit(conn, order["referrer_email"], order["direct_rebate_cents"])
            note_paid(conn, order)
            paid_snapshot = dict(order)
            conn.commit()
            try:
                from shop.adtrack import notify_purchase

                notify_purchase(conn, paid_snapshot)
            except Exception:
                pass
            return True
        except Exception:
            conn.rollback()
            raise
    finally:
        for lock in reversed(locks):
            lock.release()


def handle_event(conn, stripe, event):
    if event.get("type") != "checkout.session.completed":
        return False
    obj = event.get("data", {}).get("object", {})
    metadata = obj.get("metadata") or {}
    if "order_id" not in metadata:
        return False
    order_id = int(metadata["order_id"])
    session = stripe.find(order_id)
    if session is None:
        return False
    if str(obj.get("currency") or "").lower() != session["currency"]:
        return False
    if int(obj.get("amount_total") or 0) != session["amount"]:
        return False
    intent = str(obj.get("payment_intent") or "")
    remember = getattr(stripe, "remember_intent", None)
    if intent and remember:
        remember(order_id, intent)
    return mark_paid(conn, order_id)


def refund_order(conn, stripe, order_id):
    preview = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
    if preview is None or preview["status"] not in {"paid", "shipped"}:
        return False
    stripe.refund(
        order_id=preview["id"],
        amount=preview["due_local"],
        currency=preview["currency"],
    )
    locks = _locks_for((preview["email"], preview["referrer_email"]))
    for lock in locks:
        lock.acquire()
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            order = conn.execute("select * from orders where id = ?", (order_id,)).fetchone()
            if order is None or order["status"] not in {"paid", "shipped"}:
                conn.rollback()
                return False
            for email, cents in (
                (order["email"], order["self_rebate_cents"]),
                (order["referrer_email"], order["direct_rebate_cents"]),
            ):
                if not email or cents <= 0:
                    continue
                conn.execute(
                    """
                    insert into balances (email, available_cents) values (?, 0)
                    on conflict(email) do update set available_cents = available_cents
                    """,
                    (email,),
                )
                available = conn.execute(
                    "select available_cents from balances where email = ?",
                    (email,),
                ).fetchone()["available_cents"]
                conn.execute(
                    "update balances set available_cents = ? where email = ?",
                    (apply_refund(cents, available), email),
                )
            lines = conn.execute(
                "select sku, qty from order_lines where order_id = ?",
                (order_id,),
            ).fetchall()
            for line in lines:
                conn.execute(
                    "update products set stock = stock + ? where sku = ?",
                    (line["qty"], stock_parent(line["sku"])),
                )
            conn.execute("update orders set status = 'refunded' where id = ?", (order_id,))
            note_refund(conn, order, lines)
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise
    finally:
        for lock in reversed(locks):
            lock.release()


def ship_order(conn, order_id, carrier, tracking):
    carrier = (carrier or "").strip()
    tracking = (tracking or "").strip()
    if not carrier or not tracking:
        return False
    order = conn.execute("select status from orders where id = ?", (order_id,)).fetchone()
    if order is None or order["status"] != "paid":
        return False
    conn.execute(
        "update orders set status = 'shipped', carrier = ?, tracking = ? where id = ?",
        (carrier, tracking, order_id),
    )
    return True


def add_review(conn, email, sku, rating, body):
    body = (body or "").strip()
    try:
        rating = int(rating)
    except (TypeError, ValueError):
        return False
    if rating < 1 or rating > 5 or not body:
        return False
    shipped = conn.execute(
        """
        select 1 as ok from orders o
        join order_lines l on l.order_id = o.id
        where o.email = ? and o.status = 'shipped' and l.sku = ?
        """,
        (email, sku),
    ).fetchone()
    if shipped is None:
        return False
    try:
        conn.execute(
            "insert into reviews (sku, email, rating, body) values (?, ?, ?, ?)",
            (sku, email, rating, body),
        )
    except sqlite3.IntegrityError:
        return False
    return True


def request_withdrawal(conn, email, amount_cents, payout_account):
    payout_account = (payout_account or "").strip()
    if amount_cents < 1000 or not payout_account:
        return False
    with email_lock(email):
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """
                insert into balances (email, available_cents) values (?, 0)
                on conflict(email) do update set available_cents = available_cents
                """,
                (email,),
            )
            available = conn.execute(
                "select available_cents from balances where email = ?",
                (email,),
            ).fetchone()["available_cents"]
            if available < amount_cents:
                conn.rollback()
                return False
            conn.execute(
                "update balances set available_cents = available_cents - ? where email = ?",
                (amount_cents, email),
            )
            conn.execute(
                """
                insert into withdrawals (email, amount_cents, payout_account, status)
                values (?, ?, ?, 'pending')
                """,
                (email, amount_cents, payout_account),
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            raise


def ensure_code(conn, email):
    row = conn.execute("select code from referrals where email = ?", (email,)).fetchone()
    if row:
        return row["code"]
    code = secrets.token_hex(6)
    conn.execute("insert into referrals (email, code) values (?, ?)", (email, code))
    return code


def grant_templates(conn, email, kind, day):
    rows = conn.execute(
        "select id from coupons where kind = ? and enabled = 1",
        (kind,),
    ).fetchall()
    added = 0
    for row in rows:
        try:
            conn.execute(
                "insert into coupon_grants (email, coupon_id, day) values (?, ?, ?)",
                (email, row["id"], day),
            )
            added += 1
        except sqlite3.IntegrityError:
            pass
    return added


def utc_day(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone(timezone.utc).strftime("%Y-%m-%d")
