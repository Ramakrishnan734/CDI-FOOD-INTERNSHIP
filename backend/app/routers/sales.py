# backend/app/routers/sales.py

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.dependencies import get_db, require_role

router = APIRouter(prefix="/sales", tags=["sales"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class SalesOrderLine(BaseModel):
    item_code: str = Field(min_length=1, max_length=20)
    qty: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    unit_price: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class CreateSalesOrderRequest(BaseModel):
    customer_id: int
    order_date: date
    lines: list[SalesOrderLine] = Field(min_length=1)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _generate_order_number(conn, order_date: date) -> str:
    date_str = order_date.strftime("%Y%m%d")
    prefix = f"ORD-{date_str}-"
    count = conn.execute(
        text("SELECT COUNT(*) FROM sales_orders WHERE order_number LIKE :prefix"),
        {"prefix": prefix + "%"},
    ).scalar()
    return f"{prefix}{int(count) + 1:04d}"


# ------------------------------------------------------------------
# POST /sales/order
# Roles: salesman, admin
# ------------------------------------------------------------------

@router.post("/order", status_code=201)
def create_sales_order(
    body: CreateSalesOrderRequest,
    conn=Depends(get_db),
    user=Depends(require_role("salesman", "admin")),
):
    user_id = int(user["sub"])

    with conn.begin():

        # 1. Validate customer
        customer = conn.execute(
            text("""
                SELECT id, name, state_code
                FROM customers
                WHERE id = :cid AND is_active = true
            """),
            {"cid": body.customer_id},
        ).fetchone()

        if customer is None:
            raise HTTPException(
                status_code=404,
                detail=f"Customer {body.customer_id} not found or inactive",
            )

        # 2. Validate line items
        resolved_lines = []
        for line in body.lines:
            item = conn.execute(
                text("""
                    SELECT id, code, name, unit, item_type
                    FROM items
                    WHERE code = :code AND is_active = true
                """),
                {"code": line.item_code},
            ).fetchone()

            if item is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Item '{line.item_code}' not found or inactive",
                )
            if item.item_type != "finished":
                raise HTTPException(
                    status_code=422,
                    detail=f"Item '{line.item_code}' is a {item.item_type} item. Only finished goods can be sold.",
                )
            resolved_lines.append((line, item))

        # 3. Generate order number
        order_number = _generate_order_number(conn, body.order_date)

        # 4. Insert sales order header
        order_id = conn.execute(
            text("""
                INSERT INTO sales_orders
                    (order_number, customer_id, salesman_id, order_date, status)
                VALUES
                    (:order_number, :customer_id, :salesman_id, :order_date, 'pending')
                RETURNING id
            """),
            {
                "order_number": order_number,
                "customer_id": customer.id,
                "salesman_id": user_id,
                "order_date": body.order_date,
            },
        ).scalar_one()

        # 5. Insert order lines
        result_lines = []
        order_total = Decimal("0")

        for line, item in resolved_lines:
            line_total = (line.qty * line.unit_price).quantize(Decimal("0.01"))
            order_total += line_total

            conn.execute(
                text("""
                    INSERT INTO sales_order_lines
                        (order_id, item_id, qty, unit_price, line_total)
                    VALUES
                        (:order_id, :item_id, :qty, :unit_price, :line_total)
                """),
                {
                    "order_id": order_id,
                    "item_id": item.id,
                    "qty": line.qty,
                    "unit_price": line.unit_price,
                    "line_total": line_total,
                },
            )

            result_lines.append({
                "item_code": item.code,
                "item_name": item.name,
                "unit": item.unit,
                "qty": str(line.qty),
                "unit_price": str(line.unit_price),
                "line_total": str(line_total),
            })

    return {
        "order_id": order_id,
        "order_number": order_number,
        "customer_name": customer.name,
        "customer_state": customer.state_code,
        "order_date": str(body.order_date),
        "status": "pending",
        "taxable_value": str(order_total),
        "lines": result_lines,
    }
