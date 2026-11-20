# backend/app/routers/reports.py

import io
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from app.dependencies import get_db, require_role

router = APIRouter(prefix="/reports", tags=["reports"])


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _header_row(ws, headers, col_widths):
    """Write a styled header row to the worksheet."""
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E79")

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=col).column_letter].width = width


def _make_response(wb, filename):
    """Convert workbook to streaming HTTP response."""
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


# ------------------------------------------------------------------
# GET /reports/stock
# Stock ledger export — all items, all movements
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/stock")
def export_stock_ledger(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor", "production")),
):
    rows = conn.execute(text("""
        SELECT
            i.code,
            i.name,
            i.unit,
            sl.movement_type,
            sl.qty_in,
            sl.qty_out,
            sl.rate,
            sl.ref_type,
            sl.ref_id,
            sl.created_at,
            SUM(sl.qty_in - sl.qty_out) OVER (
                PARTITION BY sl.item_id
                ORDER BY sl.created_at, sl.id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_balance
        FROM stock_ledger sl
        JOIN items i ON i.id = sl.item_id
        ORDER BY i.code, sl.created_at, sl.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Ledger"

    headers = ["Item Code", "Item Name", "Unit", "Movement Type",
               "Qty In", "Qty Out", "Rate (₹)", "Ref Type", "Ref ID",
               "Date", "Running Balance"]
    widths = [12, 20, 8, 18, 10, 10, 12, 16, 8, 18, 16]
    _header_row(ws, headers, widths)

    for row_num, r in enumerate(rows, 2):
        ws.cell(row=row_num, column=1, value=r.code)
        ws.cell(row=row_num, column=2, value=r.name)
        ws.cell(row=row_num, column=3, value=r.unit)
        ws.cell(row=row_num, column=4, value=r.movement_type)
        ws.cell(row=row_num, column=5, value=float(r.qty_in))
        ws.cell(row=row_num, column=6, value=float(r.qty_out))
        ws.cell(row=row_num, column=7, value=float(r.rate) if r.rate else 0)
        ws.cell(row=row_num, column=8, value=r.ref_type)
        ws.cell(row=row_num, column=9, value=r.ref_id)
        ws.cell(row=row_num, column=10, value=r.created_at.strftime("%Y-%m-%d %H:%M"))
        ws.cell(row=row_num, column=11, value=float(r.running_balance))

    return _make_response(wb, f"stock_ledger_{date.today()}.xlsx")


# ------------------------------------------------------------------
# GET /reports/sales
# Sales register export
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/sales")
def export_sales_register(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor")),
):
    rows = conn.execute(text("""
        SELECT
            so.order_number,
            so.order_date,
            so.invoice_number,
            so.invoice_date,
            c.name        AS customer_name,
            c.state_code  AS customer_state,
            c.gstin       AS customer_gstin,
            so.taxable_value,
            so.cgst_amount,
            so.sgst_amount,
            so.igst_amount,
            so.invoice_total,
            so.amount_paid,
            so.outstanding,
            so.status
        FROM sales_orders so
        JOIN customers c ON c.id = so.customer_id
        ORDER BY so.order_date, so.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Register"

    headers = [
        "Order No.", "Order Date", "Invoice No.", "Invoice Date",
        "Customer", "State", "GSTIN",
        "Taxable Value", "CGST", "SGST", "IGST",
        "Invoice Total", "Amount Paid", "Outstanding", "Status"
    ]
    widths = [18, 12, 18, 12, 20, 8, 18, 14, 10, 10, 10, 14, 12, 12, 12]
    _header_row(ws, headers, widths)

    for row_num, r in enumerate(rows, 2):
        ws.cell(row=row_num, column=1, value=r.order_number)
        ws.cell(row=row_num, column=2, value=str(r.order_date))
        ws.cell(row=row_num, column=3, value=r.invoice_number or "—")
        ws.cell(row=row_num, column=4, value=str(r.invoice_date) if r.invoice_date else "—")
        ws.cell(row=row_num, column=5, value=r.customer_name)
        ws.cell(row=row_num, column=6, value=r.customer_state)
        ws.cell(row=row_num, column=7, value=r.customer_gstin or "—")
        ws.cell(row=row_num, column=8, value=float(r.taxable_value) if r.taxable_value else 0)
        ws.cell(row=row_num, column=9, value=float(r.cgst_amount) if r.cgst_amount else 0)
        ws.cell(row=row_num, column=10, value=float(r.sgst_amount) if r.sgst_amount else 0)
        ws.cell(row=row_num, column=11, value=float(r.igst_amount) if r.igst_amount else 0)
        ws.cell(row=row_num, column=12, value=float(r.invoice_total) if r.invoice_total else 0)
        ws.cell(row=row_num, column=13, value=float(r.amount_paid) if r.amount_paid else 0)
        ws.cell(row=row_num, column=14, value=float(r.outstanding) if r.outstanding else 0)
        ws.cell(row=row_num, column=15, value=r.status)

    return _make_response(wb, f"sales_register_{date.today()}.xlsx")