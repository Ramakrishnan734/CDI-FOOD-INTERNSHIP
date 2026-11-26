# backend/app/routers/production.py

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.dependencies import get_db, require_role
from app.services.inventory_service import get_balance_and_wac, lock_items

router = APIRouter(prefix="/production", tags=["production"])

RATE_PLACES = Decimal("0.0001")
COST_PLACES = Decimal("0.0001")
VARIANCE_THRESHOLD = Decimal("3.0")


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class StartProductionRequest(BaseModel):
    bom_id: int
    run_date: date
    planned_output: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    labour_cost: Decimal = Field(ge=0, max_digits=15, decimal_places=2, default=Decimal("0"))
    overhead_cost: Decimal = Field(ge=0, max_digits=15, decimal_places=2, default=Decimal("0"))


class ActualLine(BaseModel):
    item_code: str = Field(min_length=1, max_length=20)
    actual_qty: Decimal = Field(ge=0, max_digits=12, decimal_places=4)


class PostProductionRequest(BaseModel):
    actual_output: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    damaged_qty: Decimal = Field(ge=0, max_digits=10, decimal_places=3, default=Decimal("0"))
    cartons_used: Decimal = Field(ge=0, max_digits=10, decimal_places=3, default=Decimal("0"))
    actual_lines: list[ActualLine] = Field(min_length=1)


# ------------------------------------------------------------------
# GET /production/boms
# Read-only BOM visibility for production, finance, and owner roles.
# ------------------------------------------------------------------

@router.get("/boms")
def list_boms(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production", "auditor", "owner")),
):
    rows = conn.execute(text("""
        SELECT bh.id AS bom_id, bh.version, bh.batch_output_qty,
               fg.code AS finished_item_code, fg.name AS finished_item_name,
               rm.code AS component_code, rm.name AS component_name,
               rm.unit AS component_unit, bl.qty_per_batch
        FROM bom_headers bh
        JOIN items fg ON fg.id = bh.finished_item_id
        LEFT JOIN bom_lines bl ON bl.bom_id = bh.id
        LEFT JOIN items rm ON rm.id = bl.item_id
        WHERE bh.is_active = true
        ORDER BY bh.id, bl.id
    """)).fetchall()

    boms = {}
    for row in rows:
        bom = boms.setdefault(row.bom_id, {
            "bom_id": row.bom_id,
            "version": row.version,
            "batch_output_qty": str(row.batch_output_qty),
            "finished_item_code": row.finished_item_code,
            "finished_item_name": row.finished_item_name,
            "components": [],
        })
        if row.component_code is not None:
            bom["components"].append({
                "item_code": row.component_code,
                "item_name": row.component_name,
                "unit": row.component_unit,
                "qty_per_batch": str(row.qty_per_batch),
            })
    return list(boms.values())


# ------------------------------------------------------------------
# GET /production/runs
# Read-only production history. No posting or stock movement occurs.
# ------------------------------------------------------------------

@router.get("/runs")
def list_production_runs(
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production", "auditor", "owner")),
):
    rows = conn.execute(text("""
        SELECT pr.id, pr.run_date, pr.bom_id, pr.planned_output,
               pr.actual_output, pr.damaged_qty, pr.cartons_used, pr.status,
               pr.labour_cost, pr.overhead_cost, pr.created_at,
               u.name AS created_by,
               fg.code AS finished_item_code, fg.name AS finished_item_name
        FROM production_runs pr
        JOIN bom_headers bh ON bh.id = pr.bom_id
        JOIN items fg ON fg.id = bh.finished_item_id
        LEFT JOIN users u ON u.id = pr.created_by
        ORDER BY pr.run_date DESC, pr.id DESC
    """)).fetchall()

    lines = conn.execute(text("""
        SELECT pl.run_id, i.code AS item_code, i.name AS item_name,
               i.unit, pl.planned_qty, pl.actual_qty
        FROM production_lines pl
        JOIN items i ON i.id = pl.item_id
        ORDER BY pl.run_id DESC, pl.id
    """)).fetchall()
    by_run = {}
    for line in lines:
        by_run.setdefault(line.run_id, []).append({
            "item_code": line.item_code,
            "item_name": line.item_name,
            "unit": line.unit,
            "planned_qty": str(line.planned_qty),
            "actual_qty": str(line.actual_qty),
            "variance_qty": str(Decimal(str(line.actual_qty)) - Decimal(str(line.planned_qty))),
        })

    return [{
        "run_id": row.id,
        "run_date": str(row.run_date),
        "bom_id": row.bom_id,
        "finished_item_code": row.finished_item_code,
        "finished_item_name": row.finished_item_name,
        "planned_output": str(row.planned_output),
        "actual_output": str(row.actual_output),
        "damaged_qty": str(row.damaged_qty),
        "cartons_used": str(row.cartons_used),
        "status": row.status,
        "labour_cost": str(row.labour_cost),
        "overhead_cost": str(row.overhead_cost),
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "lines": by_run.get(row.id, []),
    } for row in rows]


# ------------------------------------------------------------------
# POST /production/start
# Creates a draft production run with planned quantities from BOM.
# No stock movement at this stage.
# Roles: admin, production
# ------------------------------------------------------------------

@router.post("/start", status_code=201)
def start_production(
    body: StartProductionRequest,
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production")),
):
    user_id = int(user["sub"])

    with conn.begin():

        # 1. Validate BOM
        bom = conn.execute(
            text("""
                SELECT bh.id, bh.batch_output_qty, i.id AS fg_item_id,
                       i.code AS fg_code, i.name AS fg_name
                FROM bom_headers bh
                JOIN items i ON i.id = bh.finished_item_id
                WHERE bh.id = :bom_id AND bh.is_active = true
            """),
            {"bom_id": body.bom_id},
        ).fetchone()

        if bom is None:
            raise HTTPException(
                status_code=404,
                detail=f"BOM {body.bom_id} not found or inactive",
            )

        # 2. Load BOM lines
        bom_lines = conn.execute(
            text("""
                SELECT bl.item_id, bl.qty_per_batch,
                       i.code, i.name, i.unit
                FROM bom_lines bl
                JOIN items i ON i.id = bl.item_id
                WHERE bl.bom_id = :bom_id
                ORDER BY bl.id
            """),
            {"bom_id": body.bom_id},
        ).fetchall()

        if not bom_lines:
            raise HTTPException(
                status_code=422,
                detail=f"BOM {body.bom_id} has no lines",
            )

        # 3. Calculate planned quantities scaled to planned_output
        # planned_qty = qty_per_batch × (planned_output / batch_output_qty)
        batch_output_qty = Decimal(str(bom.batch_output_qty))
        if batch_output_qty <= 0:
            raise HTTPException(
                status_code=422,
                detail="BOM batch_output_qty must be greater than zero",
            )
        planned_output = body.planned_output
        scale = planned_output / batch_output_qty

        # 4. Create draft production run
        run_id = conn.execute(
            text("""
                INSERT INTO production_runs
                    (run_date, bom_id, planned_output, actual_output,
                     damaged_qty, cartons_used, status,
                     labour_cost, overhead_cost, created_by)
                VALUES
                    (:run_date, :bom_id, :planned_output, 0,
                     0, 0, 'draft',
                     :labour_cost, :overhead_cost, :user_id)
                RETURNING id
            """),
            {
                "run_date": body.run_date,
                "bom_id": body.bom_id,
                "planned_output": planned_output,
                "labour_cost": body.labour_cost,
                "overhead_cost": body.overhead_cost,
                "user_id": user_id,
            },
        ).scalar_one()

        # 5. Insert production lines (planned only, actual_qty = 0)
        planned_lines = []
        for line in bom_lines:
            planned_qty = (
                Decimal(str(line.qty_per_batch)) * scale
            ).quantize(RATE_PLACES, rounding=ROUND_HALF_UP)

            conn.execute(
                text("""
                    INSERT INTO production_lines
                        (run_id, item_id, planned_qty, actual_qty)
                    VALUES
                        (:run_id, :item_id, :planned_qty, 0)
                """),
                {
                    "run_id": run_id,
                    "item_id": line.item_id,
                    "planned_qty": planned_qty,
                },
            )

            planned_lines.append({
                "item_code": line.code,
                "item_name": line.name,
                "unit": line.unit,
                "planned_qty": str(planned_qty),
            })

    return {
        "run_id": run_id,
        "status": "draft",
        "bom_id": body.bom_id,
        "finished_good": bom.fg_code,
        "planned_output": str(planned_output),
        "planned_lines": planned_lines,
    }


# ------------------------------------------------------------------
# POST /production/{run_id}/post
# Posts a draft run: writes stock movements, calculates variances.
# Roles: admin, production
# ------------------------------------------------------------------

@router.post("/{run_id}/post", status_code=200)
def post_production(
    run_id: int,
    body: PostProductionRequest,
    conn=Depends(get_db),
    user=Depends(require_role("admin", "production")),
):
    user_id = int(user["sub"])

    with conn.begin():

        # 1. Load and validate the run
        run = conn.execute(
            text("""
                SELECT pr.id, pr.bom_id, pr.planned_output,
                       pr.labour_cost, pr.overhead_cost, pr.status,
                       bh.finished_item_id
                FROM production_runs pr
                JOIN bom_headers bh ON bh.id = pr.bom_id
                WHERE pr.id = :run_id
                FOR UPDATE OF pr
            """),
            {"run_id": run_id},
        ).fetchone()

        if run is None:
            raise HTTPException(status_code=404, detail=f"Production run {run_id} not found")
        if run.status != "draft":
            raise HTTPException(
                status_code=409,
                detail=f"Production run {run_id} is already {run.status} and cannot be posted again",
            )

        # 2. Load planned lines to match against actual input
        planned = conn.execute(
            text("""
                SELECT pl.id, pl.item_id, pl.planned_qty,
                       i.code, i.name, i.unit
                FROM production_lines pl
                JOIN items i ON i.id = pl.item_id
                WHERE pl.run_id = :run_id
                ORDER BY pl.id
            """),
            {"run_id": run_id},
        ).fetchall()

        # Build a lookup: item_code -> planned row
        planned_map = {row.code: row for row in planned}

        # 3. Validate actual lines match BOM items exactly
        actual_map = {}
        for al in body.actual_lines:
            if al.item_code in actual_map:
                raise HTTPException(
                    status_code=422,
                    detail=f"Duplicate actual material code: {al.item_code}",
                )

            if al.item_code not in planned_map:
                raise HTTPException(
                    status_code=422,
                    detail=f"Item '{al.item_code}' is not in this BOM",
                )

            actual_map[al.item_code] = al.actual_qty

        # Every BOM item must have an actual entry
        for code in planned_map:
            if code not in actual_map:
                raise HTTPException(
                    status_code=422,
                    detail=f"Missing actual quantity for item '{code}'",
                )

        # 4. Lock all items: inputs + finished good
        all_item_ids = [row.item_id for row in planned] + [run.finished_item_id]
        lock_items(conn, all_item_ids)

        # 5. Check sufficient stock for each input material
        for row in planned:
            actual_qty = actual_map[row.code]
            balance, _ = get_balance_and_wac(conn, row.item_id)
            if balance < actual_qty:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Insufficient stock for '{row.code}': "
                        f"need {actual_qty}, have {balance}"
                    ),
                )

        # 6. Write stock-out ledger rows for each input material
        # Record the WAC at issue time — this is required for accurate costing
        total_material_cost = Decimal("0")
        result_lines = []

        for row in planned:
            actual_qty = actual_map[row.code]
            planned_qty = Decimal(str(row.planned_qty))
            balance, wac = get_balance_and_wac(conn, row.item_id)

            # Issue at current WAC
            issue_rate = wac if wac is not None else Decimal("0")
            material_cost = actual_qty * issue_rate
            total_material_cost += material_cost

            conn.execute(
                text("""
                    INSERT INTO stock_ledger
                        (item_id, movement_type, qty_in, qty_out, rate,
                         ref_type, ref_id, created_by)
                    VALUES
                        (:item_id, 'production_issue', 0, :qty_out, :rate,
                         'production_run', :run_id, :user_id)
                """),
                {
                    "item_id": row.item_id,
                    "qty_out": actual_qty,
                    "rate": issue_rate,
                    "run_id": run_id,
                    "user_id": user_id,
                },
            )

            # Update production_lines with actual qty
            conn.execute(
                text("""
                    UPDATE production_lines
                    SET actual_qty = :actual_qty
                    WHERE id = :line_id
                """),
                {"actual_qty": actual_qty, "line_id": row.id},
            )

            # Calculate variance
            if planned_qty > 0:
                variance_pct = (
                    (actual_qty - planned_qty) / planned_qty * 100
                ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                variance_pct = Decimal("0")

            flagged = abs(variance_pct) > VARIANCE_THRESHOLD

            result_lines.append({
                "item_code": row.code,
                "item_name": row.name,
                "unit": row.unit,
                "planned_qty": str(planned_qty),
                "actual_qty": str(actual_qty),
                "issue_rate_wac": str(issue_rate),
                "material_cost": str(material_cost.quantize(COST_PLACES, rounding=ROUND_HALF_UP)),
                "variance_pct": str(variance_pct),
                "flagged": flagged,
            })

        # 7. Calculate cost per finished good packet
        total_cost = (
            total_material_cost
            + Decimal(str(run.labour_cost))
            + Decimal(str(run.overhead_cost))
        )
        actual_output = body.actual_output
        cost_per_packet = (total_cost / actual_output).quantize(
            COST_PLACES, rounding=ROUND_HALF_UP
        )

        # 8. Write stock-in ledger row for finished good
        conn.execute(
            text("""
                INSERT INTO stock_ledger
                    (item_id, movement_type, qty_in, qty_out, rate,
                     ref_type, ref_id, created_by)
                VALUES
                    (:item_id, 'production_output', :qty_in, 0, :rate,
                     'production_run', :run_id, :user_id)
            """),
            {
                "item_id": run.finished_item_id,
                "qty_in": actual_output,
                "rate": cost_per_packet,
                "run_id": run_id,
                "user_id": user_id,
            },
        )

        # 9. Update production run to posted
        conn.execute(
            text("""
                UPDATE production_runs
                SET status = 'posted',
                    actual_output = :actual_output,
                    damaged_qty = :damaged_qty,
                    cartons_used = :cartons_used
                WHERE id = :run_id
            """),
            {
                "actual_output": actual_output,
                "damaged_qty": body.damaged_qty,
                "cartons_used": body.cartons_used,
                "run_id": run_id,
            },
        )

    return {
        "run_id": run_id,
        "status": "posted",
        "actual_output": str(actual_output),
        "damaged_qty": str(body.damaged_qty),
        "cartons_used": str(body.cartons_used),
        "total_material_cost": str(total_material_cost.quantize(COST_PLACES, rounding=ROUND_HALF_UP)),
        "labour_cost": str(run.labour_cost),
        "overhead_cost": str(run.overhead_cost),
        "total_cost": str(total_cost.quantize(COST_PLACES, rounding=ROUND_HALF_UP)),
        "cost_per_packet": str(cost_per_packet),
        "lines": result_lines,
    }