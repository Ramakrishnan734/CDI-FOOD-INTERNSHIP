# backend/app/routers/inventory.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from pydantic import BaseModel
from decimal import Decimal
from datetime import date

from app.dependencies import get_db, require_role

router = APIRouter(prefix="/inventory", tags=["inventory"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class PurchaseLine(BaseModel):
    item_code: str
    qty: Decimal
    unit_rate: Decimal


class PurchaseRequest(BaseModel):
    supplier_name: str        # we look up by name for simplicity
    order_date: date
    lines: list[PurchaseLine]


# ------------------------------------------------------------------
# POST /inventory/purchase
# Roles: admin, production
# ------------------------------------------------------------------

@router.post("/purchase")
def create_purchase(
    body: PurchaseRequest,
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production"))
):
    with conn.begin():
        # 1. Resolve supplier
        supplier = conn.execute(
            text("SELECT id FROM suppliers WHERE name = :name"),
            {"name": body.supplier_name}
        ).fetchone()

        if supplier is None:
            raise HTTPException(status_code=404, detail=f"Supplier '{body.supplier_name}' not found")

        # 2. Create purchase order
        po = conn.execute(
            text("""
                INSERT INTO purchase_orders (supplier_id, order_date, created_by)
                VALUES (:supplier_id, :order_date, :user_id)
                RETURNING id
            """),
            {"supplier_id": supplier.id, "order_date": body.order_date, "user_id": user["sub"]}
        ).fetchone()
        po_id = po.id

        results = []

        for line in body.lines:
            # 3. Resolve item
            item = conn.execute(
                text("SELECT id, name, unit FROM items WHERE code = :code AND is_active = true"),
                {"code": line.item_code}
            ).fetchone()

            if item is None:
                raise HTTPException(status_code=404, detail=f"Item '{line.item_code}' not found")

            # 4. Insert purchase line
            conn.execute(
                text("""
                    INSERT INTO purchase_lines (po_id, item_id, qty, unit_rate)
                    VALUES (:po_id, :item_id, :qty, :rate)
                """),
                {"po_id": po_id, "item_id": item.id, "qty": line.qty, "rate": line.unit_rate}
            )

            # 5. Write stock ledger entry
            conn.execute(
                text("""
                    INSERT INTO stock_ledger
                        (item_id, movement_type, qty_in, qty_out, rate, ref_type, ref_id, created_by)
                    VALUES
                        (:item_id, 'purchase', :qty, 0, :rate, 'purchase_order', :po_id, :user_id)
                """),
                {
                    "item_id": item.id,
                    "qty": line.qty,
                    "rate": line.unit_rate,
                    "po_id": po_id,
                    "user_id": user["sub"]
                }
            )

            # 6. Compute new WAC for this item
            wac_row = conn.execute(
                text("""
                    SELECT
                        SUM(qty_in) - SUM(qty_out)              AS balance,
                        SUM(CASE WHEN qty_in > 0 THEN qty_in * rate ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN qty_in > 0 THEN qty_in ELSE 0 END), 0)
                                                                AS wac
                    FROM stock_ledger
                    WHERE item_id = :item_id
                """),
                {"item_id": item.id}
            ).fetchone()

            results.append({
                "item_code": line.item_code,
                "item_name": item.name,
                "qty_purchased": float(line.qty),
                "unit": item.unit,
                "unit_rate": float(line.unit_rate),
                "new_balance": float(wac_row.balance),
                "new_wac": round(float(wac_row.wac), 4)
            })

    return {
        "purchase_order_id": po_id,
        "lines": results
    }


# ------------------------------------------------------------------
# GET /inventory/balance
# All roles can read stock
# ------------------------------------------------------------------

@router.get("/balance")
def get_stock_balance(conn=Depends(get_db), user=Depends(require_role(
    "admin", "production", "salesman", "auditor", "owner"
))):
    rows = conn.execute(text("""
        SELECT
            i.code,
            i.name,
            i.unit,
            i.item_type,
            SUM(sl.qty_in) - SUM(sl.qty_out) AS balance
        FROM stock_ledger sl
        JOIN items i ON i.id = sl.item_id
        GROUP BY i.id, i.code, i.name, i.unit, i.item_type
        ORDER BY i.item_type, i.code
    """)).fetchall()

    return [
        {
            "code": r.code,
            "name": r.name,
            "unit": r.unit,
            "type": r.item_type,
            "balance": float(r.balance)
        }
        for r in rows
    ]