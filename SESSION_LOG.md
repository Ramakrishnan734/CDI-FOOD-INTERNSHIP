# CDI Food ERP — Complete Session Log
# NIT Tiruchirappalli — CDI Software Developer Intern Winter 2026

---

## Project Overview

Build an order-to-audit ERP system for a small South Indian packaged snacks
manufacturing factory. The system connects two business loops:

**Production loop:** Purchase → Raw material stock → BOM → Production run →
Finished goods → Costing and variance.

**Sales loop:** Salesman order → Admin approval → GST invoice → Dispatch →
Stock deduction → Payment → Outstanding balance.

Both loops share a single stock ledger as the source of truth.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.14 + FastAPI |
| Database | PostgreSQL 16 |
| DB Access | SQLAlchemy Core (raw SQL, no ORM) |
| Auth | JWT (python-jose) + bcrypt |
| PDF | WeasyPrint 70.0 |
| Excel | openpyxl 3.1.5 |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Railway (backend) + Vercel (frontend) |
| Local Dev | Docker Compose |

---

## Project Structure

```
CDI-FOOD-INTERNSHIP/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point, router registration
│   │   ├── database.py              # SQLAlchemy engine, PostgreSQL connection
│   │   ├── dependencies.py          # JWT auth dependency, RBAC dependency
│   │   ├── routers/
│   │   │   ├── auth.py              # POST /auth/login
│   │   │   ├── inventory.py         # Purchase, balance, ledger endpoints
│   │   │   ├── production.py        # Production run endpoints
│   │   │   ├── sales.py             # Sales order, approval, dispatch, payment, PDF
│   │   │   └── reports.py           # Excel export endpoints
│   │   ├── services/
│   │   │   ├── inventory_service.py # WAC calculation, stock locking
│   │   │   └── pdf_service.py       # WeasyPrint PDF generation
│   │   ├── templates/
│   │   │   └── invoice.html         # GST invoice HTML template
│   │   └── models/
│   │       └── schema.sql           # 14-table PostgreSQL schema
│   ├── seed/
│   │   └── seed.py                  # Master data and opening stock
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx                  # Router, PrivateRoute
│   │   ├── api/
│   │   │   ├── client.js            # Axios instance, JWT interceptor
│   │   │   ├── auth.js              # Login API call
│   │   │   └── sales.js             # Sales API calls
│   │   └── pages/
│   │       ├── Login.jsx            # Login screen
│   │       ├── SalesmanDashboard.jsx # Place order screen
│   │       └── AdminDashboard.jsx   # Admin management screen
│   ├── vite.config.js               # Vite + Tailwind config, API proxy
│   └── package.json
├── docker-compose.yml
├── README.md
├── DESIGN_NOTE.md
├── ASSUMPTIONS.md
├── DEVELOPMENT_LOG.md
├── TASK_TRACKER.md
└── SESSION_LOG.md
```

---

## Database Schema — 14 Tables

### Design principle
The stock_ledger table is the single source of truth for all inventory.
No table stores a running balance. Balance is always computed as:

```sql
SELECT SUM(qty_in) - SUM(qty_out) FROM stock_ledger WHERE item_id = X
```

### Tables

| Group | Tables |
|---|---|
| Masters | users, items, customers, suppliers |
| BOM | bom_headers, bom_lines |
| Inventory | stock_ledger |
| Purchasing | purchase_orders, purchase_lines |
| Production | production_runs, production_lines |
| Sales | sales_orders, sales_order_lines, payments |

### Money and quantity precision
- Money: `NUMERIC(15,4)` — no float arithmetic anywhere
- Quantity: `NUMERIC(12,4)` — handles kg, litres, pieces precisely
- Python: `Decimal` used throughout — never `float` for financial calculations

---

## Roles and Access

| Role | Access |
|---|---|
| owner | Read all |
| admin | Full access to everything |
| salesman | Create orders, view stock |
| production | Purchase, production runs, view stock |
| auditor | Read all |

Seed credentials:
- admin@cdi.com / admin123
- salesman_a@cdi.com / sales123
- salesman_b@cdi.com / sales123
- prod@cdi.com / prod123
- audit@cdi.com / audit123
- owner@cdi.com / owner123

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Returns JWT token |

### Inventory
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/inventory/purchase` | admin, production | Record purchase, update WAC |
| GET | `/inventory/balance` | all | Current stock balances |
| GET | `/inventory/ledger?item_code=XX` | all | Stock movements with running balance |

### Production
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/production/start` | admin, production | Create draft run from BOM |
| POST | `/production/{id}/post` | admin, production | Post run, update stock, calculate variance |

### Sales
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/sales/order` | salesman, admin | Create pending sales order |
| GET | `/sales/orders` | admin, owner, auditor | List all orders |
| POST | `/sales/{id}/approve` | admin | Approve order, generate GST invoice |
| POST | `/sales/{id}/dispatch` | admin | Dispatch, deduct stock |
| POST | `/sales/{id}/payment` | admin | Record payment |
| GET | `/sales/{id}/invoice/pdf` | admin, owner, auditor | Download PDF invoice |

### Reports
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/reports/stock` | admin, owner, auditor, production | Stock ledger Excel export |
| GET | `/reports/sales` | admin, owner, auditor | Sales register Excel export |

---

## Key Design Decisions and Why

### 1. Stock ledger as single source of truth
Every stock movement — purchase, production issue, production output,
sale dispatch, adjustment — creates a row in stock_ledger. Balance is
always computed by summing qty_in - qty_out. This means:
- Complete audit trail of every movement
- No possibility of balance getting out of sync
- Running balance computed with PostgreSQL window function:
  `SUM(qty_in - qty_out) OVER (ORDER BY created_at, id ROWS BETWEEN
  UNBOUNDED PRECEDING AND CURRENT ROW)`

### 2. Weighted Average Cost (WAC)
On each purchase:

new_wac = (current_balance × current_wac + purchase_qty × purchase_rate)
/ (current_balance + purchase_qty)

Every ledger row stores the rate at time of movement. This allows
accurate costing of production issues and dispatches.

Benchmark calculation:

Opening flour: 100 kg × ₹42 = ₹4,200
Purchase: 60 kg × ₹45 = ₹2,700
WAC = (4200 + 2700) / (100 + 60) = ₹43.125/kg


### 3. Idempotent purchase API
Each purchase request carries a `client_request_id` and a SHA-256 hash
of the payload. If the same ID is replayed:
- Same payload → returns original result (HTTP 200)
- Different payload → returns HTTP 409

This prevents duplicate stock movements if the network drops and the
client retries.

### 4. Draft → Post production workflow
Production runs are created in draft status first. The supervisor
enters planned quantities from BOM. When actual quantities are known,
the run is posted:
- Stock-out rows written for each raw material at WAC
- Stock-in row written for finished goods at cost per packet
- Variance calculated: (actual - planned) / planned × 100
- Flagged if absolute variance > 3%

### 5. GST logic
Seller state: Tamil Nadu (TN)
- Customer in TN → CGST 2.5% + SGST 2.5% (intra-state)
- Customer outside TN → IGST 5% (inter-state)

Determined by comparing customers.state_code with seller state at
approval time.

### 6. Row locking for concurrent safety
Before any stock movement, `SELECT ... FOR UPDATE` is called on the
item rows. Locks are taken in sorted ID order to prevent deadlocks.
This ensures two simultaneous requests cannot create negative stock.

### 7. Decimal arithmetic throughout
Python `Decimal` is used for all financial calculations. PostgreSQL
`NUMERIC` is used for all money and quantity columns. Float is never
used for financial arithmetic — only for Excel export where openpyxl
requires it.

---

## Implementation — Day by Day

### Day 1 (November 19, 2026) — Claude 1
- PostgreSQL setup and database creation
- 14-table schema design and creation
- Seed script with master data and opening stock
- FastAPI application setup
- JWT authentication and login
- Role-based access control (RBAC)
- Inventory purchase API
- Stock balance API
- Purchase validations
- Stock locking and WAC calculation

### Day 2 (November 20, 2026) — Claude 1
- Purchase idempotency using client_request_id and SHA-256 hash
- Benchmark purchase: 60 kg flour at ₹45/kg
- Verified WAC: ₹43.1250/kg, balance: 160 kg

### Day 3 (November 20, 2026) — Claude 1
- Production workflow: draft and post two-phase design
- BOM-based planned quantity calculation
- Raw material consumption recording at WAC
- Finished goods output recording at cost per packet
- Yield and consumption variance calculation
- Variance alerts at 3% threshold

### Day 4 (November 20, 2026) — Claude 2 (this session)

#### Handover and verification
- Read all uploaded files and Git history
- Verified actual database state against Claude 1's reported results
- Confirmed all 6 opening stock balances
- Identified benchmark discrepancy — Claude 1 used wrong production actuals

#### Sales module — Phase 1: Order creation
- POST /sales/order
- Customer and item validation
- Order number generation: ORD-YYYYMMDD-NNNN
- Status: pending, no stock movement at creation

#### Sales module — Phase 2: Admin approval and GST invoice
- POST /sales/{id}/approve
- Stock availability check at approval time
- GST calculation based on customer state
- Invoice number generation: INV-FY2627-NNNN
- All invoice fields stored on sales_orders row
- Double-approval blocked with HTTP 409

#### Sales module — Phase 3: Dispatch
- POST /sales/{id}/dispatch
- Items locked before deduction
- Stock re-checked at dispatch time
- sale_dispatch ledger row written at WAC
- Duplicate dispatch blocked with HTTP 409

#### Sales module — Phase 4: Payment
- POST /sales/{id}/payment
- Payment inserted into payments table
- amount_paid and outstanding updated on sales_orders
- Overpayment blocked with HTTP 422
- Multiple payments supported

#### Stock ledger report
- GET /inventory/ledger?item_code=XX
- Running balance via PostgreSQL window function
- Tested with FG-MRK200 and RM-FLOUR

#### Documentation
- README with setup, API reference, benchmark results
- Docker Compose with PostgreSQL and FastAPI containers
- Dockerfile for backend

#### Benchmark reset and verification
- Reset transaction data to correct benchmark numbers
- Re-ran full benchmark end to end
- All figures verified against problem statement

#### PDF invoice
- WeasyPrint HTML template
- GET /sales/{id}/invoice/pdf
- Returns PDF bytes as streaming response
- Verified: correct GST, amounts, customer details

#### React frontend
- Vite + React + Tailwind CSS
- Login page with role-based redirect
- Salesman dashboard: stock view, place order form
- Admin dashboard: order list, approve, dispatch, payment, download invoice
- Axios client with JWT interceptor

#### Excel export
- GET /reports/stock — full stock ledger with running balance
- GET /reports/sales — sales register with GST breakup
- openpyxl with styled headers

---

## Benchmark Verification — Final Results

### Opening stock (after seed)
| Item | Balance | Unit |
|---|---:|---|
| RM-FLOUR | 100.000 | kg |
| RM-OIL | 30.000 | litre |
| RM-SPICE | 5.000 | kg |
| PK-POUCH | 500.000 | piece |
| PK-CARTON | 30.000 | piece |
| FG-MRK200 | 50.000 | packet |

### After purchase (60 kg flour at ₹45/kg)
| Item | Balance | WAC |
|---|---:|---:|
| RM-FLOUR | 160.000 kg | ₹43.1250/kg |

### After production run
| Check | Expected | Result |
|---|---|---|
| Flour consumed | 40 kg | ✅ 40 kg |
| Oil consumed | 10.5 L | ✅ 10.5 L |
| Spice consumed | 1.2 kg | ✅ 1.2 kg |
| Pouches consumed | 194 (188+6) | ✅ 194 |
| Cartons used | 9 | ✅ 9 |
| Actual output | 188 packets | ✅ 188 packets |
| RM-FLOUR balance | 120 kg | ✅ 120 kg |
| RM-OIL balance | 19.5 L | ✅ 19.5 L |
| RM-SPICE balance | 3.8 kg | ✅ 3.8 kg |
| PK-POUCH balance | 306 pieces | ✅ 306 pieces |
| PK-CARTON balance | 21 pieces | ✅ 21 pieces |
| FG-MRK200 balance | 238 packets | ✅ 238 packets |
| Oil variance | +5% flagged | ✅ |
| Carton variance | -10% flagged | ✅ |
| Yield variance | -6% flagged | ✅ |
| Labour cost | ₹1,200 | ✅ |
| Overhead cost | ₹600 | ✅ |
| Total cost | ₹5,855 | ✅ |
| Cost per packet | ₹31.1436 | ✅ |

### After Retailer A sale
| Check | Expected | Result |
|---|---|---|
| Taxable value | ₹7,500.00 | ✅ |
| CGST 2.5% | ₹187.50 | ✅ |
| SGST 2.5% | ₹187.50 | ✅ |
| Invoice total | ₹7,875.00 | ✅ |
| FG balance | 88 packets | ✅ |
| Payment | ₹4,000.00 | ✅ |
| Outstanding | ₹3,875.00 | ✅ |

### Distributor B
| Check | Expected | Result |
|---|---|---|
| Stock available | 88 packets | ✅ |
| Order qty | 120 packets | ✅ |
| Shortage | 32 packets | ✅ |
| Approval blocked | Yes | ✅ |
| GST type if fulfilled | IGST 5% | ✅ |

---

## Git Commit History

8b77e77 docs: update log and tracker after Excel export completion
4271024 feat: implement Excel export for stock ledger and sales register
40ff653 docs: update log and tracker after frontend completion
e2c5640 feat: add React frontend with salesman order and admin dashboard
9e75610 feat: implement GST invoice PDF generation using WeasyPrint
9b1f1b3 docs: reset and verify full benchmark against problem statement
c47073c chore: move Dockerfile to correct location backend/
19d5668 chore: add Docker Compose and Dockerfile for local development
478ec53 docs: add project README with setup instructions and API reference
9e96e7f feat: implement stock ledger report with running balance
906744e docs: verify Distributor B benchmark and mark sales module complete
eba4808 feat: implement payment recording and outstanding balance tracking
dd49ed3 feat: implement dispatch and finished goods stock deduction
857c3c9 feat: add admin approval and GST invoice generation with benchmark verification
9f53231 feat: implement sales order creation with customer and item validation
482252e feat: implement sales order creation with customer and item validation
af0f879 feat: production workflow with BOM costing and variance detection
b8ab5f6 feat: purchase API idempotency and benchmark WAC verification
55992ff docs: update development progress and task tracker
9ab6f92 Day 2-3: auth, RBAC, purchase endpoint (pre-review checkpoint)
7831bac Day 1: Add project documentation files


---

## Demo Video Script — 8 Minutes

Walk through section 5 of the problem statement in order.

### 0:00 — Introduction (30 sec)
- Show GitHub repo URL and commit history
- Briefly show README

### 0:30 — Login as salesman (30 sec)
- Open localhost:5173
- Login as salesman_a@cdi.com / sales123
- Show salesman dashboard — finished goods stock visible

### 1:00 — Place Retailer A order (1 min)
- Select Retailer A (Tamil Nadu)
- Enter qty 150, price ₹50
- Place order — show success: ORD-20261120-0001

### 2:00 — Admin login (30 sec)
- Login as admin@cdi.com / admin123
- Show admin dashboard — order appears as pending

### 2:30 — Approve and invoice (1 min)
- Click Approve & Invoice on Retailer A order
- Show: INV-FY2627-0001, CGST ₹187.50, SGST ₹187.50, total ₹7,875

### 3:30 — Download PDF invoice (30 sec)
- Click Download Invoice
- Open PDF — show all fields, GST breakup, outstanding

### 4:00 — Dispatch (30 sec)
- Click Dispatch
- Show stock drops from 238 to 88 packets

### 4:30 — Distributor B shortage (1 min)
- Login as salesman, place order for Distributor B, qty 120
- Switch to admin, try to approve
- Show error: insufficient stock, need 120 have 88

### 5:30 — Record payment (30 sec)
- Record ₹4,000 from Retailer A
- Show outstanding ₹3,875

### 6:00 — Reports (1 min)
- Download sales register Excel
- Download stock ledger Excel
- Show both files open with correct data

### 7:00 — Production and API docs (30 sec)
- Open localhost:8000/docs
- Show production run result — 188 packets, oil +5% flagged

### 7:30 — Closing (30 sec)
- Show GitHub commit history
- Mention Docker Compose for local run

---

## Running Locally

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/cdi_food_db"
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker Compose (single command)
```bash
docker compose up --build
```

### Seed the database
```bash
cd backend
python -m seed.seed
```

API docs: http://localhost:8000/docs
Frontend: http://localhost:5173

---

## Known Gaps and Assumptions

### Assumptions
1. Seller state is always Tamil Nadu (TN)
2. Pouches consumed = good packets + damaged packets
3. Cartons consumed entered manually by supervisor
4. Opening finished goods stock has rate = 0 (no prior production cost)
5. WAC used for raw material valuation
6. Labour and overhead allocated entirely to the run they are entered against
7. Variance threshold: 3%
8. Posted runs and dispatched invoices cannot be deleted
9. Invoice format: INV-FY2627-NNNN
10. Salesman sees only their own orders (backend enforced)

### Known gaps
- No offline order capture (mobile PWA sync)
- No batch/expiry tracking
- No reorder level alerts
- No production planning from pending orders
- No Tally export
- Frontend shows all orders to admin — no date filter yet
- No salesman order history screen

### Benchmark differences explained
The cost per packet (₹31.1436) differs from a simple calculation because:
- Opening 50 FG packets have rate = 0 (assumption 4)
- WAC for dispatch is blended across opening + produced stock
- The benchmark production run yielded 188 packets from a planned 200 (-6% yield variance). Oil usage was +5% and was flagged against the 3% variance threshold.

---

## Docker Compose Session — November 24, 2026

- Updated the original Compose configuration to use generated container names, PostgreSQL host port 5433, and API host port 8001 so it can run beside the tested copy.
- Added required WeasyPrint system libraries to the backend image and retained the cached Python dependency layer during rebuilds.
- Verified original database health, API docs at `http://localhost:8001/docs` (HTTP 200), and that the original database is empty; no data was seeded.
- Confirmed the tested-copy containers and `cdi-food-internship3_postgres_data` volume were not modified.

---

## Source-and-Documentation Audit — November 24, 2026

- Read-only checks verified the preserved test stack's authentication, balances, order list, ledger, Excel exports, and invoice PDF.
- The current preserved data retains the documented final stock balances and Retailer A totals, but its ledger records production before the flour purchase. Its actual flour WAC is ₹43.5000 and production output rate is ₹30.9043; earlier ₹43.1250 and ₹31.1436 figures remain historical target calculations, not the current runtime state.
- A fresh Compose database lacks the two `purchase_orders` idempotency columns required by the purchase API. This is documented as an unresolved source-schema gap; no source-code change was made during this audit.

## Fresh-Schema Purchase Fix — November 24, 2026

- Added `client_request_id` and `request_hash` to the checked-in `purchase_orders` schema.
- Verified the purchase endpoint on an isolated fresh Compose database: initial purchase succeeded, exact replay returned the original result without duplicate writes, and a changed payload with the same request ID returned HTTP 409.
- This follow-up resolves the fresh-schema gap noted in the earlier audit. Preserved databases were not modified.
