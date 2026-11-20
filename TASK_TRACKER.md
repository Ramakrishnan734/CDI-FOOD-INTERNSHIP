# CDI Food ERP — Task Tracker

## Completed

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
- [x] Inventory purchase API
- [x] Stock balance API
- [x] Purchase input validation
- [x] Purchase role authorization
- [x] Shared inventory service for stock locking and WAC retrieval
- [x] Invalid purchase requests tested
- [x] Database integrity verified after failed purchase requests
- [x] FastAPI Swagger documentation verified
- [x] Authentication and inventory endpoints verified in Swagger
- [x] Python dependencies checked using `pip check`
- [x] Purchase API validation tests passed
- [x] Failed purchase requests verified to leave the database unchanged
- [x] Database connection and transaction handling reviewed
- [x] Duplicate purchase request protection (idempotency)
- [x] Database migration for `client_request_id` and request hash
- [x] Benchmark purchase execution and WAC verification
- [x] BOM-based production run API
- [x] Raw material consumption recording
- [x] Finished goods production and stock update
- [x] Yield and material consumption variance calculation
## In Progress



## Pending

### Sales Management
- [ ] Sales order API (salesman/mobile)
- [ ] Admin order approval
- [ ] GST invoice generation and PDF
- [ ] Dispatch and finished goods stock deduction
- [ ] Partial dispatch and backorder handling

### Finance and Costing
- [ ] Payment recording
- [ ] Customer outstanding balance
- [ ] Production costing
- [ ] Cost per packet and profit margin calculation
- [ ] GST summary

### Inventory and Reports
- [ ] Stock ledger and inventory reports
- [ ] Sales reports
- [ ] Excel export
- [ ] Low-stock alerts

### Frontend
- [ ] React frontend setup
- [ ] Login and role-based dashboards
- [ ] Inventory management screens
- [ ] Production management screens
- [ ] Sales order and approval screens
- [ ] Reports and dashboard

### Deployment and Documentation
- [ ] Docker Compose
- [ ] README
- [ ] DESIGN_NOTE
- [ ] ASSUMPTIONS documentation
- [ ] Testing and bug fixes
- [ ] Deployment
- [ ] Demo video



