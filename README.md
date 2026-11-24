# CDI Food ERP

An order-to-audit ERP system for a small South Indian packaged snacks manufacturing factory.

Built for the NIT Tiruchirappalli Centre for Digital Infrastructure — Software Developer Intern (Winter 2026) assignment.

---

## Business Workflows

**Production workflow**
Purchase raw materials → update stock → run BOM-based production → record finished goods → calculate cost and variance.

**Sales workflow**
Salesman creates order → admin approves and generates GST invoice → dispatch deducts stock → record payments → track outstanding balance.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 (Docker) + FastAPI |
| Database | PostgreSQL 16 |
| DB Access | SQLAlchemy Core (raw SQL) |
| Auth | JWT + bcrypt |
| Frontend | React + Vite + Tailwind CSS + shadcn/ui |
| PDF | WeasyPrint |
| Excel | openpyxl |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## Project Structure

```
CDI-FOOD-INTERNSHIP/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entry point
│   │   ├── database.py           # PostgreSQL engine
│   │   ├── dependencies.py       # Auth and DB dependencies
│   │   ├── routers/
│   │   │   ├── auth.py           # Login and JWT
│   │   │   ├── inventory.py      # Purchase, balance, ledger
│   │   │   ├── production.py     # Production runs
│   │   │   └── sales.py          # Orders, approval, dispatch, payment
│   │   └── services/
│   │       └── inventory_service.py  # WAC and stock locking
│   ├── models/
│   │   └── schema.sql            # 14-table database schema
│   └── requirements.txt
├── DESIGN_NOTE.md
├── ASSUMPTIONS.md
├── DEVELOPMENT_LOG.md
├── TASK_TRACKER.md
└── README.md
```

---

## Local Setup

### Prerequisites
- Python 3.12 or later
- PostgreSQL 16
- Node.js 20 (for frontend)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create the database:

```bash
createdb cdi_food_db
psql -U your_user -d cdi_food_db -f app/models/schema.sql
```

Set environment variable (optional — defaults to local):

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/cdi_food_db"
```

Run the server:

```bash
uvicorn app.main:app --reload
```

API documentation available at: `http://localhost:8000/docs`

---

### Docker Compose

Start the containerized backend and database:

```bash
docker compose up -d --build
```

The Compose environment is configured to run alongside another local CDI Food
stack: PostgreSQL is published on `localhost:5433` and API documentation is at
`http://localhost:8001/docs`. The containers still communicate internally as
`db:5432`.

On a fresh `cdi-food-internship_postgres_data` volume, Compose initializes the
schema but does not seed master or business data. To stop the containers while
preserving that volume, run `docker compose down` (without `-v`).

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login and get JWT token |

### Inventory
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/inventory/purchase` | admin, production | Record a purchase |
| GET | `/inventory/balance` | all | Current stock balances |
| GET | `/inventory/ledger?item_code=XX` | all | Stock ledger with running balance |
| POST | `/inventory/items` | admin | Create an item with code/type validation |
| GET | `/inventory/items` | all | List items |

### Production
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/production/start` | admin, production | Create draft production run |
| POST | `/production/{id}/post` | admin, production | Post run and update stock |

### Sales
| Method | Endpoint | Role | Description |
|---|---|---|---|
| POST | `/sales/order` | salesman, admin | Create sales order |
| POST | `/sales/{id}/approve` | admin | Approve order and generate GST invoice |
| POST | `/sales/{id}/dispatch` | admin | Dispatch and deduct stock |
| POST | `/sales/{id}/payment` | admin | Record payment |
| GET | `/sales/orders` | admin, owner, auditor | List sales orders |
| GET | `/sales/{id}/invoice/pdf` | admin, owner, auditor | Download GST invoice PDF |

### Reports
| Method | Endpoint | Role | Description |
|---|---|---|---|
| GET | `/reports/stock` | admin, owner, auditor, production | Download the stock ledger as Excel |
| GET | `/reports/sales` | admin, owner, auditor | Download the sales register as Excel |
| GET | `/reports/production-costing` | admin, owner, auditor | Download production costs and indicative product margins as Excel |
| GET | `/reports/gst-summary` | admin, owner, auditor | Download GST totals grouped by invoice date as Excel |
| GET | `/reports/purchases` | admin, owner, auditor | Download posted purchase lines as a Purchase Register Excel report |
| GET | `/reports/outstanding-ageing` | admin, owner, auditor | Download outstanding dispatched invoices with invoice-age buckets as Excel |

---

## Roles

| Role | Access |
|---|---|
| owner | Read all |
| admin | Full access |
| salesman | Create orders, view stock |
| production | Purchase, production runs, view stock |
| auditor | Read all |

---

## Key Design Decisions

- **Stock ledger as single source of truth** — no running balance stored; always computed from ledger rows.
- **Weighted Average Cost (WAC)** — used for raw material and finished goods valuation.
- **Decimal arithmetic throughout** — no float used for financial calculations.
- **Idempotent purchase API** — duplicate requests detected via `client_request_id` and SHA-256 hash.
- **Draft → Post production workflow** — planned quantities recorded first, actuals posted separately.
- **GST logic** — seller state TN; same state → CGST + SGST; different state → IGST.

---

## Current Preserved Test-Stack Snapshot

The following figures were read without modification from the preserved test
stack on November 24, 2026. They are the current runtime state, not a fresh
seed baseline.

### Flour Purchase
| Item | Opening | Purchased | Balance | WAC |
|---|---:|---:|---:|---:|
| RM-FLOUR | 100 kg | 60 kg | 120 kg | ₹43.5000/kg |

The ledger records the production issue before the ₹45/kg purchase, so this
current WAC differs from the historical target calculation documented in
`DESIGN_NOTE.md`.

### Production Run
| Output | Cost |
|---|---:|
| 188 packets (planned 200) | ₹30.9043/packet |
| Yield variance | −6% (recorded in the historical benchmark) |
| Oil variance | +5% (recorded in the historical benchmark) |

### Retailer A — Tamil Nadu
| Field | Value |
|---|---:|
| Taxable value | ₹7,500.00 |
| CGST 2.5% | ₹187.50 |
| SGST 2.5% | ₹187.50 |
| Invoice total | ₹7,875.00 |
| Payment | ₹4,000.00 |
| Outstanding | ₹3,875.00 |

### Distributor B — Karnataka
| Situation | Result |
|---|---|
| Order: 120 packets | Pending; approval was not exercised in the current audit |
| Stock available | 88 packets |
| Shortage | 32 packets |
| GST type if fulfilled | IGST 5% |
