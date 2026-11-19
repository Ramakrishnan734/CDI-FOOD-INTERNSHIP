# CDI Food ERP — Assumptions

## Business assumptions

1. The factory state is always Tamil Nadu (state code: TN).
   GST type is determined by comparing seller state (TN) vs buyer state.
   Same state → CGST 2.5% + SGST 2.5%. Different state → IGST 5%.

2. Pouches consumed in a production run = good packets + damaged packets.
   Rationale: a damaged packet still consumed a pouch.

3. Cartons consumed = actual cartons used (entered manually), not derived from output.

4. Opening finished goods stock (50 packets Murukku) has no cost assigned (rate = 0).
   Only production runs generate costed finished goods.

5. Weighted Average Cost (WAC) is used for raw material valuation.
   WAC = (existing stock value + new purchase value) / (existing qty + new qty)

6. Overhead allocation: labour + gas/power costs are allocated entirely to the
   single production run they are entered against. No cross-run allocation.

7. Variance tolerance is 3%. Variances beyond ±3% are flagged.

8. Posted production runs and dispatched invoices cannot be deleted.
   Corrections require an adjustment entry or credit note.

9. Invoice numbering format: INV-FY2627-0001 (financial year 2026-27).

10. Salesman can only see their own orders. Admin sees all orders.

## Technical assumptions

1. Passwords are hashed with bcrypt in the backend. Seed data uses placeholder
   hashes — real hashing is applied at runtime via the auth service.

2. No Alembic migrations for now. Schema is managed via schema.sql.
   Re-running seed.py on a fresh database recreates everything correctly.

3. All money stored as NUMERIC(15,2) in the database. Python Decimal used
   throughout — no float arithmetic for financial calculations.
