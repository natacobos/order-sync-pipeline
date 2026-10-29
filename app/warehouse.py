"""A local stand-in for the BigQuery dataset, using SQLite (part of Python).

Like a BigQuery table, `orders` does not enforce unique keys: nothing stops two rows with the same order_id.
SQLite has no MERGE statement; `INSERT ... ON CONFLICT ... DO UPDATE` (with a unique index) or an UPDATE
followed by an INSERT in one transaction do the same job here.

To simulate BigQuery being briefly unavailable (HTTP 503), every 25th write raises WarehouseUnavailable.
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    order_id     TEXT NOT NULL,
    customer_id  TEXT,
    status       TEXT,
    amount_cents INTEGER,
    commit_ts    TEXT NOT NULL
);
"""


class WarehouseUnavailable(Exception):
    """BigQuery answered 503: the write did not happen and can be tried again."""


class Warehouse:
    def __init__(self, path="warehouse.db", fail_every=25):
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)
        self._fail_every = fail_every
        self._writes = 0

    def reset(self):
        self.db.executescript("DROP TABLE IF EXISTS orders;" + SCHEMA)

    def write(self, sql, params=()):
        """Run one write statement, committed on its own."""
        self._writes += 1
        if self._fail_every and self._writes % self._fail_every == 0:
            raise WarehouseUnavailable(f"503 Service Unavailable (write #{self._writes})")
        with self.db:
            return self.db.execute(sql, params)

    def query(self, sql, params=()):
        return self.db.execute(sql, params).fetchall()
