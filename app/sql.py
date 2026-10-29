"""Run a SQL query against the local `orders` table and print the rows.

    python -m app.sql "SELECT * FROM orders WHERE order_id = 'O-1012'"
"""
import sys

from app.warehouse import Warehouse


def main():
    warehouse = Warehouse()
    for row in warehouse.query(sys.argv[1]):
        print(" | ".join("" if v is None else str(v) for v in row))


if __name__ == "__main__":
    main()
