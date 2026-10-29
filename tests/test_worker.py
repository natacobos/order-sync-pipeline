import json
import unittest

from app.warehouse import Warehouse
from app.worker import Worker


class FakeMessage:
    def __init__(self, message_id, change):
        self.message_id = message_id
        self.data = json.dumps(change).encode()
        self.acked = self.nacked = False

    def ack(self):
        self.acked = True

    def nack(self):
        self.nacked = True


def change(order_id, mod_type, commit_ts, status=None, amount_cents=2450):
    data = {} if mod_type == "DELETE" else {"customer_id": "C-001", "status": status, "amount_cents": amount_cents}
    return {"order_id": order_id, "mod_type": mod_type, "commit_ts": commit_ts, "data": data}


class WorkerTest(unittest.TestCase):
    def setUp(self):
        self.warehouse = Warehouse(":memory:", fail_every=0)
        self.worker = Worker(self.warehouse)

    def deliver(self, message_id, body):
        message = FakeMessage(message_id, body)
        self.worker.handle(message)
        return message

    def orders(self):
        return self.warehouse.query("SELECT order_id, status, amount_cents FROM orders ORDER BY order_id")

    def test_insert_creates_the_order(self):
        message = self.deliver("m-1", change("O-1", "INSERT", "2026-10-27T08:00:00.000000Z", "CREATED"))
        self.assertTrue(message.acked)
        self.assertEqual(self.orders(), [("O-1", "CREATED", 2450)])

    def test_updates_change_the_status(self):
        self.deliver("m-1", change("O-1", "INSERT", "2026-10-27T08:00:00.000000Z", "CREATED"))
        self.deliver("m-2", change("O-1", "UPDATE", "2026-10-27T08:01:00.000000Z", "PAID"))
        self.deliver("m-3", change("O-1", "UPDATE", "2026-10-27T08:05:00.000000Z", "SHIPPED"))
        self.assertEqual(self.orders(), [("O-1", "SHIPPED", 2450)])

    def test_orders_are_kept_apart(self):
        self.deliver("m-1", change("O-1", "INSERT", "2026-10-27T08:00:00.000000Z", "CREATED"))
        self.deliver("m-2", change("O-2", "INSERT", "2026-10-27T08:00:01.000000Z", "CREATED", 999))
        self.deliver("m-3", change("O-2", "UPDATE", "2026-10-27T08:02:00.000000Z", "PAID", 999))
        self.assertEqual(self.orders(), [("O-1", "CREATED", 2450), ("O-2", "PAID", 999)])


if __name__ == "__main__":
    unittest.main()
