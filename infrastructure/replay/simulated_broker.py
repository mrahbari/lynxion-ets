"""Network-incapable broker boundary for later canonical replay composition.

This adapter only records accepted pre-broker orders. It does not make Risk
decisions, assume fills, fabricate order-book depth or calculate PnL.
"""

from infrastructure.adapters.broker_data_adapters import BrokerAdapter


class SimulatedBrokerAdapter(BrokerAdapter):
    def __init__(self):
        self.orders = {}
        self._next_id = 1

    def place_order(self, order):
        order_id = f"REPLAY-{self._next_id:08d}"
        self._next_id += 1
        self.orders[order_id] = {"order": order, "status": "ACCEPTED"}
        return order_id

    def cancel_order(self, order_id, symbol=None):
        record = self.orders.get(order_id)
        if record is None or record["status"] != "ACCEPTED":
            return False
        record["status"] = "CANCELED"
        return True

    def get_order_status(self, order_id, symbol=None):
        record = self.orders.get(order_id)
        return record["status"] if record is not None else "NOT_FOUND"

    def get_open_orders(self, symbol):
        key = getattr(symbol, "value", symbol)
        return [record["order"] for record in self.orders.values()
                if record["status"] == "ACCEPTED"
                and getattr(getattr(record["order"], "symbol", None), "value",
                            getattr(record["order"], "symbol", None)) == key]

    def get_position(self, symbol):
        # An accepted order is not proof of a fill or an active position.
        return None

    def get_all_positions(self):
        return []
