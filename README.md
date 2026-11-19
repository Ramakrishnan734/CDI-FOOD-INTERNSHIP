# CDI Food ERP

Order-to-Audit System for a Small South Indian Food Manufacturer
NIT Tiruchirappalli — CDI Software Developer Intern — Winter 2026

## Stack

- Backend: FastAPI + Python 3.14 + PostgreSQL 16
- Frontend: React + Vite + Tailwind CSS
- Auth: JWT with role-based access control
- DB access: SQLAlchemy Core (raw SQL, no ORM)

**Why this stack:** FastAPI gives automatic API docs and fast development.
PostgreSQL provides ACID transactions and NUMERIC arithmetic for correct
financial calculations. SQLAlchemy Core keeps SQL readable and explainable.

## Setup (local)

### Requirements
- Python 3.11+
- PostgreSQL 16
- Node.js 18+

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m seed.seed       # creates tables and loads benchmark data
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Test logins

| Role       | Email                  | Password   |
|------------|------------------------|------------|
| Admin      | admin@cdi.com          | admin123   |
| Salesman A | salesman_a@cdi.com     | sales123   |
| Salesman B | salesman_b@cdi.com     | sales123   |
| Production | prod@cdi.com           | prod123    |
| Auditor    | audit@cdi.com          | audit123   |
| Owner      | owner@cdi.com          | owner123   |

## Benchmark numbers

(To be filled after benchmark verification)

## Known gaps

(To be filled before submission)
