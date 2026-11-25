# backend/app/routers/inventory.py

import hashlib
import json
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.dependencies import get_db, require_role
from app.services.inventory_service import get_balance_and_wac, lock_items

router = APIRouter(prefix="/inventory", tags=["inventory"])

PURCHASABLE_TYPES = ("raw", "packaging")


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class PurchaseLine(BaseModel):
    item_code: str = Field(min_length=1, max_length=20)
    qty: Decimal = Field(gt=0, max_digits=12, decimal_places=4)
    unit_rate: Decimal = Field(gt=0, max_digits=15, decimal_places=4)


class PurchaseRequest(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=100)
    supplier_name: str = Field(min_length=1, max_length=100)
    order_date: date
    lines: list[PurchaseLine] = Field(min_length=1)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _compute_request_hash(body: PurchaseRequest) -> str:
    """
    Deterministic SHA-256 of the purchase payload.

    Rules:
    - Lines are sorted by item_code so order does not affect the hash.
    - Decimal values are serialised as strings to avoid float imprecision.
    - supplier_name and order_date are included; client_request_id is NOT
      (the hash represents the payload, independent of the ID).
    """
    canonical = {
        "supplier_name": body.supplier_name,
        "order_date": body.order_date.isoformat(),
        "lines": sorted(
            [
                {
                    "item_code": line.item_code,
                    "qty": str(line.qty),
                    "unit_rate": str(line.unit_rate),
                }
                for line in body.lines
            ],
            key=lambda x: x["item_code"],
        ),
    }
    payload_bytes = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload_bytes).hexdigest()


def _fetch_original_result(conn, po_id: int) -> dict:
    """
    Re-constructs the purchase response from existing database rows.
    Used when returning a replayed idempotent response.
    """
    lines = conn.execute(
        text("""
            SELECT
                i.code        AS item_code,
                i.name        AS item_name,
                i.unit        AS unit,
                pl.qty        AS qty_purchased,
                pl.unit_rate  AS unit_rate
            FROM purchase_lines pl
            JOIN items i ON i.id = pl.item_id
            WHERE pl.po_id = :po_id
            ORDER BY pl.id
        """),
        {"po_id": po_id},
    ).fetchall()

    result_lines = []
    for row in lines:
        balance, wac = get_balance_and_wac(conn, _item_id_for_po_line(conn, po_id, row.item_code))
        result_lines.append({
            "item_code": row.item_code,
            "item_name": row.item_name,
            "unit": row.unit,
            "qty_purchased": str(row.qty_purchased),
            "unit_rate": str(row.unit_rate),
            "new_balance": str(balance),
            "new_wac": str(wac),
        })

    return {"purchase_order_id": po_id, "lines": result_lines}


def _item_id_for_po_line(conn, po_id: int, item_code: str) -> int:
    return conn.execute(
        text("""
            SELECT i.id
            FROM purchase_lines pl
            JOIN items i ON i.id = pl.item_id
            WHERE pl.po_id = :po_id AND i.code = :code
        """),
        {"po_id": po_id, "code": item_code},
    ).scalar_one()


# ------------------------------------------------------------------
# POST /inventory/purchase
# Roles: admin, production
# ------------------------------------------------------------------

@router.post("/purchase", status_code=201)
def create_purchase(
    body: PurchaseRequest,
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production")),
):
    user_id = int(user["sub"])
    request_hash = _compute_request_hash(body)

    with conn.begin():

        # ── Idempotency check ──────────────────────────────────────────
        # Must happen inside the transaction and before any writes so that
        # the UNIQUE index on client_request_id protects the race window.
        existing = conn.execute(
            text("""
                SELECT id, request_hash
                FROM purchase_orders
                WHERE client_request_id = :crid
            """),
            {"crid": body.client_request_id},
        ).fetchone()

        if existing is not None:
            if existing.request_hash == request_hash:
                # Safe replay: same ID, same payload. Return original result.
                # HTTP 200 (not 201) signals "already existed".
                from fastapi.responses import JSONResponse
                result = _fetch_original_result(conn, existing.id)
                return JSONResponse(status_code=200, content=result)
            else:
                # Same ID, different payload — this is a client error.
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"client_request_id '{body.client_request_id}' was already used "
                        f"with a different payload. Use a new client_request_id for a "
                        f"different purchase."
                    ),
                )

        # ── Supplier validation ────────────────────────────────────────
        suppliers = conn.execute(
            text("SELECT id FROM suppliers WHERE name = :name AND is_active = true"),
            {"name": body.supplier_name},
        ).fetchall()

        if not suppliers:
            raise HTTPException(
                status_code=404,
                detail=f"Supplier '{body.supplier_name}' not found or inactive",
            )
        if len(suppliers) > 1:
            raise HTTPException(
                status_code=409,
                detail=f"Supplier name '{body.supplier_name}' is ambiguous",
            )
        supplier_id = suppliers[0].id

        # ── Item validation ────────────────────────────────────────────
        resolved = []
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
            if item.item_type not in PURCHASABLE_TYPES:
                raise HTTPException(
                    status_code=422,
                    detail=f"Item '{line.item_code}' is a {item.item_type} item "
                           f"and cannot be purchased",
                )
            resolved.append((line, item))

        # ── Row locking ────────────────────────────────────────────────
        lock_items(conn, [item.id for _, item in resolved])

        # ── Create purchase order ──────────────────────────────────────
        # Both idempotency columns are written here. If a concurrent request
        # with the same client_request_id races past the SELECT above and
        # reaches this INSERT, the UNIQUE index will raise an IntegrityError
        # and the transaction rolls back cleanly.
        po_id = conn.execute(
            text("""
                INSERT INTO purchase_orders
                    (supplier_id, order_date, created_by,
                     client_request_id, request_hash)
                VALUES
                    (:supplier_id, :order_date, :user_id,
                     :crid, :rhash)
                RETURNING id
            """),
            {
                "supplier_id": supplier_id,
                "order_date": body.order_date,
                "user_id": user_id,
                "crid": body.client_request_id,
                "rhash": request_hash,
            },
        ).scalar_one()

        # ── Purchase lines + ledger ────────────────────────────────────
        results = []
        for line, item in resolved:
            conn.execute(
                text("""
                    INSERT INTO purchase_lines (po_id, item_id, qty, unit_rate)
                    VALUES (:po_id, :item_id, :qty, :rate)
                """),
                {"po_id": po_id, "item_id": item.id,
                 "qty": line.qty, "rate": line.unit_rate},
            )

            conn.execute(
                text("""
                    INSERT INTO stock_ledger
                        (item_id, movement_type, qty_in, qty_out, rate,
                         ref_type, ref_id, created_by)
                    VALUES
                        (:item_id, 'purchase', :qty, 0, :rate,
                         'purchase_order', :po_id, :user_id)
                """),
                {"item_id": item.id, "qty": line.qty, "rate": line.unit_rate,
                 "po_id": po_id, "user_id": user_id},
            )

            balance, wac = get_balance_and_wac(conn, item.id)
            results.append({
                "item_code": item.code,
                "item_name": item.name,
                "unit": item.unit,
                "qty_purchased": str(line.qty),
                "unit_rate": str(line.unit_rate),
                "new_balance": str(balance),
                "new_wac": str(wac),
            })

    return {"purchase_order_id": po_id, "lines": results}


# ------------------------------------------------------------------
# GET /inventory/balance
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
            "balance": str(Decimal(str(r.balance)))  # fixed: was float()
        }
        for r in rows
    ]

# ------------------------------------------------------------------
# GET /inventory/ledger?item_code=XX
# All roles
# ------------------------------------------------------------------

@router.get("/ledger")
def get_stock_ledger(
    item_code: str,
    conn=Depends(get_db),
    user=Depends(require_role("admin", "owner", "auditor", "production", "salesman")),
):
    # Validate item exists
    item = conn.execute(
        text("SELECT id, code, name, unit FROM items WHERE code = :code AND is_active = true"),
        {"code": item_code},
    ).fetchone()

    if item is None:
        raise HTTPException(status_code=404, detail=f"Item '{item_code}' not found")

    rows = conn.execute(
        text("""
            SELECT
                sl.id,
                sl.created_at,
                sl.movement_type,
                sl.qty_in,
                sl.qty_out,
                sl.rate,
                sl.ref_type,
                sl.ref_id,
                sl.notes,
                SUM(sl.qty_in - sl.qty_out) OVER (
                ORDER BY
                    CASE WHEN sl.movement_type = 'opening' THEN 0 ELSE 1 END,
                    sl.created_at,
                    sl.id
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_balance
            FROM stock_ledger sl
            WHERE sl.item_id = :item_id
            ORDER BY
                CASE WHEN sl.movement_type = 'opening' THEN 0 ELSE 1 END,
                sl.created_at,
                sl.id
        """),
        {"item_id": item.id},
    ).fetchall()

    return {
        "item_code": item.code,
        "item_name": item.name,
        "unit": item.unit,
        "movements": [
            {
                "id": r.id,
                "date": r.created_at.strftime("%Y-%m-%d %H:%M"),
                "movement_type": r.movement_type,
                "qty_in": str(r.qty_in),
                "qty_out": str(r.qty_out),
                "rate": str(r.rate) if r.rate is not None else None,
                "ref_type": r.ref_type,
                "ref_id": r.ref_id,
                "notes": r.notes,
                "running_balance": str(r.running_balance),
            }
            for r in rows
        ],
    }

# ------------------------------------------------------------------
# Item code → type validation
# ------------------------------------------------------------------

PREFIX_TYPE_MAP = {
    "RM-": "raw",
    "PK-": "packaging",
    "FG-": "finished",
}


def validate_item_code_type(code: str, item_type: str):
    """
    Enforces that item code prefix matches item_type.
    RM- → raw | PK- → packaging | FG- → finished
    Raises HTTPException 422 on mismatch.
    """
    for prefix, expected_type in PREFIX_TYPE_MAP.items():
        if code.upper().startswith(prefix):
            if item_type != expected_type:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Item code '{code}' starts with '{prefix}' "
                        f"and must be classified as '{expected_type}', "
                        f"not '{item_type}'."
                    ),
                )
            return  # prefix matched and type is correct
    # No known prefix — still allow, but warn in the future if needed
    # For now: unrecognised prefixes pass through (they don't exist in this system)


# ------------------------------------------------------------------
# POST /inventory/items
# Roles: admin only
# ------------------------------------------------------------------

class CreateItemRequest(BaseModel):
    code: str
    name: str
    item_type: str
    unit: str
    hsn_code: str = ""


@router.post("/items", status_code=201)
def create_item(
    body: CreateItemRequest,
    conn=Depends(get_db),
    user=Depends(require_role("admin")),
):
    # API-layer prefix/type validation
    validate_item_code_type(body.code, body.item_type)

    if body.item_type not in ("raw", "packaging", "finished"):
        raise HTTPException(status_code=422, detail="item_type must be raw, packaging, or finished")

    with conn.begin():
        try:
            item_id = conn.execute(
                text("""
                    INSERT INTO items (code, name, item_type, unit, hsn_code)
                    VALUES (:code, :name, :item_type, :unit, :hsn_code)
                    RETURNING id
                """),
                {
                    "code": body.code.upper(),
                    "name": body.name,
                    "item_type": body.item_type,
                    "unit": body.unit,
                    "hsn_code": body.hsn_code or None,
                },
            ).scalar_one()
        except Exception as e:
            if "chk_item_code_type_match" in str(e):
                # DB constraint caught it (e.g. direct insert bypassing API)
                raise HTTPException(
                    status_code=422,
                    detail=f"Item code prefix does not match item_type '{body.item_type}'."
                )
            if "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"Item code '{body.code}' already exists.")
            raise

    return {"item_id": item_id, "code": body.code.upper(), "name": body.name, "item_type": body.item_type}


# ------------------------------------------------------------------
# GET /inventory/items
# All authenticated roles
# ------------------------------------------------------------------

@router.get("/items")
def list_items(conn=Depends(get_db), user=Depends(require_role(
    "admin", "production", "salesman", "auditor", "owner"
))):
    rows = conn.execute(text(
        "SELECT id, code, name, item_type, unit, hsn_code, is_active FROM items ORDER BY item_type, code"
    )).fetchall()
    return [dict(r._mapping) for r in rows]