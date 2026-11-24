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

8. The API exposes no delete endpoints for posted production runs or dispatched
   invoices. A database-enforced correction, adjustment, or credit-note workflow
   is not implemented.

9. Invoice numbering format: INV-FY2627-0001 (financial year 2026-27).

10. Salesman order history is not implemented. The only order-list endpoint is
    available to admin, owner, and auditor roles; admin can see all orders.

## Technical assumptions

1. Passwords are hashed with bcrypt. The seed script generates bcrypt hashes
   when it runs.

2. No Alembic migrations are used. `schema.sql` is the fresh-schema source of
   truth and includes the purchase-idempotency columns required by the API.
   The seed script is intended for a fresh database and is not a repeatable
   reset procedure.

3. Monetary rates and inventory valuation use NUMERIC(15,4); invoice and
   payment totals use NUMERIC(15,2). Python Decimal is used in financial
   calculations; report exports convert values to floats for Excel output.

11. Item code prefixes are enforced to match item_type:
    RM- → raw, PK- → packaging, FG- → finished.
    Enforced at both API layer and database constraint level.
    The current database constraint requires one of these recognised prefixes.
    The API validation allows an unknown prefix through, but the database rejects
    it; unknown-prefix items therefore cannot be created.

12. Purchase API is idempotent: a client_request_id + SHA-256 payload hash
    prevents duplicate purchase orders on network retry.
    Same ID + same payload → returns original result (200).
    Same ID + different payload → rejected (409).
    The required columns are included in the checked-in fresh schema and the
    behavior was verified against an isolated fresh Compose database.
