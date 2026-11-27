# CDI Food ERP

An order-to-audit ERP system for a small South Indian packaged snacks manufacturing factory.

Built for the NIT Tiruchirappalli Centre for Digital Infrastructure — Software Developer Intern (Winter 2026) assignment.

> **Source-verification notice:** This README is based on the assignment problem statement and the project's available documentation and development records. The submitted source ZIP has not been independently audited in this review. Features and implementation details are therefore described as documented, not independently source-verified. Demo credentials below are documented in the session log and have not been verified against the current `backend/seed/seed.py`.

---

## Business Workflows

**Production workflow**

Purchase raw materials → update stock → run BOM-based production → record finished goods → calculate cost and variance.

**Sales workflow**

Salesman creates order → admin approves and generates GST invoice → dispatch deducts stock → record payments → track outstanding balance.

Both workflows use a shared stock ledger as the inventory source of truth.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python + FastAPI |
| Database | PostgreSQL 16 |
| DB access | SQLAlchemy Core |
| Authentication | JWT + bcrypt |
| Frontend | React + Vite + Tailwind CSS |
| PDF invoices | WeasyPrint |
| Excel reports | openpyxl |
| Local environment | Docker Compose |

The Docker environment is documented as using Python 3.12. Local development records also mention Python 3.14.

---

## Project Structure

```text
CDI-FOOD-INTERNSHIP/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── models/
│   │   │   └── schema.sql
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── inventory.py
│   │   │   ├── production.py
│   │   │   ├── sales.py
│   │   │   └── reports.py
│   │   ├── services/
│   │   │   ├── inventory_service.py
│   │   │   └── pdf_service.py
│   │   └── templates/
│   │       └── invoice.html
│   ├── seed/
│   │   └── seed.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml
├── README.md
├── DESIGN_NOTE.md
├── ASSUMPTIONS.md
├── DEVELOPMENT_LOG.md
├── TASK_TRACKER.md
└── SESSION_LOG.md
```

The database schema is located at `backend/app/models/schema.sql`.

The documented schema contains 14 tables covering users, masters, BOM, inventory ledger, purchasing, production, sales, and payments.

---

## Local Setup

### Prerequisites

- Python 3.12 or later
- PostgreSQL 16
- Node.js 20 or later for the frontend
- npm
- Git

### Backend setup

From the repository root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a PostgreSQL database:

```bash
createdb cdi_food_db
```

Initialize the schema from the `backend` directory:

```bash
psql -U your_user -d cdi_food_db -f app/models/schema.sql
```

Configure the database connection:

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/cdi_food_db"
```

Run the backend:

```bash
uvicorn app.main:app --reload
```

API documentation:

```text
http://localhost:8000/docs
```

### Seed data

The seed command is documented as:

```bash
cd backend
python -m seed.seed
```

This command is intended for a fresh database. The exact current seed contents and demo credentials have not been independently verified against `backend/seed/seed.py` during this README review.

Do not run the seed script against the preserved benchmark database unless you intentionally want to initialize a fresh database.

### Frontend setup

From the repository root:

```bash
cd frontend
npm install
npm run dev
```

The local frontend is documented at:

```text
http://localhost:5173
```

### Docker Compose

From the repository root:

```bash
docker compose up -d --build
```

The documented Compose configuration publishes:

- PostgreSQL on `localhost:5433`
- API documentation at `http://localhost:8001/docs`

The containers communicate internally through `db:5432`.

On a fresh `cdi-food-internship_postgres_data` volume, Compose initializes the schema but does not automatically seed master or business data.

To stop the containers while preserving the database volume:

```bash
docker compose down
```

Do not add `-v` if you want to preserve the database volume.

---

## Documented API Endpoints

The following endpoints are documented in the project README and development records. Their current source implementation has not been independently audited as part of this README review.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/login` | Login and obtain a JWT token |

### Inventory

| Method | Endpoint | Description |
|---|---|---|
| POST | `/inventory/purchase` | Record a purchase |
| GET | `/inventory/balance` | View current stock balances |
| GET | `/inventory/ledger?item_code=XX` | View stock ledger with running balance |
| POST | `/inventory/items` | Create an item with code/type validation |
| GET | `/inventory/items` | List items |

### Production

| Method | Endpoint | Description |
|---|---|---|
| POST | `/production/start` | Create a draft production run |
| POST | `/production/{id}/post` | Post production and update stock |
| GET | `/production/boms` | View active BOMs |
| GET | `/production/runs` | View production run history |

### Sales

| Method | Endpoint | Description |
|---|---|---|
| POST | `/sales/order` | Create a sales order |
| POST | `/sales/{id}/approve` | Approve order and generate GST invoice |
| POST | `/sales/{id}/dispatch` | Dispatch and deduct finished goods stock |
| POST | `/sales/{id}/payment` | Record payment |
| GET | `/sales/orders` | List sales orders |
| GET | `/sales/{id}/invoice/pdf` | Download GST invoice PDF |

### Reports

| Method | Endpoint | Description |
|---|---|---|
| GET | `/reports/stock` | Export stock ledger to Excel |
| GET | `/reports/sales` | Export sales register to Excel |
| GET | `/reports/production-costing` | Export production costs and indicative product margins |
| GET | `/reports/gst-summary` | Export GST totals grouped by invoice date |
| GET | `/reports/purchases` | Export posted purchase lines |
| GET | `/reports/outstanding-ageing` | Export outstanding dispatched invoices with ageing buckets |

---

## Roles and Access

The following access descriptions are documented in the project materials and are not independently source-verified in this README review.

| Role | Documented access |
|---|---|
| owner | Read-only business overview and reports |
| admin | Administrative workflows |
| salesman | Create sales orders and view stock |
| production | Purchase, production runs, and stock visibility |
| auditor | Read-only financial and audit visibility |

The documented role dashboards include owner and auditor views. The exact dashboard behavior and role enforcement should be verified against the submitted source before treating this README as source-certified.

---

## Key Design Decisions

- **Stock ledger as the single source of truth:** Inventory balances are calculated from ledger movements rather than maintained as independent running balances.
- **Weighted Average Cost (WAC):** Purchase valuation updates the weighted average rate used for material issues.
- **Decimal arithmetic:** Financial and quantity calculations are documented as using decimal values to avoid floating-point rounding errors.
- **Purchase idempotency:** Purchase requests are documented as using `client_request_id` and a SHA-256 hash to detect duplicate requests.
- **Draft → Post production workflow:** Production is created as a draft and actual quantities are recorded when the run is posted.
- **BOM-based production:** Planned consumption is calculated from the active Bill of Materials.
- **Variance calculation:** Actual consumption is compared with planned consumption; the documented threshold is 3%.
- **GST logic:** Tamil Nadu seller; intra-state sales use CGST + SGST, while inter-state sales use IGST.
- **Stock safety:** The design documentation describes row locking before stock movements to help prevent concurrent requests from creating negative stock.

---

## Assignment Benchmark

This section records the intended benchmark values documented in the assignment and development records. These figures are distinct from the preserved November 25 runtime snapshot below.

### Opening stock

| Item | Opening balance |
|---|---:|
| RM-FLOUR | 100 kg |
| RM-OIL | 30 litre |
| RM-SPICE | 5 kg |
| PK-POUCH | 500 piece |
| PK-CARTON | 30 piece |
| FG-MRK200 | 50 packet |

### Flour purchase and WAC

Purchase: 60 kg flour at ₹45/kg.

| Item | Quantity | Rate / value |
|---|---:|---:|
| Opening flour | 100 kg | ₹42/kg |
| Purchase | 60 kg | ₹45/kg |
| Post-purchase balance | 160 kg | ₹43.1250/kg WAC |

Calculation:

```text
WAC = (100 × ₹42 + 60 × ₹45) / 160
    = ₹43.1250/kg
```

### Production benchmark

| Component | Actual quantity | Rate | Cost |
|---|---:|---:|---:|
| Flour | 40 kg | ₹43.125/kg | ₹1,725 |
| Oil | 10.5 litre | ₹140/litre | ₹1,470 |
| Spice | 1.2 kg | ₹200/kg | ₹240 |
| Pouches | 194 piece | ₹2.50/piece | ₹485 |
| Cartons | 9 piece | ₹15/piece | ₹135 |
| **Material cost** | | | **₹4,055** |
| Labour | | | ₹1,200 |
| Gas / power overhead | | | ₹600 |
| **Total production cost** | | | **₹5,855** |

Good output: 188 packets

Planned output: 200 packets

```text
Cost per packet = ₹5,855 / 188
                = ₹31.1436
```

Documented benchmark variances:

- Yield variance: −6%
- Oil variance: +5%
- Pouches consumed: 194, including 6 damaged pouches
- Cartons used: 9

### Retailer A — Tamil Nadu

| Field | Value |
|---|---:|
| Quantity | 150 packets |
| Taxable value | ₹7,500.00 |
| CGST 2.5% | ₹187.50 |
| SGST 2.5% | ₹187.50 |
| Invoice total | ₹7,875.00 |
| Payment | ₹4,000.00 |
| Outstanding | ₹3,875.00 |
| Finished goods after dispatch | 88 packets |

### Distributor B — Karnataka

| Field | Value |
|---|---:|
| Order quantity | 120 packets |
| Stock available | 88 packets |
| Shortage | 32 packets |
| Documented outcome | Approval blocked due to insufficient stock |
| GST type if fulfilled | IGST 5% |

---

## Current Preserved Runtime Snapshot — November 25, 2026

The following figures describe the preserved test-stack records as documented on November 25, 2026. They are not a fresh seed baseline and should not be confused with the assignment benchmark.

The preserved runtime records document **production before the flour purchase transaction**.

### Runtime production costing

At the time production was posted, the flour issue was valued at the opening-stock rate of ₹42/kg.

| Component | Actual quantity | Issue rate | Cost |
|---|---:|---:|---:|
| Flour | 40 kg | ₹42/kg | ₹1,680 |
| Oil | 10.5 litre | ₹140/litre | ₹1,470 |
| Spice | 1.2 kg | ₹200/kg | ₹240 |
| Pouches | 194 piece | ₹2.50/piece | ₹485 |
| Cartons | 9 piece | ₹15/piece | ₹135 |
| **Material cost** | | | **₹4,010** |
| Labour | | | ₹1,200 |
| Gas / power overhead | | | ₹600 |
| **Total production cost** | | | **₹5,810** |

Good output: 188 packets

```text
Runtime cost per packet = ₹5,810 / 188
                        = ₹30.9043
```

After production, the 60 kg of remaining opening flour was combined with the 60 kg purchase at ₹45/kg, resulting in a closing flour balance of 120 kg and a post-purchase WAC of ₹43.5000/kg. This closing WAC does not retroactively change the rate recorded for the earlier production issue.

### Runtime flour balance and WAC

| Item | Quantity |
|---|---:|
| Opening flour | 100 kg |
| Flour issued before purchase | 40 kg |
| Remaining opening flour | 60 kg |
| Subsequent purchase | 60 kg |
| Closing flour balance | 120 kg |
| Post-purchase WAC | ₹43.5000/kg |

### Retailer A — preserved runtime records

| Field | Value |
|---|---:|
| Taxable value | ₹7,500.00 |
| CGST 2.5% | ₹187.50 |
| SGST 2.5% | ₹187.50 |
| Invoice total | ₹7,875.00 |
| Payment | ₹4,000.00 |
| Outstanding | ₹3,875.00 |
| Finished goods after dispatch | 88 packets |

### Distributor B — preserved runtime records

| Situation | Result |
|---|---|
| Order quantity | 120 packets |
| Stock available | 88 packets |
| Shortage | 32 packets |
| Approval | Pending / not exercised in the preserved audit |
| GST type if fulfilled | IGST 5% |

---

## Documented Reports

The project documentation describes the following Excel reports:

- Stock ledger with running balance
- Sales register with GST breakup
- Production costing and indicative product margins
- GST summary grouped by invoice date
- Purchase register
- Outstanding invoice ageing

The production costing report documents material cost, labour, overhead, cost per packet, average selling price, and indicative product-level margin.

---

## Known Gaps and Assumptions

The following assumptions and limitations are documented in the project materials. Their current source implementation has not been independently audited during this README review.

### Assumptions

1. Seller state is Tamil Nadu.
2. Pouches consumed equal good packets plus damaged packets.
3. Cartons consumed are entered manually by the supervisor.
4. Opening finished goods stock has a rate of zero because no prior production cost is available.
5. Raw materials are valued using weighted average cost.
6. Labour and overhead are allocated entirely to the production run where they are entered.
7. Variance threshold is 3%.
8. Posted production runs and dispatched invoices cannot be deleted.
9. Invoice numbering follows `INV-FY2627-NNNN`.
10. Monetary and quantity calculations use decimal values / PostgreSQL `NUMERIC`.
11. Credit note and correction workflows are not documented as implemented.
12. The seed script is intended for a fresh database and should not be run against a preserved benchmark database.

### Not documented as implemented / not verified

The following stretch features were not documented as implemented or were not verified in the available project records:

- Offline synchronization
- Batch / expiry tracking and FEFO
- Low-stock alerts
- Production planning
- Route or GPS tracking
- Tally integration
- E-invoice / e-waybill integration
- Tamil-language interface

---

## Demo Accounts

The following demo accounts are listed in the project session log. They are **documented credentials, not independently verified against the current seed script**. Use only in a local demo environment.

| Role | Email | Password |
|---|---|---|
| admin | `admin@cdi.com` | `admin123` |
| salesman | `salesman_a@cdi.com` | `sales123` |
| salesman | `salesman_b@cdi.com` | `sales123` |
| production | `prod@cdi.com` | `prod123` |
| auditor | `audit@cdi.com` | `audit123` |
| owner | `owner@cdi.com` | `owner123` |

These are demonstration credentials only. Do not use them for a production deployment or real customer data.

---

## Verification Notes

Development records document:

- Opening stock balances checked against the benchmark
- Purchase idempotency checks
- Production costing and variance checks
- GST invoice PDF generation
- Excel report exports
- Docker Compose configuration checks
- A test run reporting 14 passed tests and 2 passed subtests

These results are reported from the available development records and have not been independently rerun during this README review.

---

## Project Documentation

- `DESIGN_NOTE.md` — documented data model, stock ledger, BOM, WAC, GST, and design decisions
- `ASSUMPTIONS.md` — documented business assumptions and limitations
- `DEVELOPMENT_LOG.md` — development progress and verification notes
- `TASK_TRACKER.md` — task status
- `SESSION_LOG.md` — implementation and benchmark history
