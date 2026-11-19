# CDI Food ERP — Development Log

## Day 1 — November 19, 2026

### Completed
- Verified project environment, virtual environment, dependencies, and PostgreSQL connection.
- Reviewed and finalized the 14-table database schema.
- Created `backend/app/models/schema.sql` containing all 14 tables.
- Created `backend/seed/seed.py` with benchmark master data and opening stock.
- Executed the seed script and verified all 6 opening stock balances.
- Implemented FastAPI application.
- Implemented JWT-based authentication and login.
- Implemented role-based access control (RBAC).
- Implemented inventory purchase and stock balance APIs.
- Added purchase validations.
- Restricted purchase access to authorized roles.
- Created a shared inventory service for stock locking and balance/WAC retrieval.
- Tested invalid purchase requests and verified that failed requests do not modify the database.

### Files Created / Updated
- `backend/app/models/schema.sql`
- `backend/seed/seed.py`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/routers/auth.py`
- `backend/app/routers/inventory.py`
- `backend/app/services/inventory_service.py`

### Verified Opening Stock

| Item | Balance | Unit |
|---|---:|---|
| RM-FLOUR | 100.000 | kg |
| RM-OIL | 30.000 | litre |
| RM-SPICE | 5.000 | kg |
| PK-POUCH | 500.000 | piece |
| PK-CARTON | 30.000 | piece |
| FG-MRK200 | 50.000 | packet |

### Next — Day 2 (November 20, 2026)
- Implement duplicate purchase request protection (idempotency).
- Execute benchmark purchase of 60 kg flour at ₹45/kg.
- Verify updated stock balance and weighted average cost (WAC).
- Begin production workflow implementation:
  - Production run creation.
  - BOM requirement calculation.
  - Raw material consumption recording.
  - Finished goods output recording.
  - Stock ledger updates.
  - Yield and consumption variance calculation.


  ### Additional Verification
- Verified FastAPI Swagger documentation at `/docs`.
- Verified authentication and inventory endpoints are registered.
- Verified Python dependencies using `pip check` — no broken requirements found.
- Reviewed database connection management and transaction handling.
- Reviewed purchase API validation, stock locking, and WAC calculation logic.
- Reviewed the existing purchase order database schema.

### Next Day 2: 
Implement duplicate purchase request protection (idempotency), execute the benchmark purchase, verify weighted average cost (WAC), and begin the production workflow.

## Day 2 — November 20, 2026

### Completed
- Added `client_request_id` and `request_hash` columns to `purchase_orders` via ALTER TABLE.
- Created partial unique index `uq_purchase_orders_client_request_id` on `purchase_orders`.
- Implemented idempotency in purchase API: same ID + same payload returns original result; same ID + different payload returns 409.
- Fixed `get_stock_balance` returning `float` — corrected to `str(Decimal(...))`.
- Tested idempotency: new purchase (201), exact replay (200, same PO id), different payload (409).
- Verified database integrity: exactly one purchase order and one ledger row created across three test attempts.
- Cleaned up test purchase row.
- Executed benchmark purchase: 60 kg Rice Flour at ₹45/kg.
- Verified benchmark result: balance = 160 kg, WAC = ₹43.1250/kg.

### Files Created / Updated
- `backend/app/models/schema.sql` — documented new columns (ALTER TABLE applied directly)
- `backend/app/routers/inventory.py` — idempotency logic, float fix

### Verified Benchmark

| Item     | Opening | Purchased | Balance | WAC      |
|----------|--------:|----------:|--------:|---------:|
| RM-FLOUR | 100 kg  | 60 kg     | 160 kg  | ₹43.1250 |

### Next — Day 3
- Begin production workflow:
  - Production run creation API.
  - BOM requirement calculation.
  - Raw material consumption recording.
  - Finished goods output recording.
  - Stock ledger updates for production.
  - Yield and consumption variance calculation.