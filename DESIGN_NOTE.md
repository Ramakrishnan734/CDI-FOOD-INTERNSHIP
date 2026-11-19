# CDI Food ERP — Design Note

## 1. Data Model Summary

14 tables across 6 groups:

| Group       | Tables |
|-------------|--------|
| Masters     | users, items, customers, suppliers |
| BOM         | bom_headers, bom_lines |
| Inventory   | stock_ledger |
| Purchasing  | purchase_orders, purchase_lines |
| Production  | production_runs, production_lines |
| Sales       | sales_orders, sales_order_lines, payments |

## 2. Stock Ledger Design

The stock_ledger table is the single source of truth for all inventory balances.
No table stores a running balance. Balance is always computed as:

    SELECT SUM(qty_in) - SUM(qty_out) FROM stock_ledger WHERE item_id = X

Every movement row carries: item_id, movement_type, qty_in or qty_out, rate,
and a ref_type + ref_id pointing back to the source document.

Movement types: opening, purchase, production_issue, production_output,
sale_dispatch, adjustment.

## 3. BOM Consumption Logic

When a production run is posted:
1. The active BOM lines are read and snapshotted into production_lines
   (planned_qty = BOM qty_per_batch for the batch size).
2. Actual quantities entered by the supervisor are stored as actual_qty.
3. Stock ledger rows are written:
   - qty_out for each raw/packaging material (actual_qty consumed)
   - qty_in for the finished good (actual_output packets)
4. Variance = (actual_qty - planned_qty) / planned_qty * 100
   Flagged if abs(variance) > 3%.

## 4. Weighted Average Cost (WAC)

On each purchase:
  new_wac = (current_balance * current_wac + purchase_qty * purchase_rate)
            / (current_balance + purchase_qty)

This new_wac is stored on the stock_ledger row and used in costing.

For the benchmark:
  Flour opening: 100 kg @ ₹42 = ₹4,200
  Flour purchase: 60 kg @ ₹45 = ₹2,700
  WAC = (4200 + 2700) / (100 + 60) = ₹43.125/kg

## 5. GST Logic

Seller state: Tamil Nadu (TN, code 33)
  Buyer in TN → CGST 2.5% + SGST 2.5%
  Buyer outside TN → IGST 5%

Determined by comparing customers.state_code with seller state at invoice time.

## 6. Technology Stack

- Backend: FastAPI + Python 3.14
- Database: PostgreSQL 16 with SQLAlchemy Core (raw SQL, no ORM)
- Frontend: React + Vite + Tailwind CSS + shadcn/ui
- Auth: JWT (python-jose + bcrypt)
- PDF: WeasyPrint
- Excel: openpyxl
- Deployment: Railway (backend) + Vercel (frontend)
