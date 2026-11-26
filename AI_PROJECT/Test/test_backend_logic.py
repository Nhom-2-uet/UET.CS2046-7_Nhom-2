"""Unit tests for backend logic; these tests do not require a running MySQL server."""

from datetime import date, datetime
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


PROJECT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_DIR / "APP"
for import_path in (APP_DIR, PROJECT_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from services.logic.analytics.budget_service import BudgetService
from services.logic.analytics.anomaly_service import AnomalyService
from services.logic.analytics.finance_service import FinanceService
from services.logic.analytics.insight_service import InsightService
from services.logic.analytics.saving_service import SavingService
from services.logic.repositories._db import open_cursor
from services import user_service


class FinanceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.transactions = [
            {
                "amount": 5_000_000,
                "type": "income",
                "category": "Lương",
                "date": "2026-04-01",
            },
            {
                "amount": 1_500_000,
                "type": "expense",
                "category": "Ăn uống",
                "date": "2026-04-02",
            },
            {
                "amount": 500_000,
                "type": "expense",
                "category": "Đi lại",
                "date": "2026-04-03",
            },
            {
                "amount": 1_000_000,
                "type": "income",
                "category": "Lương",
                "date": "2026-05-01",
            },
        ]

    def test_totals_filter_by_month_and_year(self) -> None:
        self.assertEqual(
            FinanceService.calculate_total_income(self.transactions, 4, 2026),
            5_000_000,
        )
        self.assertEqual(
            FinanceService.calculate_expense_by_period(
                self.transactions, month=4, year=2026
            ),
            2_000_000,
        )

    def test_expense_categories_include_amount_and_percentage(self) -> None:
        result = FinanceService.get_expense_by_category(
            self.transactions, month=4, year=2026
        )

        self.assertEqual(result["total_expense"], 2_000_000)
        self.assertEqual(result["categories"][0]["category"], "Ăn uống")
        self.assertEqual(result["categories"][0]["percentage"], 75.0)

    def test_net_balance_and_budget_status(self) -> None:
        balance = FinanceService.calculate_net_balance(
            self.transactions, month=4, year=2026
        )
        budget = FinanceService.check_budget_status(
            self.transactions, budget_limit=2_500_000, month=4, year=2026
        )

        self.assertEqual(balance["net_balance"], 3_000_000)
        self.assertEqual(balance["saving_rate_percent"], 60.0)
        self.assertEqual(budget["status"], "WARNING")
        self.assertEqual(budget["usage_percent"], 80.0)

    def test_summarize_transactions_aggregates_all_input_dates(self) -> None:
        result = FinanceService.summarize_transactions(self.transactions)

        self.assertEqual(result["summary"]["total_income"], 6_000_000)
        self.assertEqual(result["summary"]["total_expense"], 2_000_000)
        self.assertEqual(result["summary"]["net_balance"], 4_000_000)
        self.assertEqual(
            result["categories"]["categories"][0]["category"], "Ăn uống"
        )

    def test_spending_trend_handles_month_after_zero_spending(self) -> None:
        transactions = [
            {
                "amount": 100,
                "type": "expense",
                "category": "Ăn uống",
                "date": "2026-01-10",
            },
            {
                "amount": 200,
                "type": "expense",
                "category": "Ăn uống",
                "date": "2026-03-10",
            },
        ]

        result = FinanceService.analyze_spending_trends(transactions)

        self.assertEqual(result["monthly_trend"][1]["amount"], 0.0)
        self.assertIsNone(result["mom_change_percent"])
        self.assertEqual(result["trend_direction"], "INCREASING")


class BudgetServiceTests(unittest.TestCase):
    def test_equal_to_limit_is_exceeded_and_zero_limit_is_handled(self) -> None:
        at_limit = BudgetService.evaluate_budget_status("Tổng", 100, 100)
        zero_limit = BudgetService.evaluate_category_budget("Ăn uống", 0, 10)

        self.assertEqual(at_limit["status"], "EXCEEDED")
        self.assertEqual(zero_limit["status"], "EXCEEDED")
        self.assertEqual(zero_limit["usage_percentage"], 100.0)

    def test_invalid_warning_threshold_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            BudgetService.evaluate_budget_status("Tổng", 100, 10, 101)


class AnomalyServiceTests(unittest.TestCase):
    def test_unusual_expense_is_returned_as_string_keyed_record(self) -> None:
        transactions = [
            {
                "amount": amount,
                "type": "expense",
                "category": "Ăn uống",
                "date": f"2026-04-{day:02d}",
            }
            for day, amount in enumerate([10, 10, 10, 10, 10, 1_000], start=1)
        ]

        result = AnomalyService.detect_unusual_transactions(transactions)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["amount"], 1_000)
        self.assertIn("z_score", result[0])

class SavingLogicTests(unittest.TestCase):
    def test_completed_goal_needs_no_more_saving(self) -> None:
        result = SavingService.evaluate_saving_goal(
            goal_name="Laptop",
            target_amount=10_000,
            current_saved=10_000,
            deadline_str="2026-12-31",
            current_date=date(2026, 11, 24),
        )

        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["required_per_day"], 0)
        self.assertEqual(result["required_per_month"], 0)

    def test_saving_plan_skips_inactive_goals_and_checks_feasibility(self) -> None:
        goals = [
            {
                "name": "Laptop",
                "target_amount_vnd": 10_000,
                "progress_vnd": 0,
                "deadline": date(2026, 3, 2),
                "status": "active",
            },
            {
                "name": "Inactive goal",
                "target_amount_vnd": 50_000,
                "progress_vnd": 0,
                "deadline": date(2026, 3, 2),
                "status": "cancelled",
            },
        ]

        result = InsightService.evaluate_saving_plan(
            goals,
            available_to_save_per_month=6_000,
            today=date(2026, 1, 1),
        )

        self.assertEqual(len(result["goals"]), 1)
        self.assertEqual(result["total_required_per_month_vnd"], 5_000)
        self.assertTrue(result["feasible"])


class DatabaseCursorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cursor = _FakeCursor()
        self.connection = _FakeConnection(self.cursor)

    def test_success_commits_and_closes_resources(self) -> None:
        with patch(
            "services.logic.repositories._db.get_connection",
            return_value=self.connection,
        ):
            with open_cursor() as cursor:
                self.assertIs(cursor, self.cursor)

        self.assertEqual(self.connection.commit_count, 1)
        self.assertEqual(self.connection.rollback_count, 0)
        self.assertTrue(self.cursor.closed)
        self.assertTrue(self.connection.closed)

    def test_error_rolls_back_and_closes_resources(self) -> None:
        with patch(
            "services.logic.repositories._db.get_connection",
            return_value=self.connection,
        ):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                with open_cursor():
                    raise RuntimeError("query failed")

        self.assertEqual(self.connection.commit_count, 0)
        self.assertEqual(self.connection.rollback_count, 1)
        self.assertTrue(self.cursor.closed)
        self.assertTrue(self.connection.closed)


class UserServiceTests(unittest.TestCase):
    def test_get_user_maps_repository_record_to_model(self) -> None:
        row = {
            "user_id": 7,
            "display_name": "Lan",
            "username": "lan",
            "created_at": datetime(2026, 1, 1),
        }
        with patch.object(user_service.user_repository, "get_user_record", return_value=row):
            user = user_service.get_user(7)

        self.assertIsNotNone(user)
        assert user is not None
        self.assertEqual(user.user_id, 7)
        self.assertEqual(user.username, "lan")

    def test_change_password_uses_verified_hash_for_conditional_update(self) -> None:
        with (
            patch.object(
                user_service.user_repository,
                "get_user_password_hash",
                return_value="verified-old-hash",
            ),
            patch.object(user_service, "_password_matches", return_value=True),
            patch.object(user_service, "_hash_password", return_value="new-hash"),
            patch.object(
                user_service.user_repository,
                "update_user_password_hash",
                return_value=True,
            ) as update_hash,
        ):
            updated = user_service.change_password(7, "old-password", "new-password")

        self.assertTrue(updated)
        update_hash.assert_called_once_with(
            7,
            expected_password_hash="verified-old-hash",
            new_password_hash="new-hash",
        )

class _FakeCursor:
    closed = False

    def close(self) -> None:
        self.closed = True


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def cursor(self, *, dictionary: bool) -> _FakeCursor:
        if not dictionary:
            raise AssertionError("Expected a dictionary cursor")
        return self._cursor

    def commit(self) -> None:
        self.commit_count += 1

    def rollback(self) -> None:
        self.rollback_count += 1

    def close(self) -> None:
        self.closed = True


if __name__ == "__main__":
    unittest.main()
