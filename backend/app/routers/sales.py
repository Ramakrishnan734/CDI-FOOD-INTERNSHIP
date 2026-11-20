# backend/app/routers/sales.py

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.dependencies import get_db, require_role
from app.services.inventory_service import get_balance_and_wac

router = APIRouter(prefix="/sales", tags=["sales"])

SELLER_STATE = "TN"
CGST_RATE = Decimal("2.5")
SGST_RATE = Decimal("2.5")
IGST_RATE = Decimal("5.0")


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


def _generate_invoice_number(conn) -> str:
    count = conn.execute(
        text("SELECT COUNT(*) FROM sales_orders WHERE invoice_number IS NOT NULL")
    ).scalar()
    return f"INV-FY2627-{int(count) + 1:04d}"


def _calculate_gst(taxable_value: Decimal, customer_state: str) -> dict:
    if customer_state == SELLER_STATE:
        cgst = (taxable_value * CGST_RATE / 100).quantize(Decimal("0.01"))
        sgst = (taxable_value * SGST_RATE / 100).quantize(Decimal("0.01"))
        igst = Decimal("0.00")
    else:
        cgst = Decimal("0.00")
        sgst = Decimal("0.00")
        igst = (taxable_value * IGST_RATE / 100).quantize(Decimal("0.01"))
    return {
        "cgst_amount": cgst,
        "sgst_amount": sgst,
        "igst_amount": igst,
        "invoice_total": taxable_value + cgst + sgst + igst,
    }


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

        order_number = _generate_order_number(conn, body.order_date)

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


# ------------------------------------------------------------------
# POST /sales/{order_id}/approve
# Role: admin only
# ------------------------------------------------------------------

@router.post("/{order_id}/approve", status_code=200)
def approve_sales_order(
    order_id: int,
    conn=Depends(get_db),
    user=Depends(require_role("admin")),
):
    with conn.begin():

        order = conn.execute(
            text("""
                SELECT so.id, so.status, so.order_number,
                       c.name AS customer_name, c.state_code
                FROM sales_orders so
                JOIN customers c ON c.id = so.customer_id
                WHERE so.id = :order_id
            """),
            {"order_id": order_id},
        ).fetchone()

        if order is None:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
        if order.status != "pending":
            raise HTTPException(
                status_code=409,
                detail=f"Order {order_id} is '{order.status}' and cannot be approved",
            )

        lines = conn.execute(
            text("""
                SELECT sol.item_id, sol.qty, sol.unit_price, sol.line_total,
                       i.code, i.name
                FROM sales_order_lines sol
                JOIN items i ON i.id = sol.item_id
                WHERE sol.order_id = :order_id
            """),
            {"order_id": order_id},
        ).fetchall()

        for line in lines:
            balance, _ = get_balance_and_wac(conn, line.item_id)
            if balance < Decimal(str(line.qty)):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Insufficient stock for '{line.code}': "
                        f"need {line.qty}, have {balance}"
                    ),
                )

        taxable_value = sum(Decimal(str(l.line_total)) for l in lines)
        gst = _calculate_gst(taxable_value, order.state_code)
        invoice_number = _generate_invoice_number(conn)
        invoice_date = date.today()

        conn.execute(
            text("""
                UPDATE sales_orders SET
                    status         = 'approved',
                    approved_by    = :user_id,
                    approved_at    = now(),
                    invoice_number = :invoice_number,
                    invoice_date   = :invoice_date,
                    taxable_value  = :taxable_value,
                    cgst_amount    = :cgst_amount,
                    sgst_amount    = :sgst_amount,
                    igst_amount    = :igst_amount,
                    invoice_total  = :invoice_total,
                    outstanding    = :invoice_total
                WHERE id = :order_id
            """),
            {
                "user_id": int(user["sub"]),
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "taxable_value": taxable_value,
                "cgst_amount": gst["cgst_amount"],
                "sgst_amount": gst["sgst_amount"],
                "igst_amount": gst["igst_amount"],
                "invoice_total": gst["invoice_total"],
                "order_id": order_id,
            },
        )

    return {
        "order_id": order_id,
        "order_number": order.order_number,
        "status": "approved",
        "customer_name": order.customer_name,
        "customer_state": order.state_code,
        "invoice_number": invoice_number,
        "invoice_date": str(invoice_date),
        "taxable_value": str(taxable_value),
        "cgst_amount": str(gst["cgst_amount"]),
        "sgst_amount": str(gst["sgst_amount"]),
        "igst_amount": str(gst["igst_amount"]),
        "invoice_total": str(gst["invoice_total"]),
        "outstanding": str(gst["invoice_total"]),
    }
