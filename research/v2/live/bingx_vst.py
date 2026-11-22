"""Minimal signed BingX perpetual client — VST (demo) host ONLY.

The base URL is hard-coded to the VST simulation host; this module cannot trade real funds.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request

VST = "https://open-api-vst.bingx.com"
PUBLIC = "https://open-api.bingx.com"


class BingXVST:
    def __init__(self, key: str | None = None, secret: str | None = None):
        self.key = key or os.environ["BINGX_API_KEY"]
        self.secret = secret or os.environ["BINGX_SECRET_KEY"]
        self.base = VST

    def _req(self, method: str, path: str, params: dict | None = None):
        p = {k: v for k, v in (params or {}).items() if v is not None}
        p["timestamp"] = int(time.time() * 1000)
        q = "&".join(f"{k}={p[k]}" for k in sorted(p))
        sig = hmac.new(self.secret.encode(), q.encode(), hashlib.sha256).hexdigest()
        url = f"{self.base}{path}?{urllib.parse.quote(q, safe='=&')}&signature={sig}"
        req = urllib.request.Request(url, method=method, headers={"X-BX-APIKEY": self.key})
        for i in range(3):
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.loads(r.read())
            except Exception as e:  # noqa: BLE001
                if method != "GET" or i == 2:      # never blindly retry writes
                    return {"code": -1, "msg": f"transport:{type(e).__name__}"}
                time.sleep(1 + i)

    # --- read ---
    def balance(self) -> dict:
        return (self._req("GET", "/openApi/swap/v2/user/balance").get("data") or {}).get("balance") or {}

    def positions(self) -> list[dict]:
        return self._req("GET", "/openApi/swap/v2/user/positions").get("data") or []

    def open_orders(self) -> list[dict]:
        return (self._req("GET", "/openApi/swap/v2/trade/openOrders").get("data") or {}).get("orders") or []

    def dual_mode(self) -> bool:
        d = self._req("GET", "/openApi/swap/v1/positionSide/dual").get("data") or {}
        return str(d.get("dualSidePosition")).lower() == "true"

    @staticmethod
    def contracts() -> dict[str, dict]:
        with urllib.request.urlopen(PUBLIC + "/openApi/swap/v2/quote/contracts", timeout=30) as r:
            d = json.loads(r.read())["data"]
        return {x["symbol"].replace("-", ""): x for x in d if x["symbol"].endswith("-USDT") and int(x.get("status", 1)) == 1}

    @staticmethod
    def prices() -> dict[str, float]:
        with urllib.request.urlopen(PUBLIC + "/openApi/swap/v2/quote/price", timeout=30) as r:
            d = json.loads(r.read())["data"]
        return {x["symbol"].replace("-", ""): float(x["price"]) for x in d if x["symbol"].endswith("-USDT")}

    # --- write (VST only) ---
    def set_leverage(self, sym: str, side: str, lev: int):
        return self._req("POST", "/openApi/swap/v2/trade/leverage", {"symbol": sym, "side": side, "leverage": lev})

    def market_order(self, sym: str, side: str, position_side: str, qty: float, client_id: str):
        return self._req("POST", "/openApi/swap/v2/trade/order", {
            "symbol": sym, "side": side, "positionSide": position_side, "type": "MARKET",
            "quantity": qty, "clientOrderID": client_id})

