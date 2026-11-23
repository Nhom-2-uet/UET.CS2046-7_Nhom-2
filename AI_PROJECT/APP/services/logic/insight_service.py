"""Các phép tính và cảnh báo tài chính bổ sung cho ứng dụng."""

from calendar import monthrange
from datetime import date, datetime
from difflib import SequenceMatcher
from math import ceil
from typing import Any


def _value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("Ngày phải có định dạng YYYY-MM-DD.") from error
    raise ValueError("Ngày giao dịch không hợp lệ.")


class InsightService:
    @staticmethod
    def classify_required_expense(
        expense: Any,
        today: date | None = None,
        remind_within_days: int = 7,
    ) -> dict[str, Any]:
        """Phân loại khoản chi bắt buộc theo trạng thái và ngày đến hạn."""
        if remind_within_days < 0:
            raise ValueError("remind_within_days không được âm.")

        name = _value(expense, "name", "")
        status = _value(expense, "status")
        due_date = _as_date(_value(expense, "due_date"))
        current_date = today or date.today()

        if status not in {"unpaid", "paid", "cancelled"}:
            raise ValueError("Trạng thái khoản chi bắt buộc không hợp lệ.")

        days_left = (due_date - current_date).days
        if status == "paid":
            alert_status = "PAID"
        elif status == "cancelled":
            alert_status = "CANCELLED"
        elif days_left < 0:
            alert_status = "OVERDUE"
        elif days_left == 0:
            alert_status = "DUE_TODAY"
        elif days_left <= remind_within_days:
            alert_status = "UPCOMING"
        else:
            alert_status = "LATER"

        return {
            "expense_name": name,
            "amount_vnd": _value(expense, "amount_vnd", 0),
            "due_date": due_date.isoformat(),
            "database_status": status,
            "alert_status": alert_status,
            "days_until_due": days_left,
        }

    @staticmethod
    def classify_required_expenses(
        expenses: list[Any],
        today: date | None = None,
        remind_within_days: int = 7,
    ) -> list[dict[str, Any]]:
        """Phân loại danh sách và xếp khoản cần chú ý lên trước."""
        priority = {
            "OVERDUE": 0,
            "DUE_TODAY": 1,
            "UPCOMING": 2,
            "LATER": 3,
            "PAID": 4,
            "CANCELLED": 5,
        }
        results = [
            InsightService.classify_required_expense(
                expense, today=today, remind_within_days=remind_within_days
            )
            for expense in expenses
        ]
        return sorted(
            results,
            key=lambda item: (
                priority[item["alert_status"]],
                item["due_date"],
            ),
        )

    @staticmethod
    def forecast_monthly_spending(
        spent_so_far: float,
        monthly_budget: float,
        today: date | None = None,
    ) -> dict[str, Any]:
        """Ước tính tổng chi cuối tháng theo tốc độ chi hiện tại."""
        if spent_so_far < 0 or monthly_budget < 0:
            raise ValueError("Chi tiêu và ngân sách không được âm.")

        current_date = today or date.today()
        days_in_month = monthrange(current_date.year, current_date.month)[1]
        projected_total = round(spent_so_far / current_date.day * days_in_month, 2)
        remaining_budget = round(monthly_budget - spent_so_far, 2)

        if projected_total > monthly_budget:
            status = "LIKELY_TO_EXCEED"
        else:
            status = "ON_TRACK"

        return {
            "month": current_date.strftime("%Y-%m"),
            "spent_so_far": round(spent_so_far, 2),
            "monthly_budget": round(monthly_budget, 2),
            "remaining_budget_now": remaining_budget,
            "projected_total": projected_total,
            "projected_over_by": round(
                max(0.0, projected_total - monthly_budget), 2
            ),
            "status": status,
            "method": "linear_daily_average",
        }

    @staticmethod
    def evaluate_saving_plan(
        goals: list[Any],
        available_to_save_per_month: float,
        today: date | None = None,
    ) -> dict[str, Any]:
        """Tính mức cần tiết kiệm hàng tháng cho các mục tiêu còn hoạt động."""
        if available_to_save_per_month < 0:
            raise ValueError("Số tiền có thể tiết kiệm không được âm.")

        current_date = today or date.today()
        goal_results = []

        for goal in goals:
            if _value(goal, "status", "active") != "active":
                continue

            target = float(_value(goal, "target_amount_vnd", 0))
            saved = float(
                _value(goal, "progress_vnd", _value(goal, "current_saved", 0))
            )
            deadline = _as_date(_value(goal, "deadline"))
            remaining = max(0.0, target - saved)
            days_left = (deadline - current_date).days

            if remaining == 0:
                required_per_month = 0
                status = "COMPLETED"
            elif days_left < 0:
                required_per_month = ceil(remaining)
                status = "OVERDUE"
            else:
                months_left = max(days_left / 30.0, 1.0 / 30.0)
                required_per_month = ceil(remaining / months_left)
                status = "IN_PROGRESS"

            goal_results.append({
                "goal_name": _value(goal, "name", ""),
                "remaining_amount_vnd": round(remaining, 2),
                "deadline": deadline.isoformat(),
                "required_per_month_vnd": required_per_month,
                "status": status,
            })

        total_required = sum(
            goal["required_per_month_vnd"] for goal in goal_results
        )
        return {
            "goals": goal_results,
            "total_required_per_month_vnd": total_required,
            "available_to_save_per_month_vnd": round(
                available_to_save_per_month, 2
            ),
            "feasible": total_required <= available_to_save_per_month,
            "shortfall_per_month_vnd": round(
                max(0, total_required - available_to_save_per_month), 2
            ),
        }

    @staticmethod
    def compare_monthly_category_spending(
        transactions: list[Any],
        month: int,
        year: int,
    ) -> dict[str, Any]:
        """So sánh chi tiêu từng danh mục với tháng liền trước."""
        if not 1 <= month <= 12:
            raise ValueError("month phải nằm trong khoảng 1 đến 12.")

        if month == 1:
            previous_month, previous_year = 12, year - 1
        else:
            previous_month, previous_year = month - 1, year

        totals: dict[tuple[int, int], dict[str, float]] = {
            (previous_year, previous_month): {},
            (year, month): {},
        }

        for transaction in transactions:
            transaction_type = _value(
                transaction, "type", _value(transaction, "transaction_type")
            )
            if transaction_type != "expense":
                continue

            transaction_date = _as_date(
                _value(transaction, "date", _value(transaction, "transaction_date"))
            )
            period = (transaction_date.year, transaction_date.month)
            if period not in totals:
                continue

            category = _value(
                transaction,
                "category_name",
                _value(transaction, "category", _value(transaction, "category_id")),
            )
            amount = float(
                _value(transaction, "amount", _value(transaction, "amount_vnd", 0))
            )
            if amount < 0:
                raise ValueError("Số tiền giao dịch không được âm.")

            totals[period][category] = totals[period].get(category, 0.0) + amount

        old_totals = totals[(previous_year, previous_month)]
        new_totals = totals[(year, month)]
        comparisons = []

        for category in set(old_totals) | set(new_totals):
            old_amount = old_totals.get(category, 0.0)
            new_amount = new_totals.get(category, 0.0)
            difference = new_amount - old_amount
            comparisons.append({
                "category": category,
                "previous_amount": round(old_amount, 2),
                "current_amount": round(new_amount, 2),
                "difference": round(difference, 2),
                "change_percent": (
                    round(difference / old_amount * 100, 2)
                    if old_amount > 0
                    else None
                ),
                "new_category": old_amount == 0 and new_amount > 0,
            })

        comparisons.sort(key=lambda item: item["difference"], reverse=True)
        return {
            "previous_period": f"{previous_year:04d}-{previous_month:02d}",
            "current_period": f"{year:04d}-{month:02d}",
            "categories": comparisons,
        }

    @staticmethod
    def find_possible_duplicates(
        transactions: list[Any],
        description_similarity_threshold: float = 0.85,
    ) -> list[dict[str, Any]]:
        """Tìm cặp giao dịch cùng ngày, số tiền, danh mục và mô tả gần nhau."""
        if not 0 <= description_similarity_threshold <= 1:
            raise ValueError("Ngưỡng tương đồng phải nằm trong khoảng 0 đến 1.")

        candidates = []
        normalized = []
        for transaction in transactions:
            normalized.append({
                "transaction_id": _value(transaction, "transaction_id"),
                "amount": float(
                    _value(transaction, "amount", _value(transaction, "amount_vnd", 0))
                ),
                "category": _value(
                    transaction,
                    "category_name",
                    _value(transaction, "category", _value(transaction, "category_id")),
                ),
                "date": _as_date(
                    _value(transaction, "date", _value(transaction, "transaction_date"))
                ),
                "description": str(_value(transaction, "description", "") or "").strip(),
            })

        for index, first in enumerate(normalized):
            for second in normalized[index + 1:]:
                if first["transaction_id"] is not None and (
                    first["transaction_id"] == second["transaction_id"]
                ):
                    continue
                if (
                    first["amount"] != second["amount"]
                    or first["category"] != second["category"]
                    or first["date"] != second["date"]
                ):
                    continue

                first_description = first["description"].casefold()
                second_description = second["description"].casefold()
                similarity = (
                    SequenceMatcher(None, first_description, second_description).ratio()
                    if first_description and second_description
                    else 1.0
                )
                if similarity >= description_similarity_threshold:
                    candidates.append({
                        "first_transaction": first,
                        "second_transaction": second,
                        "description_similarity": round(similarity, 3),
                        "needs_user_confirmation": True,
                    })

        return candidates
