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

## Day 3 — November 20, 2026

### Completed
- Implemented production workflow: draft and post two-phase design.
- Created `backend/app/routers/production.py` with two endpoints:
  - `POST /production/start` — creates draft run, calculates planned quantities from BOM.
  - `POST /production/{run_id}/post` — posts run, writes stock movements, calculates variances.
- Registered production router in `main.py`.
- Tested full production run: 200 planned packets, 196 actual output.
- Verified WAC-based material costing at issue time.
- Variance detection working: RM-SPICE flagged at 4.17% (threshold 3%).
- Verified all stock balances after production.

### Files Created / Updated
- `backend/app/routers/production.py` — new file
- `backend/app/main.py` — production router registered

### Verified Stock Balances After Production

| Item      | Balance  | Unit   |
|-----------|--------:|--------|
| RM-FLOUR  | 118.800 | kg     |
| RM-OIL   |  20.000 | litre  |
| RM-SPICE |   3.750 | kg     |
| PK-POUCH | 300.000 | piece  |
| PK-CARTON|  20.000 | piece  |
| FG-MRK200| 246.000 | packet |

### Verified Production Costing

| | Amount |
|---|---:|
| Total material cost | ₹4,076.75 |
| Labour cost | ₹500.00 |
| Overhead cost | ₹200.00 |
| Total cost | ₹4,776.75 |
| Cost per packet | ₹24.3712 |

### Completed — Item Classification Validation

- Added DB constraint `chk_item_code_type_match` to live database via ALTER TABLE.
- Updated `backend/app/models/schema.sql` — constraint added inside items table definition.
- Added `validate_item_code_type()` function in `backend/app/routers/inventory.py`.
- Added `POST /inventory/items` endpoint with API-layer prefix/type validation.
- Added `GET /inventory/items` endpoint.

### Validation rule enforced (two layers)

| Code prefix | Required item_type |
|-------------|-------------------|
| RM-         | raw               |
| PK-         | packaging         |
| FG-         | finished          |

### Test results

| Test | Result |
|------|--------|
| POST RM-TEST with item_type=finished | ✅ Rejected (422) at API layer |
| POST RM-SALT with item_type=raw | ✅ Accepted (201) |
| Direct psql INSERT with wrong type | ✅ Blocked by DB constraint |
| GET /inventory/items — all 6 seed items | ✅ All present and correct |

### Files modified
- `backend/app/models/schema.sql` — constraint added to items table
- `backend/app/routers/inventory.py` — validate_item_code_type(),


### Next — Day 4
- Sales order API (salesman creates order).
- Admin approval and GST invoice generation.
- Dispatch and finished goods stock deduction.

## Day 4 — November 20, 2026

### Completed
- Implemented sales order creation API (`POST /sales/order`).
- Salesman and admin roles can create orders.
- Customer validation — checks customer exists and is active.
- Item validation — only finished goods can be sold.
- Order number auto-generated in format `ORD-YYYYMMDD-NNNN`.
- Order stored with status `pending`. No stock movement at creation.
- Tested Retailer A order: 150 packets × ₹50 = ₹7,500 taxable value.
- Verified database: order and line stored correctly.
- Verified stock balance unchanged at 246 packets after order creation.

### Files Created / Updated
- `backend/app/routers/sales.py` — new file
- `backend/app/main.py` — sales router registered

### Verified Order Creation

| Field | Value |
|---|---|
| Order number | ORD-20261120-0001 |
| Customer | Retailer A (TN) |
| Status | pending |
| Taxable value | ₹7,500.00 |
| FG-MRK200 balance | 246.000 (unchanged) |

### Next — Phase 2
- Admin approval endpoint (`POST /sales/{order_id}/approve`).
- Stock availability check at approval time.
- GST calculation: TN→TN = CGST 2.5% + SGST 2.5%, TN→other = IGST 5%.
- Invoice number generation in format `INV-FY2627-NNNN`.
- Invoice fields populated on the sales_orders row.


## Day 4 continued — November 20, 2026

### Completed
- Implemented admin approval endpoint (`POST /sales/{order_id}/approve`).
- Stock availability check at approval time.
- GST calculation: TN→TN = CGST 2.5% + SGST 2.5%, TN→other = IGST 5%.
- Invoice number generated in format `INV-FY2627-NNNN`.
- All invoice fields written to `sales_orders` row at approval.
- Double-approval blocked with HTTP 409.

### Verified Benchmark — Retailer A Approval

| Field | Value |
|---|---|
| Invoice number | INV-FY2627-0001 |
| Taxable value | ₹7,500.00 |
| CGST 2.5% | ₹187.50 |
| SGST 2.5% | ₹187.50 |
| IGST | ₹0.00 |
| Invoice total | ₹7,875.00 |
| Outstanding | ₹7,875.00 |

### Next — Phase 3
- Dispatch endpoint (`POST /sales/{order_id}/dispatch`).
- Deduct finished goods from stock ledger.
- Prevent negative stock and duplicate dispatch.

### Completed — Dispatch
- Implemented dispatch endpoint (`POST /sales/{order_id}/dispatch`).
- Stock locked before deduction using `lock_items`.
- Stock re-checked at dispatch time (not just at approval).
- `sale_dispatch` ledger row written at WAC issue rate.
- Duplicate dispatch blocked with HTTP 409.

### Verified Benchmark — Retailer A Dispatch

| Field | Value |
|---|---|
| FG-MRK200 dispatched | 150.000 packets |
| Issue rate (WAC) | ₹19.4177 |
| FG-MRK200 balance after dispatch | 96.000 packets |

### Next — Phase 4
- Payment recording (`POST /sales/{order_id}/payment`).
- Outstanding balance update.
- Benchmark: record ₹4,000 payment, verify outstanding = ₹3,875.


### Completed — Payment
- Implemented payment recording endpoint (`POST /sales/{order_id}/payment`).
- Payment only allowed on dispatched orders.
- Overpayment blocked with HTTP 422.
- Payment inserted into `payments` table.
- `amount_paid` and `outstanding` updated on `sales_orders`.
- Multiple payments supported until fully settled.

### Verified Benchmark — Retailer A Payment

| Field | Value |
|---|---|
| Invoice total | ₹7,875.00 |
| Payment recorded | ₹4,000.00 |
| Outstanding | ₹3,875.00 |
| Fully paid | false |

### Next — Distributor B benchmark test
- Create order for 120 packets (Karnataka customer, IGST 5%).
- Approve — verify IGST calculation.
- Dispatch — expect failure due to insufficient stock (96 packets available).

### Verified — Distributor B Benchmark

- Order created: ORD-20261120-0002, 120 packets, ₹6,000 taxable value.
- Approval blocked correctly: insufficient stock (need 120, have 96).
- Stock shortage: 24 packets.
- IGST logic confirmed: Karnataka customer would attract IGST 5%.
- No stock movement occurred for Distributor B order.

### Sales Module — Complete

All four phases implemented and benchmark-verified:
1. Sales order creation
2. Admin approval and GST invoice generation
3. Dispatch and stock deduction
4. Payment recording and outstanding balance

### Completed — Stock Ledger Report
- Implemented `GET /inventory/ledger?item_code=XX`.
- Returns chronological stock movements with running balance.
- Running balance calculated using PostgreSQL window function.
- Tested with FG-MRK200 and RM-FLOUR — all movements and balances correct.
- Accessible to all roles.



## Day 4 — Benchmark Reset and Verification

### Completed
- Reset transaction data to correct benchmark numbers from problem statement.
- Re-ran full benchmark scenario end to end.
- All stock balances, costing, GST, and outstanding figures verified.

### Verified Final Benchmark

| Check | Expected | Result |
|---|---|---|
| Flour closing balance | 120 kg | ✅ |
| Oil closing balance | 19.5 L | ✅ |
| Pouches closing balance | 306 | ✅ |
| FG after production run | 238 packets | ✅ |
| FG after Retailer A dispatch | 88 packets | ✅ |
| Oil variance | +5% flagged | ✅ |
| Carton variance | −10% flagged | ✅ |
| Yield variance | 188 vs 200, −6% flagged | ✅ |
| Retailer A invoice | ₹7,875 | ✅ |
| Retailer A outstanding | ₹3,875 | ✅ |
| Distributor B shortage | 32 packets | ✅ |
| Cost per packet | ₹31.1436 | ✅ |

### Completed — React Frontend
- Login page with role-based redirect.
- Salesman dashboard — finished goods stock, place order form, live taxable value preview.
- Admin dashboard — stock summary, order list with status badges, approve, dispatch, payment, invoice download.
- Axios client with JWT interceptor and auto-redirect on 401.
- Added `GET /sales/orders` endpoint for admin order listing.

### Completed — Excel Export
- Implemented `GET /reports/stock` — full stock ledger with running balance exported to Excel.
- Implemented `GET /reports/sales` — sales register with GST breakup exported to Excel.
- Styled header rows with dark blue background and white bold text.
- Both reports verified against benchmark data.

## Docker Compose Parallel-Run Milestone — November 24, 2026

### Completed
- Removed fixed Compose container names so Docker Compose generates project-scoped names.
- Changed published host ports to PostgreSQL `5433:5432` and API `8001:8000`; internal service DNS remains `db:5432`.
- Added the Debian runtime libraries required by WeasyPrint to the backend image.
- Ordered the Dockerfile to retain the cached Python dependency layer when only system libraries change.
- Started the original project alongside the existing tested copy without changing the tested-copy containers or its database volume.

### Verified
- `docker compose config --quiet` passed (Compose reports only the existing obsolete `version` warning).
- Original PostgreSQL container is healthy and published on port 5433.
- Original API container is running and `http://localhost:8001/docs` returned HTTP 200.
- The original `cdi-food-internship_postgres_data` database has the schema but zero rows in the inspected master and business tables; no seed or business data was added.
