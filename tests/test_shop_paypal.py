import json
from io import BytesIO
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from shop.app import create_app
from shop.pay import PayPalCheckout, PayPalError


BUYER = {
    "email": "pp@example.com",
    "name": "P Buyer",
    "address": "1 Road",
    "city": "Austin",
    "region": "TX",
    "postal": "73301",
    "phone": "5551212",
    "ship_country": "US",
    "pay_method": "paypal",
    "coupon_id": "",
}


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_paypal_checkout_redirect_and_return_marks_paid(monkeypatch):
    monkeypatch.setenv("PAYPAL_CLIENT_ID", "client")
    monkeypatch.setenv("PAYPAL_CLIENT_SECRET", "secret")
    monkeypatch.setenv("PAYPAL_ENV", "sandbox")
    monkeypatch.delenv("LIANLIAN_MERCHANT_ID", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    calls = []

    def fake_urlopen(request, timeout=20):
        url = request.full_url
        method = request.get_method()
        calls.append((method, url))
        if url.endswith("/v1/oauth2/token"):
            return _Resp({"access_token": "tok", "expires_in": 3600})
        if method == "POST" and url.endswith("/v2/checkout/orders"):
            return _Resp({
                "id": "ORDER-PP-1",
                "status": "CREATED",
                "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-PP-1"}],
            })
        if method == "GET" and url.endswith("/v2/checkout/orders/ORDER-PP-1"):
            return _Resp({
                "id": "ORDER-PP-1",
                "status": "APPROVED",
                "purchase_units": [{
                    "reference_id": "1",
                    "custom_id": "1",
                    "amount": {"currency_code": "USD", "value": "0.00"},
                }],
            })
        if method == "POST" and url.endswith("/v2/checkout/orders/ORDER-PP-1/capture"):
            # amount filled after we know due; read stored session later — use flexible match in settle
            body = request.data.decode() if request.data else "{}"
            return _Resp({
                "id": "ORDER-PP-1",
                "status": "COMPLETED",
                "purchase_units": [{
                    "reference_id": calls_order_id[0],
                    "custom_id": calls_order_id[0],
                    "amount": {"currency_code": "USD", "value": calls_amount[0]},
                    "payments": {"captures": [{
                        "id": "CAP-1",
                        "status": "COMPLETED",
                        "amount": {"currency_code": "USD", "value": calls_amount[0]},
                    }]},
                }],
            })
        raise AssertionError(f"unexpected {method} {url}")

    calls_order_id = ["0"]
    calls_amount = ["0.00"]
    monkeypatch.setattr("shop.pay.urlopen", fake_urlopen)

    client = TestClient(create_app(units_per_usd=150, db_path=":memory:"))
    assert isinstance(client.app.state.stripe, PayPalCheckout)

    client.post("/cart/add", data={"sku": "note-holder", "qty": "1", "country": "US"})
    payload = dict(BUYER)
    payload["submit_id"] = "pp-1"
    # first create may happen on checkout redirect — patch amount after place by inspecting DB in fake capture
    def fake_urlopen2(request, timeout=20):
        url = request.full_url
        method = request.get_method()
        calls.append((method, url))
        if url.endswith("/v1/oauth2/token"):
            return _Resp({"access_token": "tok", "expires_in": 3600})
        if method == "POST" and url.endswith("/v2/checkout/orders"):
            order = client.app.state.db.execute("select id, due_local from orders order by id desc").fetchone()
            calls_order_id[0] = str(order["id"])
            cents = int(order["due_local"])
            calls_amount[0] = f"{cents/100:.2f}"
            return _Resp({
                "id": "ORDER-PP-1",
                "status": "CREATED",
                "links": [{"rel": "approve", "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-PP-1"}],
            })
        if method == "GET" and "/v2/checkout/orders/ORDER-PP-1" in url and method == "GET":
            return _Resp({"id": "ORDER-PP-1", "status": "APPROVED", "purchase_units": [{
                "reference_id": calls_order_id[0],
                "custom_id": calls_order_id[0],
                "amount": {"currency_code": "USD", "value": calls_amount[0]},
            }]})
        if method == "POST" and url.endswith("/capture"):
            return _Resp({
                "id": "ORDER-PP-1",
                "status": "COMPLETED",
                "purchase_units": [{
                    "reference_id": calls_order_id[0],
                    "custom_id": calls_order_id[0],
                    "amount": {"currency_code": "USD", "value": calls_amount[0]},
                    "payments": {"captures": [{
                        "id": "CAP-1",
                        "status": "COMPLETED",
                        "amount": {"currency_code": "USD", "value": calls_amount[0]},
                    }]},
                }],
            })
        raise AssertionError(f"unexpected {method} {url}")

    monkeypatch.setattr("shop.pay.urlopen", fake_urlopen2)
    resp = client.post("/checkout?country=US", data=payload, follow_redirects=False)
    assert resp.status_code == 303
    assert "sandbox.paypal.com" in resp.headers["location"]
    order = client.app.state.db.execute("select * from orders order by id desc").fetchone()
    assert order["pay_method"] == "paypal"
    assert order["status"] == "pending"

    back = client.get(f"/orders/{order['id']}/paypal?token=ORDER-PP-1", follow_redirects=False)
    assert back.status_code in {302, 303}
    paid = client.app.state.db.execute("select status from orders where id = ?", (order["id"],)).fetchone()["status"]
    assert paid == "paid"
    session = client.app.state.stripe.find(order["id"])
    assert session["session_id"] == "ORDER-PP-1"
    assert session["payment_intent"] == "CAP-1"
