# backend/app/services/pdf_service.py

import os
from decimal import Decimal
from weasyprint import HTML


TEMPLATE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "templates", "invoice.html"
)


def _load_template() -> str:
    with open(TEMPLATE_PATH, "r") as f:
        return f.read()


def generate_invoice_pdf(order: dict) -> bytes:
    """
    Accepts an order dict and returns PDF bytes.
    """
    template = _load_template()

    # Build line rows HTML
    line_rows = ""
    for i, line in enumerate(order["lines"], 1):
        line_rows += f"""
        <tr>
            <td>{i}</td>
            <td>{line['item_name']}</td>
            <td>{line['hsn_code'] or '—'}</td>
            <td class="right">{line['qty']}</td>
            <td>{line['unit']}</td>
            <td class="right">{line['unit_price']}</td>
            <td class="right">{line['line_total']}</td>
        </tr>
        """

    # Build GST rows HTML
    if order["igst_amount"] and Decimal(order["igst_amount"]) > 0:
        gst_type = "Inter-State Supply (IGST)"
        gst_rows = f"<tr><td>IGST @ 5%</td><td class='right'>₹ {order['igst_amount']}</td></tr>"
    else:
        gst_type = "Intra-State Supply (CGST + SGST)"
        gst_rows = f"""
        <tr><td>CGST @ 2.5%</td><td class='right'>₹ {order['cgst_amount']}</td></tr>
        <tr><td>SGST @ 2.5%</td><td class='right'>₹ {order['sgst_amount']}</td></tr>
        """

    # Fill template
    html = template \
        .replace("{{invoice_number}}", order["invoice_number"]) \
        .replace("{{invoice_date}}", order["invoice_date"]) \
        .replace("{{order_number}}", order["order_number"]) \
        .replace("{{customer_name}}", order["customer_name"]) \
        .replace("{{customer_state}}", order["customer_state"]) \
        .replace("{{customer_gstin}}", order["customer_gstin"] or "—") \
        .replace("{{gst_type}}", gst_type) \
        .replace("{{line_rows}}", line_rows) \
        .replace("{{gst_rows}}", gst_rows) \
        .replace("{{taxable_value}}", order["taxable_value"]) \
        .replace("{{invoice_total}}", order["invoice_total"]) \
        .replace("{{amount_paid}}", order["amount_paid"]) \
        .replace("{{outstanding}}", order["outstanding"])

    return HTML(string=html).write_pdf()