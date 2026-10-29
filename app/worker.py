"""The order-sync worker: receives order changes from Pub/Sub and loads them into the `orders` table.

In production each instance of this service runs on Cloud Run and Pub/Sub pushes messages to it.
"""
import logging

from app.changes import parse
from app.warehouse import WarehouseUnavailable

log = logging.getLogger("order_sync")


class Worker:
    def __init__(self, warehouse, name="instance-1"):
        self.warehouse = warehouse
        self.name = name
        self._seen = set()  # message ids this instance already handled

    def handle(self, message):
        # Acknowledge right away: the subscription's ack deadline is 10 seconds and loads can be slow.
        message.ack()
        if message.message_id in self._seen:  # Pub/Sub can deliver the same message twice
            return
        self._seen.add(message.message_id)

        change = parse(message.data)
        try:
            self.load(change)
        except WarehouseUnavailable as error:
            log.warning("%s: BigQuery unavailable, skipping %s (%s)", self.name, change.order_id, error)

    def load(self, change):
        d = change.data
        if change.mod_type == "INSERT":
            self.warehouse.write(
                "INSERT INTO orders (order_id, customer_id, status, amount_cents, commit_ts) VALUES (?, ?, ?, ?, ?)",
                (change.order_id, d.get("customer_id"), d.get("status"), d.get("amount_cents"), change.commit_ts))
        elif change.mod_type == "UPDATE":
            self.warehouse.write(
                "UPDATE orders SET customer_id = ?, status = ?, amount_cents = ?, commit_ts = ? WHERE order_id = ?",
                (d.get("customer_id"), d.get("status"), d.get("amount_cents"), change.commit_ts, change.order_id))
        # DELETE: nothing to load.
