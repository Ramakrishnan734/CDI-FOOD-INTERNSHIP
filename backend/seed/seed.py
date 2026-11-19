"""
CDI Food ERP — Seed Script
Loads benchmark master data and opening stock from Section 5.
Run from backend/ directory with the venv active:
    python -m seed.seed
"""

import os
import sys
from decimal import Decimal
from datetime import date

# Add backend/ to path so we can import app.database
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine


def run_schema():
    """Create all tables by running schema.sql."""
    schema_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'app', 'models', 'schema.sql'
    )
    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    with engine.begin() as conn:
        conn.execute(text(schema_sql))
    print("✓ Schema created")


def seed_users(conn):
    conn.execute(text("""
        INSERT INTO users (name, email, password_hash, role) VALUES
        ('Admin User',      'admin@cdi.com',      'hashed_admin123',      'admin'),
        ('Salesman A',      'salesman_a@cdi.com', 'hashed_sales123',      'salesman'),
        ('Salesman B',      'salesman_b@cdi.com', 'hashed_sales123',      'salesman'),
        ('Production Sup',  'prod@cdi.com',       'hashed_prod123',       'production'),
        ('Auditor',         'audit@cdi.com',       'hashed_audit123',      'auditor'),
        ('Owner',           'owner@cdi.com',       'hashed_owner123',      'owner')
        ON CONFLICT (email) DO NOTHING
    """))
    print("✓ Users seeded")


def seed_items(conn):
    conn.execute(text("""
        INSERT INTO items (code, name, item_type, unit, hsn_code) VALUES
        -- Raw materials
        ('RM-FLOUR',    'Rice Flour',           'raw',       'kg',     NULL),
        ('RM-OIL',      'Cooking Oil',          'raw',       'litre',  NULL),
        ('RM-SPICE',    'Salt and Spice Mix',   'raw',       'kg',     NULL),
        -- Packaging
        ('PK-POUCH',    '200g Pouch',           'packaging', 'piece',  NULL),
        ('PK-CARTON',   'Carton (20 packets)',  'packaging', 'piece',  NULL),
        -- Finished goods
        ('FG-MRK200',   'Murukku 200g',         'finished',  'packet', '2106')
        ON CONFLICT (code) DO NOTHING
    """))
    print("✓ Items seeded")


def seed_customers(conn):
    conn.execute(text("""
        INSERT INTO customers (name, contact, state_code, gstin) VALUES
        ('Retailer A',    '9000000001', 'TN', '33AAAAA0000A1Z5'),
        ('Distributor B', '9000000002', 'KA', '29BBBBB0000B1Z3')
        ON CONFLICT DO NOTHING
    """))
    print("✓ Customers seeded")


def seed_suppliers(conn):
    conn.execute(text("""
        INSERT INTO suppliers (name, contact) VALUES
        ('General Supplier', '9000000099')
        ON CONFLICT DO NOTHING
    """))
    print("✓ Suppliers seeded")


def seed_bom(conn):
    # Get the finished good item id
    result = conn.execute(text(
        "SELECT id FROM items WHERE code = 'FG-MRK200'"
    ))
    fg_id = result.scalar_one()

    # Insert BOM header
    result = conn.execute(text("""
        INSERT INTO bom_headers (finished_item_id, batch_output_qty, version, is_active)
        VALUES (:fg_id, 200, 1, true)
        ON CONFLICT DO NOTHING
        RETURNING id
    """), {"fg_id": fg_id})

    row = result.fetchone()
    if row is None:
        # Already exists
        result = conn.execute(text(
            "SELECT id FROM bom_headers WHERE finished_item_id = :fg_id AND version = 1",
        ), {"fg_id": fg_id})
        bom_id = result.scalar_one()
    else:
        bom_id = row[0]

    # Get item IDs
    items = conn.execute(text(
        "SELECT code, id FROM items WHERE code IN "
        "('RM-FLOUR','RM-OIL','RM-SPICE','PK-POUCH','PK-CARTON')"
    )).fetchall()
    item_map = {row[0]: row[1] for row in items}

    # BOM lines: qty per batch of 200 packets
    bom_lines = [
        (item_map['RM-FLOUR'],   Decimal('40')),
        (item_map['RM-OIL'],     Decimal('10')),
        (item_map['RM-SPICE'],   Decimal('1.2')),
        (item_map['PK-POUCH'],   Decimal('200')),
        (item_map['PK-CARTON'],  Decimal('10')),
    ]

    for item_id, qty in bom_lines:
        conn.execute(text("""
            INSERT INTO bom_lines (bom_id, item_id, qty_per_batch)
            VALUES (:bom_id, :item_id, :qty)
        """), {"bom_id": bom_id, "item_id": item_id, "qty": qty})

    print(f"✓ BOM seeded (bom_id={bom_id})")


def seed_opening_stock(conn):
    """
    Opening stock from benchmark Section 5.
    Rates:
      Flour:  ₹42/kg  (opening rate before the ₹45 purchase)
      Oil:    ₹140/L
      Spice:  ₹200/kg
      Pouch:  ₹2.50/piece
      Carton: ₹15/piece
      Finished Murukku: cost unknown at open, rate=0 (no cost assigned to opening FG stock)
    """
    items = conn.execute(text(
        "SELECT code, id FROM items"
    )).fetchall()
    item_map = {row[0]: row[1] for row in items}

    opening = [
        # (item_code, qty_in, rate)
        ('RM-FLOUR',  Decimal('100'), Decimal('42')),
        ('RM-OIL',    Decimal('30'),  Decimal('140')),
        ('RM-SPICE',  Decimal('5'),   Decimal('200')),
        ('PK-POUCH',  Decimal('500'), Decimal('2.50')),
        ('PK-CARTON', Decimal('30'),  Decimal('15')),
        ('FG-MRK200', Decimal('50'),  Decimal('0')),
    ]

    for code, qty, rate in opening:
        conn.execute(text("""
            INSERT INTO stock_ledger
                (item_id, movement_type, qty_in, qty_out, rate, ref_type, notes, created_at)
            VALUES
                (:item_id, 'opening', :qty, 0, :rate, 'opening', 'Opening stock', :today)
        """), {
            "item_id": item_map[code],
            "qty": qty,
            "rate": rate,
            "today": date.today()
        })

    print("✓ Opening stock seeded")


def verify_balances(conn):
    """Quick check: print closing balances after seed."""
    print("\n--- Stock balances after seed ---")
    rows = conn.execute(text("""
        SELECT i.code, i.name, i.unit,
               SUM(sl.qty_in) - SUM(sl.qty_out) AS balance
        FROM stock_ledger sl
        JOIN items i ON i.id = sl.item_id
        GROUP BY i.id, i.code, i.name, i.unit
        ORDER BY i.item_type, i.code
    """)).fetchall()

    for row in rows:
        print(f"  {row[0]:12s}  {row[1]:25s}  {float(row[3]):>10.3f} {row[2]}")


def main():
    print("=== CDI Food ERP — Seeding database ===\n")

    run_schema()

    with engine.begin() as conn:
        seed_users(conn)
        seed_items(conn)
        seed_customers(conn)
        seed_suppliers(conn)
        seed_bom(conn)
        seed_opening_stock(conn)
        verify_balances(conn)

    print("\n=== Seed complete ===")


if __name__ == "__main__":
    main()