"""Replay one day of order changes through the pipeline, the way production ran it on 2026-10-27.

    python -m app.main

It empties the local `orders` table, starts 3 worker instances, delivers every message of
data/changes_2026-10-27.jsonl through the local Pub/Sub subscription and prints a summary.
"""
import logging
import os

from app.pubsub import LocalSubscription
from app.warehouse import Warehouse
from app.worker import Worker

HERE = os.path.dirname(os.path.abspath(__file__))
CHANGES = os.path.join(HERE, "..", "data", "changes_2026-10-27.jsonl")
INSTANCES = 3


def run(changes=CHANGES, db="warehouse.db"):
    warehouse = Warehouse(db)
    warehouse.reset()
    workers = [Worker(warehouse, f"instance-{i + 1}") for i in range(INSTANCES)]
    subscription = LocalSubscription(changes)
    for n, message in enumerate(subscription.deliveries()):
        workers[n % INSTANCES].handle(message)  # Cloud Run spreads requests across instances
    return warehouse, subscription


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
    warehouse, subscription = run()
    rows, orders = warehouse.query("SELECT COUNT(*), COUNT(DISTINCT order_id) FROM orders")[0]
    print(f"Pub/Sub: {subscription.stats}")
    print(f"orders table: {rows} rows, {orders} distinct orders")


if __name__ == "__main__":
    main()
