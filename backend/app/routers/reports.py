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
            CASE WHEN :production_only THEN NULL ELSE
                SUM(sl.qty_in - sl.qty_out) OVER (
                    PARTITION BY sl.item_id
                    ORDER BY
                        CASE WHEN sl.movement_type = 'opening' THEN 0 ELSE 1 END,
                        sl.created_at,
                        sl.id
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                )
            END AS running_balance
        FROM stock_ledger sl
        JOIN items i ON i.id = sl.item_id
        WHERE (
            :production_only = false
            OR (
                sl.movement_type IN ('production_issue', 'production_output')
                AND sl.ref_type = 'production_run'
            )
        )
        ORDER BY
            i.code,
            CASE WHEN sl.movement_type = 'opening' THEN 0 ELSE 1 END,
            sl.created_at,
            sl.id
    """), {"production_only": user["role"] == "production"}).fetchall()

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
        ws.cell(
            row=row_num,
            column=11,
            value=float(r.running_balance) if r.running_balance is not None else None,
        )

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
            so.status,
            u.name AS salesman_name
        FROM sales_orders so
        JOIN customers c ON c.id = so.customer_id
        JOIN users u ON u.id = so.salesman_id
        ORDER BY so.order_date, so.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Register"

    headers = [
        "Order No.", "Order Date", "Invoice No.", "Invoice Date",
        "Customer", "State", "GSTIN",
        "Taxable Value", "CGST", "SGST", "IGST",
        "Invoice Total", "Amount Paid", "Outstanding", "Status", "Salesman"
    ]
    widths = [18, 12, 18, 12, 20, 8, 18, 14, 10, 10, 10, 14, 12, 12, 12, 20]
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
        ws.cell(row=row_num, column=16, value=r.salesman_name)

    return _make_response(wb, f"sales_register_{date.today()}.xlsx")

# ------------------------------------------------------------------
# GET /reports/production-costing
# Production costing and indicative product margin report
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/production-costing")
def export_production_costing(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor")),
):
    rows = conn.execute(text("""
        WITH output_cost AS (
            SELECT
                sl.ref_id AS run_id,
                sl.item_id,
                SUM(sl.qty_in) AS output_qty,
                MAX(sl.rate) AS cost_per_packet
            FROM stock_ledger sl
            WHERE sl.movement_type = 'production_output'
              AND sl.ref_type = 'production_run'
            GROUP BY sl.ref_id, sl.item_id
        ),
        material_cost AS (
            SELECT
                sl.ref_id AS run_id,
                SUM(sl.qty_out * COALESCE(sl.rate, 0)) AS material_cost
            FROM stock_ledger sl
            WHERE sl.movement_type = 'production_issue'
              AND sl.ref_type = 'production_run'
            GROUP BY sl.ref_id
        ),
        selling_price AS (
            SELECT
                sol.item_id,
                SUM(sol.line_total) / NULLIF(SUM(sol.qty), 0)
                    AS average_selling_price
            FROM sales_order_lines sol
            JOIN sales_orders so ON so.id = sol.order_id
            WHERE so.invoice_number IS NOT NULL
            GROUP BY sol.item_id
        )
        SELECT
            pr.id AS run_id,
            pr.run_date,
            i.code AS item_code,
            i.name AS item_name,
            pr.planned_output,
            pr.actual_output,
            pr.damaged_qty,
            COALESCE(mc.material_cost, 0) AS material_cost,
            COALESCE(pr.labour_cost, 0) AS labour_cost,
            COALESCE(pr.overhead_cost, 0) AS overhead_cost,
            oc.cost_per_packet,
            sp.average_selling_price
        FROM production_runs pr
        JOIN bom_headers b ON b.id = pr.bom_id
        JOIN items i ON i.id = b.finished_item_id
        JOIN output_cost oc
          ON oc.run_id = pr.id
         AND oc.item_id = b.finished_item_id
        LEFT JOIN material_cost mc ON mc.run_id = pr.id
        LEFT JOIN selling_price sp ON sp.item_id = b.finished_item_id
        WHERE pr.status = 'posted'
        ORDER BY pr.run_date, pr.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Production Costing"

    headers = [
        "Run ID",
        "Run Date",
        "FG Code",
        "FG Name",
        "Planned Output",
        "Actual Output",
        "Yield Variance (Packets)",
        "Yield Variance (%)",
        "Damaged Qty",
        "Material Cost (₹)",
        "Labour Cost (₹)",
        "Overhead Cost (₹)",
        "Total Cost (₹)",
        "Cost per Packet (₹)",
        "Average Selling Price (₹)",
        "Gross Margin per Packet (₹)",
        "Gross Margin (%)",
    ]

    widths = [
        10, 14, 14, 22, 16, 16, 24, 20, 14,
        18, 18, 18, 18, 20, 24, 26, 18
    ]
    _header_row(ws, headers, widths)

    for row_num, r in enumerate(rows, 2):
        material_cost = float(r.material_cost or 0)
        labour_cost = float(r.labour_cost or 0)
        overhead_cost = float(r.overhead_cost or 0)

        total_cost = material_cost + labour_cost + overhead_cost
        planned_output = float(r.planned_output or 0)
        actual_output = float(r.actual_output or 0)

        yield_variance = actual_output - planned_output

        yield_variance_percent = (
            (yield_variance / planned_output) * 100
            if planned_output != 0
            else None
        )

        cost_per_packet = (
            float(r.cost_per_packet)
            if r.cost_per_packet is not None
            else None
        )

        average_selling_price = (
            float(r.average_selling_price)
            if r.average_selling_price is not None
            else None
        )

        # Margin is product-level and indicative, not batch-specific.
        gross_margin = None
        gross_margin_percent = None

        if cost_per_packet is not None and average_selling_price is not None:
            gross_margin = average_selling_price - cost_per_packet

            if average_selling_price != 0:
                gross_margin_percent = (
                    gross_margin / average_selling_price
                ) * 100

        values = [
            r.run_id,
            str(r.run_date),
            r.item_code,
            r.item_name,
            planned_output,
            actual_output,
            yield_variance,
            yield_variance_percent,
            float(r.damaged_qty or 0),
            material_cost,
            labour_cost,
            overhead_cost,
            total_cost,
            cost_per_packet,
            average_selling_price,
            gross_margin,
            gross_margin_percent,
        ]

        for col_num, value in enumerate(values, 1):
            ws.cell(row=row_num, column=col_num, value=value)

    return _make_response(
        wb,
        f"production_costing_{date.today()}.xlsx",
    )


# ------------------------------------------------------------------
# GET /reports/gst-summary
# GST summary grouped by invoice date
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/gst-summary")
def export_gst_summary(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor")),
):
    rows = conn.execute(text("""
        SELECT
            so.invoice_date,
            COUNT(DISTINCT so.invoice_number) AS invoice_count,
            COALESCE(SUM(so.taxable_value), 0) AS taxable_value,
            COALESCE(SUM(so.cgst_amount), 0) AS cgst_amount,
            COALESCE(SUM(so.sgst_amount), 0) AS sgst_amount,
            COALESCE(SUM(so.igst_amount), 0) AS igst_amount,
            COALESCE(
                SUM(
                    COALESCE(so.cgst_amount, 0)
                    + COALESCE(so.sgst_amount, 0)
                    + COALESCE(so.igst_amount, 0)
                ),
                0
            ) AS total_gst,
            COALESCE(SUM(so.invoice_total), 0) AS invoice_total
        FROM sales_orders so
        WHERE so.invoice_number IS NOT NULL
        GROUP BY so.invoice_date
        ORDER BY so.invoice_date
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "GST Summary"

    headers = [
        "Invoice Date",
        "Invoice Count",
        "Taxable Value (₹)",
        "CGST (₹)",
        "SGST (₹)",
        "IGST (₹)",
        "Total GST (₹)",
        "Invoice Total (₹)",
    ]

    widths = [16, 16, 22, 16, 16, 16, 20, 22]
    _header_row(ws, headers, widths)

    for row_num, r in enumerate(rows, 2):
        values = [
            str(r.invoice_date) if r.invoice_date else "",
            int(r.invoice_count or 0),
            float(r.taxable_value or 0),
            float(r.cgst_amount or 0),
            float(r.sgst_amount or 0),
            float(r.igst_amount or 0),
            float(r.total_gst or 0),
            float(r.invoice_total or 0),
        ]

        for col_num, value in enumerate(values, 1):
            ws.cell(row=row_num, column=col_num, value=value)

    return _make_response(
        wb,
        f"gst_summary_{date.today()}.xlsx",
    )


# ------------------------------------------------------------------
# GET /reports/purchases
# Purchase register export — posted purchase orders and line details
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/purchases")
def export_purchase_register(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor")),
):
    rows = conn.execute(text("""
        SELECT
            po.id AS purchase_order_id,
            po.order_date,
            s.name AS supplier_name,
            i.code AS item_code,
            i.name AS item_name,
            i.unit,
            pl.qty,
            pl.unit_rate,
            (pl.qty * pl.unit_rate) AS line_total
        FROM purchase_orders po
        JOIN purchase_lines pl ON pl.po_id = po.id
        JOIN items i ON i.id = pl.item_id
        LEFT JOIN suppliers s ON s.id = po.supplier_id
        WHERE po.status = 'posted'
        ORDER BY po.order_date, po.id, pl.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Purchase Register"

    headers = [
        "PO No.", "Purchase Date", "Supplier",
        "Item Code", "Item Name", "Unit",
        "Quantity", "Unit Rate (₹)", "Line Total (₹)",
    ]
    widths = [12, 15, 22, 14, 22, 10, 14, 16, 17]
    _header_row(ws, headers, widths)

    grand_total = Decimal("0")

    for row_num, r in enumerate(rows, 2):
        qty = Decimal(str(r.qty))
        rate = Decimal(str(r.unit_rate))
        line_total = qty * rate
        grand_total += line_total

        values = [
            r.purchase_order_id,
            str(r.order_date),
            r.supplier_name or "—",
            r.item_code,
            r.item_name,
            r.unit,
            float(qty),
            float(rate),
            float(line_total),
        ]

        for col_num, value in enumerate(values, 1):
            ws.cell(row=row_num, column=col_num, value=value)

    total_row = len(rows) + 2
    ws.cell(row=total_row, column=8, value="Grand Total")
    ws.cell(row=total_row, column=9, value=float(grand_total))
    ws.cell(row=total_row, column=8).font = Font(bold=True)
    ws.cell(row=total_row, column=9).font = Font(bold=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:I{len(rows) + 1}"

    return _make_response(wb, f"purchase_register_{date.today()}.xlsx")


# ------------------------------------------------------------------
# GET /reports/outstanding-ageing
# Outstanding invoice register with invoice-age buckets
# Roles: admin, owner, auditor
# ------------------------------------------------------------------

@router.get("/outstanding-ageing")
def export_outstanding_ageing(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor")),
):
    rows = conn.execute(text("""
        SELECT
            so.id AS order_id,
            so.order_number,
            so.invoice_number,
            so.invoice_date,
            c.name AS customer_name,
            c.contact AS customer_contact,
            so.invoice_total,
            so.amount_paid,
            COALESCE(so.outstanding, 0) AS outstanding,
            (CURRENT_DATE - so.invoice_date) AS age_days,
            CASE
                WHEN CURRENT_DATE - so.invoice_date <= 30 THEN '0-30 days'
                WHEN CURRENT_DATE - so.invoice_date <= 60 THEN '31-60 days'
                WHEN CURRENT_DATE - so.invoice_date <= 90 THEN '61-90 days'
                ELSE '90+ days'
            END AS age_bucket
        FROM sales_orders so
        JOIN customers c ON c.id = so.customer_id
        WHERE so.status = 'dispatched'
          AND so.invoice_number IS NOT NULL
          AND so.invoice_date IS NOT NULL
          AND COALESCE(so.outstanding, 0) > 0
        ORDER BY so.invoice_date, so.id
    """)).fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Outstanding Ageing"

    headers = [
        "Order No.", "Invoice No.", "Invoice Date",
        "Customer", "Contact", "Invoice Total (₹)",
        "Amount Paid (₹)", "Outstanding (₹)",
        "Invoice Age (Days)", "Age Bucket",
    ]
    widths = [16, 18, 15, 24, 18, 20, 20, 20, 20, 16]
    _header_row(ws, headers, widths)

    total_invoice = Decimal("0")
    total_paid = Decimal("0")
    total_outstanding = Decimal("0")

    for row_num, r in enumerate(rows, 2):
        invoice_total = Decimal(str(r.invoice_total or 0))
        amount_paid = Decimal(str(r.amount_paid or 0))
        outstanding = Decimal(str(r.outstanding or 0))

        total_invoice += invoice_total
        total_paid += amount_paid
        total_outstanding += outstanding

        values = [
            r.order_number,
            r.invoice_number,
            str(r.invoice_date),
            r.customer_name,
            r.customer_contact or "—",
            float(invoice_total),
            float(amount_paid),
            float(outstanding),
            int(r.age_days),
            r.age_bucket,
        ]

        for col_num, value in enumerate(values, 1):
            ws.cell(row=row_num, column=col_num, value=value)

    total_row = len(rows) + 2
    ws.cell(row=total_row, column=5, value="Grand Total")
    ws.cell(row=total_row, column=6, value=float(total_invoice))
    ws.cell(row=total_row, column=7, value=float(total_paid))
    ws.cell(row=total_row, column=8, value=float(total_outstanding))

    for col_num in range(5, 9):
        ws.cell(row=total_row, column=col_num).font = Font(bold=True)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:J{len(rows) + 1}"

    return _make_response(
        wb,
        f"outstanding_ageing_{date.today()}.xlsx",
    )
