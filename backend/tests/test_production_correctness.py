"""Focused production correctness regression tests."""
import re
import unittest
from contextlib import nullcontext
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from fastapi import HTTPException

from app.routers.production import (
    ActualLine,
    PostProductionRequest,
    StartProductionRequest,
    post_production,
    start_production,
)

ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_SOURCE = ROOT / "backend" / "app" / "routers" / "production.py"
SCHEMA_SOURCE = ROOT / "backend" / "app" / "models" / "schema.sql"


class Result:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, results):
        self._results = iter(results)

    def begin(self):
        return nullcontext()

    def execute(self, *_args, **_kwargs):
        return next(self._results)


class ProductionEndpointTests(unittest.TestCase):
    def test_duplicate_actual_material_code_returns_422(self):
        run = SimpleNamespace(
            id=1,
            bom_id=1,
            planned_output=Decimal("100"),
            labour_cost=Decimal("0"),
            overhead_cost=Decimal("0"),
            status="draft",
            finished_item_id=99,
        )
        planned_line = SimpleNamespace(
            id=10,
            item_id=20,
            planned_qty=Decimal("5"),
            code="RM-FLOUR",
            name="Flour",
            unit="kg",
        )
        conn = FakeConnection([
            Result(row=run),
            Result(rows=[planned_line]),
        ])
        body = PostProductionRequest(
            actual_output=Decimal("100"),
            actual_lines=[
                ActualLine(item_code="RM-FLOUR", actual_qty=Decimal("5")),
                ActualLine(item_code="RM-FLOUR", actual_qty=Decimal("4")),
            ],
        )

        with self.assertRaises(HTTPException) as raised:
            post_production(
                run_id=1,
                body=body,
                conn=conn,
                user={"sub": "1"},
            )

        self.assertEqual(raised.exception.status_code, 422)
        self.assertIn(
            "Duplicate actual material code: RM-FLOUR",
            raised.exception.detail,
        )

    def test_zero_and_negative_bom_batch_output_return_422(self):
        bom_lines = [
            SimpleNamespace(
                item_id=20,
                qty_per_batch=Decimal("5"),
                code="RM-FLOUR",
                name="Flour",
                unit="kg",
            )
        ]

        for invalid_qty in (Decimal("0"), Decimal("-1")):
            with self.subTest(batch_output_qty=invalid_qty):
                conn = FakeConnection([
                    Result(row=SimpleNamespace(batch_output_qty=invalid_qty)),
                    Result(rows=bom_lines),
                ])
                body = StartProductionRequest(
                    bom_id=1,
                    run_date=date(2026, 11, 26),
                    planned_output=Decimal("100"),
                )

                with self.assertRaises(HTTPException) as raised:
                    start_production(
                        body=body,
                        conn=conn,
                        user={"sub": "1"},
                    )

                self.assertEqual(raised.exception.status_code, 422)
                self.assertEqual(
                    raised.exception.detail,
                    "BOM batch_output_qty must be greater than zero",
                )


class ProductionSourceTests(unittest.TestCase):
    def test_production_run_is_locked_before_status_check(self):
        source = PRODUCTION_SOURCE.read_text(encoding="utf-8")
        function_source = source[source.index("def post_production("):]

        lock_match = re.search(
            r"WHERE\s+pr\.id\s*=\s*:run_id\s+FOR\s+UPDATE\s+OF\s+pr",
            function_source,
            flags=re.IGNORECASE,
        )
        status_pos = function_source.find('if run.status != "draft"')
        if status_pos < 0:
            status_pos = function_source.find("if run.status != 'draft'")

        self.assertIsNotNone(lock_match, "Production run lock query missing")
        self.assertGreaterEqual(status_pos, 0, "Draft status check missing")
        self.assertLess(lock_match.start(), status_pos)

    def test_schema_has_positive_bom_batch_output_constraint(self):
        schema = SCHEMA_SOURCE.read_text(encoding="utf-8")
        bom_match = re.search(
            r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+bom_headers\s*\((.*?)\);",
            schema,
            flags=re.IGNORECASE | re.DOTALL,
        )
        self.assertIsNotNone(bom_match, "bom_headers definition missing")

        column_match = re.search(
            r"batch_output_qty\s+.*",
            bom_match.group(1),
            flags=re.IGNORECASE,
        )
        self.assertIsNotNone(column_match, "batch_output_qty column missing")
        self.assertRegex(
            column_match.group(0),
            r"NOT\s+NULL\s+CHECK\s*\(\s*batch_output_qty\s*>\s*0\s*\)",
        )


if __name__ == "__main__":
    unittest.main()
