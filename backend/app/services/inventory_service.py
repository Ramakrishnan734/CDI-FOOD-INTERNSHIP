# backend/app/services/inventory_service.py
"""
Shared stock helpers. The stock_ledger is the only source of truth, so
balance and WAC are always derived from it and never stored separately.
"""

from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text

RATE_PLACES = Decimal("0.0001")


def lock_items(conn, item_ids):
    """
    Take a row lock on each item for the rest of the current transaction.
    Concurrent requests touching the same item then wait their turn, so
    balance and WAC are read and written consistently.
    Locks are taken in sorted id order so two requests can never deadlock.
    """
    for item_id in sorted(set(item_ids)):
        conn.execute(
            text("SELECT id FROM items WHERE id = :id FOR UPDATE"),
            {"id": item_id},
        )


def get_balance_and_wac(conn, item_id):
    """
    Returns (balance, wac) as Decimals.

    Stock value = SUM((qty_in - qty_out) * rate), balance = SUM(qty_in - qty_out),
    and WAC = value / balance. This is a true moving average only if every
    outflow row stores the rate it was valued at (the WAC at issue time).
    Every ledger row must therefore carry a rate; a missing rate would
    silently skew costing, so we refuse to compute instead.

    wac is None when balance <= 0 (no stock to value).
    """
    row = conn.execute(
        text("""
            SELECT
                COALESCE(SUM(qty_in - qty_out), 0)             AS balance,
                COALESCE(SUM((qty_in - qty_out) * rate), 0)    AS stock_value,
                COUNT(*) FILTER (WHERE rate IS NULL)           AS rows_missing_rate
            FROM stock_ledger
            WHERE item_id = :item_id
        """),
        {"item_id": item_id},
    ).one()

    if row.rows_missing_rate > 0:
        raise ValueError(
            f"Item {item_id} has {row.rows_missing_rate} ledger row(s) with no rate"
        )

    balance = Decimal(row.balance)
    if balance <= 0:
        return balance, None

    wac = (Decimal(row.stock_value) / balance).quantize(
        RATE_PLACES, rounding=ROUND_HALF_UP
    )
    return balance, wac
