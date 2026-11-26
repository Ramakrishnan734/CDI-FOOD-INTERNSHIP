"""Role authorization regression tests; no database connection or writes required."""
import ast
import unittest
from pathlib import Path

from fastapi import HTTPException

from app.dependencies import require_role, ROLE_VALUES

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend" / "app" / "routers"


def endpoint_permissions():
    permissions = {}
    for file in BACKEND.glob("*.py"):
        tree = ast.parse(file.read_text(encoding="utf-8"))
        prefix = ""
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "router" and isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant):
                                prefix = kw.value.value
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            route_method = route_path = None
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "router":
                    route_method = decorator.func.attr.upper()
                    if decorator.args and isinstance(decorator.args[0], ast.Constant):
                        route_path = decorator.args[0].value
            if not route_method or route_path is None:
                continue
            roles = None
            for arg in node.args.args:
                default_index = node.args.args.index(arg) - (len(node.args.args) - len(node.args.defaults))
                if default_index < 0:
                    continue
                default = node.args.defaults[default_index]
                if isinstance(default, ast.Call) and isinstance(default.func, ast.Name) and default.func.id == "Depends" and default.args:
                    inner = default.args[0]
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name) and inner.func.id == "require_role":
                        roles = tuple(item.value for item in inner.args if isinstance(item, ast.Constant))
            permissions[(route_method, prefix + route_path)] = roles
    return permissions


class RolePermissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.permissions = endpoint_permissions()

    def assert_role_allowed(self, endpoint, role):
        roles = self.permissions[endpoint]
        self.assertIsNotNone(roles, f"{endpoint} must have an explicit role dependency")
        self.assertIn(role, roles, f"{role} should be allowed at {endpoint}")
        self.assertEqual(require_role(*roles)(user={"role": role}), {"role": role})

    def assert_role_denied(self, endpoint, role):
        roles = self.permissions[endpoint]
        self.assertIsNotNone(roles, f"{endpoint} must have an explicit role dependency")
        with self.assertRaises(HTTPException) as raised:
            require_role(*roles)(user={"role": role})
        self.assertEqual(raised.exception.status_code, 403)

    def test_production_supervisor_can_post_production(self):
        self.assert_role_allowed(("POST", "/production/start"), "production")
        self.assert_role_allowed(("POST", "/production/{run_id}/post"), "production")
        self.assert_role_allowed(("GET", "/production/boms"), "production")
        self.assert_role_allowed(("GET", "/production/runs"), "production")

    def test_production_supervisor_cannot_run_sales_or_purchase_mutations(self):
        for endpoint in [
            ("POST", "/sales/{order_id}/approve"),
            ("POST", "/sales/{order_id}/dispatch"),
            ("POST", "/sales/{order_id}/payment"),
            ("POST", "/sales/order"),
            ("POST", "/inventory/purchase"),
            ("POST", "/inventory/items"),
        ]:
            self.assert_role_denied(endpoint, "production")

    def test_accountant_can_read_business_reports_and_payment_register(self):
        for endpoint in [
            ("GET", "/reports/stock"),
            ("GET", "/reports/sales"),
            ("GET", "/reports/purchases"),
            ("GET", "/reports/production-costing"),
            ("GET", "/reports/gst-summary"),
            ("GET", "/reports/outstanding-ageing"),
            ("GET", "/sales/orders"),
            ("GET", "/sales/payments"),
            ("GET", "/production/runs"),
        ]:
            self.assert_role_allowed(endpoint, "auditor")

    def test_accountant_and_owner_are_denied_every_business_write(self):
        for (method, path), roles in self.permissions.items():
            if method in {"POST", "PUT", "PATCH", "DELETE"} and path != "/auth/login":
                self.assertIsNotNone(roles, f"write endpoint {method} {path} lacks role authorization")
                self.assertNotIn("auditor", roles, f"Accountant must not write: {method} {path}")
                self.assertNotIn("owner", roles, f"Owner must not mutate: {method} {path}")
                self.assert_role_denied((method, path), "auditor")
                self.assert_role_denied((method, path), "owner")

    def test_owner_can_read_business_wide_dashboard_sources(self):
        for endpoint in [
            ("GET", "/sales/orders"),
            ("GET", "/sales/payments"),
            ("GET", "/inventory/balance"),
            ("GET", "/inventory/ledger"),
            ("GET", "/reports/sales"),
            ("GET", "/reports/gst-summary"),
            ("GET", "/production/runs"),
        ]:
            self.assert_role_allowed(endpoint, "owner")

    def test_production_supervisor_ledger_is_filtered_to_production_movements(self):
        inventory_source = (BACKEND / "inventory.py").read_text(encoding="utf-8")
        reports_source = (BACKEND / "reports.py").read_text(encoding="utf-8")
        allowed_movements = "sl.movement_type IN ('production_issue', 'production_output')"
        self.assertIn(allowed_movements, inventory_source)
        self.assertIn("sl.ref_type = 'production_run'", inventory_source)
        self.assertIn('"production_only": user["role"] == "production"', inventory_source)
        self.assertIn(allowed_movements, reports_source)
        self.assertIn("sl.ref_type = 'production_run'", reports_source)
        self.assertIn('"production_only": user["role"] == "production"', reports_source)
        self.assertIn("CASE WHEN :production_only THEN NULL", inventory_source)
        self.assertIn("CASE WHEN :production_only THEN NULL", reports_source)

    def test_salesman_and_admin_core_permissions_remain(self):
        self.assert_role_allowed(("POST", "/sales/order"), "salesman")
        self.assert_role_allowed(("POST", "/sales/order"), "admin")
        self.assert_role_allowed(("POST", "/sales/{order_id}/approve"), "admin")
        self.assert_role_allowed(("POST", "/sales/{order_id}/dispatch"), "admin")
        self.assert_role_allowed(("POST", "/sales/{order_id}/payment"), "admin")
        self.assert_role_allowed(("POST", "/inventory/purchase"), "admin")
        self.assert_role_allowed(("POST", "/inventory/items"), "admin")

    def test_existing_database_role_values_are_preserved(self):
        self.assertEqual(ROLE_VALUES, {"salesman", "admin", "production", "auditor", "owner"})

    def test_frontend_has_separate_owner_and_accountant_routes(self):
        app_source = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")
        login_source = (ROOT / "frontend/src/pages/Login.jsx").read_text(encoding="utf-8")
        self.assertIn('path="/owner"', app_source)
        self.assertIn("roles={['owner']}", app_source)
        self.assertIn('path="/accountant"', app_source)
        self.assertIn("roles={['auditor']}", app_source)
        for role in ("production", "auditor", "owner"):
            self.assertIn(f"{role}: '/", login_source)

    def test_mobile_role_validation_remains_salesman_only(self):
        auth_source = (ROOT / "mobile/src/api/auth.ts").read_text(encoding="utf-8")
        storage_source = (ROOT / "mobile/src/storage/secureStorage.ts").read_text(encoding="utf-8")
        self.assertIn("result.role !== 'salesman'", auth_source)
        self.assertIn("user.role !== 'salesman'", storage_source)


if __name__ == "__main__":
    unittest.main()
