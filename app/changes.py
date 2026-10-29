"""One change to one order, as published by the Spanner change stream.

A message body looks like this:

    {"order_id": "O-1007", "mod_type": "UPDATE", "commit_ts": "2026-10-27T14:05:12.000120Z",
     "data": {"customer_id": "C-031", "status": "PAID", "amount_cents": 4599}}

mod_type is INSERT (order created), UPDATE (order changed) or DELETE (order removed; data is empty).
commit_ts is when the change was committed in Spanner. Timestamps have the same format, so comparing them
as strings gives the same result as comparing them as times.
"""
import json
from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrderChange:
    order_id: str
    mod_type: str
    commit_ts: str
    data: dict = field(default_factory=dict)


def parse(body: bytes) -> OrderChange:
    raw = json.loads(body)
    return OrderChange(order_id=raw["order_id"], mod_type=raw["mod_type"], commit_ts=raw["commit_ts"],
                       data=raw.get("data") or {})
