-- =============================================================
-- CDI Food ERP — Database Schema
-- PostgreSQL 16
-- Convention: snake_case, singular table names where logical
-- Money: NUMERIC(15,4) — stores up to ₹99,999,999,999.9999
-- Qty:   NUMERIC(12,4) — handles kg, litres, pieces precisely
-- =============================================================

-- -------------------------
-- 1. USERS
-- -------------------------
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL
                  CHECK (role IN ('owner','admin','salesman','production','auditor')),
    is_active     BOOLEAN      NOT NULL DEFAULT true,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- -------------------------
-- 2. ITEMS
-- -------------------------
CREATE TABLE IF NOT EXISTS items (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(20)  UNIQUE NOT NULL,
    name        VARCHAR(100) NOT NULL,
    item_type   VARCHAR(10)  NOT NULL
                CHECK (item_type IN ('raw','packaging','finished')),
    unit        VARCHAR(10)  NOT NULL,
    hsn_code    VARCHAR(10),          -- required on GST invoices for finished goods
    selling_price NUMERIC(15,2),
    is_active   BOOLEAN      NOT NULL DEFAULT true,
    CONSTRAINT chk_item_selling_price_positive CHECK (
        selling_price IS NULL OR selling_price > 0
    ),
    CONSTRAINT chk_item_code_type_match CHECK (
        (code LIKE 'RM-%' AND item_type = 'raw')
        OR (code LIKE 'PK-%' AND item_type = 'packaging')
        OR (code LIKE 'FG-%' AND item_type = 'finished')
    )
);

-- -------------------------
-- 3. CUSTOMERS
-- -------------------------
CREATE TABLE IF NOT EXISTS customers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    contact     VARCHAR(20),
    state_code  VARCHAR(2)   NOT NULL,  -- 'TN', 'KA', etc. — drives CGST/SGST vs IGST
    gstin       VARCHAR(15),
    is_active   BOOLEAN      NOT NULL DEFAULT true
);

-- -------------------------
-- 4. SUPPLIERS
-- -------------------------
CREATE TABLE IF NOT EXISTS suppliers (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    contact     VARCHAR(20),
    is_active   BOOLEAN      NOT NULL DEFAULT true
);

-- -------------------------
-- 5. BOM HEADERS
-- -------------------------
CREATE TABLE IF NOT EXISTS bom_headers (
    id                SERIAL PRIMARY KEY,
    finished_item_id  INTEGER      NOT NULL REFERENCES items(id),
    batch_output_qty  NUMERIC(10,3) NOT NULL CHECK (batch_output_qty > 0),  -- expected packets per batch (e.g. 200)
    version           INTEGER      NOT NULL DEFAULT 1,
    is_active         BOOLEAN      NOT NULL DEFAULT true,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- -------------------------
-- 6. BOM LINES
-- -------------------------
CREATE TABLE IF NOT EXISTS bom_lines (
    id              SERIAL PRIMARY KEY,
    bom_id          INTEGER       NOT NULL REFERENCES bom_headers(id),
    item_id         INTEGER       NOT NULL REFERENCES items(id),
    qty_per_batch   NUMERIC(12,4) NOT NULL
);

-- -------------------------
-- 7. STOCK LEDGER  ← source of truth for all balances
-- -------------------------
CREATE TABLE IF NOT EXISTS stock_ledger (
    id              SERIAL PRIMARY KEY,
    item_id         INTEGER       NOT NULL REFERENCES items(id),
    movement_type   VARCHAR(30)   NOT NULL
                    CHECK (movement_type IN (
                        'opening',
                        'purchase',
                        'production_issue',
                        'production_output',
                        'sale_dispatch',
                        'adjustment'
                    )),
    qty_in          NUMERIC(12,4) NOT NULL DEFAULT 0,
    qty_out         NUMERIC(12,4) NOT NULL DEFAULT 0,
    rate            NUMERIC(15,4),   -- cost rate at time of movement (for WAC costing)
    ref_type        VARCHAR(30),     -- 'purchase_order' | 'production_run' | 'sales_order'
    ref_id          INTEGER,         -- FK-by-convention to the source document's id
    notes           TEXT,
    created_by      INTEGER REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index: balance queries always filter by item_id
CREATE INDEX IF NOT EXISTS idx_stock_ledger_item_id ON stock_ledger(item_id);

-- -------------------------
-- 8. PURCHASE ORDERS
-- -------------------------
CREATE TABLE IF NOT EXISTS purchase_orders (
    id            SERIAL PRIMARY KEY,
    supplier_id   INTEGER     REFERENCES suppliers(id),
    order_date    DATE        NOT NULL,
    status        VARCHAR(10) NOT NULL DEFAULT 'posted'
                  CHECK (status IN ('posted','cancelled')),
    created_by    INTEGER     REFERENCES users(id),
    client_request_id VARCHAR(100) UNIQUE,
    request_hash      VARCHAR(64),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- -------------------------
-- 9. PURCHASE LINES
-- -------------------------
CREATE TABLE IF NOT EXISTS purchase_lines (
    id          SERIAL PRIMARY KEY,
    po_id       INTEGER       NOT NULL REFERENCES purchase_orders(id),
    item_id     INTEGER       NOT NULL REFERENCES items(id),
    qty         NUMERIC(12,4) NOT NULL,
    unit_rate   NUMERIC(15,4) NOT NULL
);

-- -------------------------
-- 10. PRODUCTION RUNS
-- -------------------------
CREATE TABLE IF NOT EXISTS production_runs (
    id              SERIAL PRIMARY KEY,
    run_date        DATE          NOT NULL,
    bom_id          INTEGER       NOT NULL REFERENCES bom_headers(id),
    planned_output  NUMERIC(10,3) NOT NULL,  -- from BOM at time of posting
    actual_output   NUMERIC(10,3) NOT NULL DEFAULT 0,
    damaged_qty     NUMERIC(10,3) NOT NULL DEFAULT 0,
    cartons_used    NUMERIC(10,3) NOT NULL DEFAULT 0,
    status          VARCHAR(10)   NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','posted')),
    labour_cost     NUMERIC(15,2) NOT NULL DEFAULT 0,
    overhead_cost   NUMERIC(15,2) NOT NULL DEFAULT 0,
    created_by      INTEGER       REFERENCES users(id),
    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- -------------------------
-- 11. PRODUCTION LINES
-- -------------------------
-- Snapshotted at posting time — not a live join to bom_lines.
-- This means: if the BOM changes later, past runs still show original consumption.
CREATE TABLE IF NOT EXISTS production_lines (
    id           SERIAL PRIMARY KEY,
    run_id       INTEGER       NOT NULL REFERENCES production_runs(id),
    item_id      INTEGER       NOT NULL REFERENCES items(id),
    planned_qty  NUMERIC(12,4) NOT NULL,  -- from BOM at time of posting
    actual_qty   NUMERIC(12,4) NOT NULL   -- what was actually consumed
);

-- -------------------------
-- 12. SALES ORDERS
-- -------------------------
CREATE TABLE IF NOT EXISTS sales_orders (
    id              SERIAL PRIMARY KEY,
    order_number    VARCHAR(20)   UNIQUE NOT NULL,
    customer_id     INTEGER       NOT NULL REFERENCES customers(id),
    salesman_id     INTEGER       NOT NULL REFERENCES users(id),
    order_date      DATE          NOT NULL,
    status          VARCHAR(15)   NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','approved','dispatched','cancelled')),

    -- Approval
    approved_by     INTEGER       REFERENCES users(id),
    approved_at     TIMESTAMPTZ,

    -- GST invoice fields (populated at approval/dispatch)
    invoice_number  VARCHAR(20)   UNIQUE,
    invoice_date    DATE,
    taxable_value   NUMERIC(15,2),
    cgst_amount     NUMERIC(15,2),
    sgst_amount     NUMERIC(15,2),
    igst_amount     NUMERIC(15,2),
    invoice_total   NUMERIC(15,2),

    -- Outstanding tracking
    amount_paid     NUMERIC(15,2) NOT NULL DEFAULT 0,
    outstanding     NUMERIC(15,2),   -- updated by trigger or service layer

    created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- -------------------------
-- 13. SALES ORDER LINES
-- -------------------------
CREATE TABLE IF NOT EXISTS sales_order_lines (
    id          SERIAL PRIMARY KEY,
    order_id    INTEGER       NOT NULL REFERENCES sales_orders(id),
    item_id     INTEGER       NOT NULL REFERENCES items(id),
    qty         NUMERIC(10,3) NOT NULL,
    unit_price  NUMERIC(15,2) NOT NULL,
    line_total  NUMERIC(15,2) NOT NULL
);

-- -------------------------
-- 14. PAYMENTS
-- -------------------------
CREATE TABLE IF NOT EXISTS payments (
    id              SERIAL PRIMARY KEY,
    sales_order_id  INTEGER       NOT NULL REFERENCES sales_orders(id),
    payment_date    DATE          NOT NULL,
    amount          NUMERIC(15,2) NOT NULL,
    reference       VARCHAR(100),   -- cheque number, UPI ref, etc.
    recorded_by     INTEGER        REFERENCES users(id),
    created_at      TIMESTAMPTZ    NOT NULL DEFAULT now()
);
