# Code Challenge — Order sync pipeline (30 minutes)

## The situation

An online store keeps its orders in **Spanner**, the database behind the app. Every time an order is created, changed or deleted, a Spanner change stream publishes that change to **Pub/Sub** (a message queue). This Python service, running on **Cloud Run** as several instances, receives each message and loads the change into the **BigQuery** table `orders`, where the analytics team builds its revenue reports.

The pipeline went live last week (ticket **DATA-212** below). The tests pass, but after loading 2026-10-27 the analytics team sent these reports:

1. "Orders O-1013 and O-1026 appear twice in the `orders` table, so revenue is counted twice."
2. "Order O-1040 shows CREATED in BigQuery, but it was paid hours ago. O-1025, O-1033, O-1035 and O-1060 show PAID, but they were shipped."
3. "Orders O-1028 and O-1055 exist in Spanner but never reached BigQuery."
4. "QA's test orders O-1009, O-1023, O-1038 and O-1051 were deleted in Spanner, but they are still in BigQuery and count as revenue."

Your job is to find the cause of each report in the code, fix it, and then add a check.

You may use your usual tools, including an AI assistant. Please share your screen and explain what you ask it and how you check what it gives you.

## Ticket DATA-212 — Keep BigQuery's `orders` table in sync with Spanner

Pub/Sub delivers each message **at least once** (sometimes twice, even after it was acknowledged) and **in no guaranteed order**. A message that is not acknowledged is delivered again later. The service runs as **several instances** and can restart at any time.

**Acceptance criteria**

1. Each order appears in `orders` **exactly once**.
2. Each row shows the order's **latest** change (the newest `commit_ts`), whatever order the messages arrive in.
3. **No change is lost**, even when BigQuery is briefly unavailable.
4. Orders **deleted** in Spanner are not in `orders`.
5. Every change is loaded within a few minutes (no batch jobs).

## Steps

Each step has a time. When the time is up, move on to the next step, finished or not.

1. **Investigate (10 minutes).** For each report, find the cause in the code and the acceptance criterion it breaks. Reproduce it if you can. Tell us what you would fix first. Do not change code yet.
2. **Fix (12 minutes).** Fix the causes you found, starting with the most important. Show how you verified each fix.
3. **Add a check (8 minutes).** A new acceptance criterion is added to the ticket:

   > 6. A command `python -m app.reconcile` compares `orders` with Spanner's export of the same day (`data/spanner_orders_2026-10-27.jsonl`). It lists the orders that are missing, extra, duplicated or outdated in `orders`, and exits with code 1 if there is any difference.

   Implement it. If time is short, explain how you would finish it.

## Rules

- Keep the existing code; do not rewrite it from scratch.
- Check the code against the ticket; do not assume it is correct because the tests pass.
- Do not change `app/pubsub.py`: it stands in for Pub/Sub, which you cannot change in production either.
- If you use an AI assistant, review every change it proposes before accepting it, and be ready to explain it.
- Do not add new libraries.

## Running the project

**With Docker (recommended).** You only need Docker Desktop. Clone the repository and run, from its folder:

```bash
docker compose run --rm app python -m app.main             # replay 2026-10-27 through the pipeline
docker compose run --rm app python -m app.sql "SELECT * FROM orders WHERE order_id = 'O-1013'"
docker compose run --rm app python -m unittest -v          # run the tests
```

The first run downloads about 50 MB (the `python:3.12.7-slim` image) and takes under a minute. Edit the files in your usual editor; each command uses your latest code.

**Without Docker.** With Python 3.12 or newer, run the same commands without `docker compose run --rm app`, for example `python -m app.main`. Nothing needs to be installed.

## What is in the project

| File | What it is |
|---|---|
| `app/worker.py` | The service: receives one message and loads the change into `orders`. |
| `app/changes.py` | The format of a change message. |
| `app/warehouse.py` | A local stand-in for BigQuery, using SQLite. It can be briefly unavailable, like the real one. |
| `app/pubsub.py` | A local stand-in for the Pub/Sub subscription (do not change it). |
| `app/main.py` | Replays 2026-10-27: 163 changes through 3 instances of the service. |
| `app/sql.py` | Runs a SQL query against the local `orders` table. |
| `data/changes_2026-10-27.jsonl` | The day's change messages, in the order Spanner committed them. |
| `data/spanner_orders_2026-10-27.jsonl` | Spanner's export of every order at the end of the day. |
| `tests/` | The existing tests. |

The local table lives in `warehouse.db`; `python -m app.main` empties it before each replay.
