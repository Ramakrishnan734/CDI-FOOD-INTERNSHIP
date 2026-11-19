# CDI Food ERP — Development Log

## Day 1 — November 19, 2026

### Completed
- Verified existing project: venv, dependencies, database.py all working
- Reviewed and approved 14-table database schema
- Created `backend/app/models/schema.sql` — all 14 tables
- Created `backend/seed/seed.py` — benchmark master data + opening stock
- Ran seed script, verified all 6 opening balances match benchmark exactly

### Files created
- `backend/app/models/schema.sql`
- `backend/seed/seed.py`

### Verified balances
| Item        | Balance | Unit   |
|-------------|---------|--------|
| RM-FLOUR    | 100.000 | kg     |
| RM-OIL      |  30.000 | litre  |
| RM-SPICE    |   5.000 | kg     |
| PK-POUCH    | 500.000 | piece  |
| PK-CARTON   |  30.000 | piece  |
| FG-MRK200   |  50.000 | packet |

### Next
Day 2: FastAPI main.py, auth router, JWT login, RBAC middleware
