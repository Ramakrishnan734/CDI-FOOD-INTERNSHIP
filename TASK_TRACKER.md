# CDI Food ERP — Task Tracker

## Completed
- [x] Purchase workflow from a fresh schema — idempotency columns and purchase replay/conflict behavior verified on an isolated fresh Compose database
- [x] PostgreSQL setup and database creation
- [x] Python virtual environment and dependencies installed
- [x] Project folder structure
- [x] `database.py` — database connection
- [x] Database schema — 14 tables
- [x] Seed script — master data and opening stock
- [x] Opening stock balances verified
- [x] FastAPI application entry point (`main.py`)
- [x] Database connection dependency (`dependencies.py`)
- [x] Authentication — login and JWT
- [x] Role-based access control (RBAC)
- [x] Inventory purchase API with idempotency (`client_request_id` + SHA-256)
- [x] Stock balance API
- [x] Stock ledger API with running balance (window function)
- [x] Shared inventory service — WAC retrieval and stock locking
- [x] Benchmark purchase: 60 kg flour @ ₹45, WAC = ₹43.125 ✅
- [x] BOM-based production run API (draft → post two-phase)
- [x] Raw material consumption recording
- [x] Finished goods output recording
- [x] Yield and material consumption variance calculation (threshold 3%)
- [x] Benchmark production run: 188 packets, oil +5% flagged, yield -6% flagged ✅
- [x] Sales order API (salesman/admin)
- [x] Admin order approval with stock check
- [x] GST invoice generation (CGST/SGST for TN, IGST for other states)
- [x] Invoice PDF generation (WeasyPrint)
- [x] Dispatch and finished goods stock deduction
- [x] Payment recording and outstanding balance update
- [x] Benchmark Retailer A: invoice ₹7,875, outstanding ₹3,875 ✅
- [x] Benchmark Distributor B: shortage 32 packets correctly blocked ✅
- [x] GET /sales/orders — order listing for admin/owner/auditor
- [x] Item classification validation (API layer + DB constraint)
  - RM- → raw, PK- → packaging, FG- → finished
- [x] React frontend — login, salesman dashboard, admin dashboard
- [x] Axios JWT interceptor and 401 auto-redirect
- [x] Excel export — stock ledger report, sales register with GST breakup
- [x] Docker Compose — parallel startup verified (PostgreSQL 5433, API 8001)

## In Progress
- [x] Production costing report — authenticated Excel download verified
- [x] GST summary report — authenticated Excel download verified

## Pending

### Reports
- [x] Purchase register report — authenticated Excel download verified
- [x] Outstanding and ageing report — authenticated Excel download verified
- [ ] Low-stock alerts

### Frontend
- [ ] Inventory management screens
- [ ] Production management screens
- [ ] Reports and dashboard screens

### Deployment and Submission
- [ ] Frontend-to-original-Docker integration — Vite proxy targets `localhost:8000`, while the original Compose API is on `localhost:8001`
- [ ] README — final setup instructions
- [ ] DESIGN_NOTE — finalize
- [ ] ASSUMPTIONS — finalize
- [ ] Demo video
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Vercel
