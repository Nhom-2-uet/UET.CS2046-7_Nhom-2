"""Use case layer used by the command router."""

import re
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from APP.services import user_service
from services.ai_service import (
    answer_finance_question,
    explain_finance_result,
    extract_with_gemini,
)
from services.logic.analytics.finance_service import FinanceService
from services.logic.repositories import budget_repository as budgets
from services.logic.repositories import required_expense_repository as expenses
from services.logic.repositories import saving_goal_repository as goals
from services.logic.repositories.transaction_repository import get_categories
from services.transaction_service import (
    list_transactions,
    remove_transaction,
    save_transaction,
    save_transactions,
)
_AMOUNT_PATTERN = re.compile(
    r"(?<![\w])(?P<number>\d+(?:[.,]\d+)*)(?P<space>\s*)"
    r"(?P<unit>tỷ|tỉ|triệu|tr|củ|nghìn|ngàn|k|vnd|đồng|đ)\b",
    re.IGNORECASE,
)


def _parse_amount_from_question(question: str) -> int | None:
    """Parse an explicitly currency-marked amount; never infer a bare number."""
    matches = list(_AMOUNT_PATTERN.finditer(question))
    if not matches:
        return None

    # Prefer the first explicit amount. A bare count such as "2 tháng" is not
    # considered an amount because it has no currency unit.
    match = matches[0]
    raw_number = match.group("number")
    unit = match.group("unit").casefold()
    if "." in raw_number and "," in raw_number:
        decimal_separator = "." if raw_number.rfind(".") > raw_number.rfind(",") else ","
        integer_part, fractional_part = raw_number.rsplit(decimal_separator, 1)
        raw_number = integer_part.replace(".", "").replace(",", "") + "." + fractional_part
    elif "." in raw_number or "," in raw_number:
        separator = "." if "." in raw_number else ","
        parts = raw_number.split(separator)
        if len(parts) > 2 and all(len(part) == 3 for part in parts[1:]):
            raw_number = "".join(parts)
        elif len(parts) == 2 and len(parts[1]) == 3:
            raw_number = "".join(parts)
        else:
            raw_number = raw_number.replace(separator, ".")

    try:
        amount = Decimal(raw_number)
    except InvalidOperation:
        return None

    multiplier = {
        "k": 1_000,
        "nghìn": 1_000,
        "ngàn": 1_000,
        "tr": 1_000_000,
        "triệu": 1_000_000,
        "củ": 1_000_000,
        "tỷ": 1_000_000_000,
        "tỉ": 1_000_000_000,
    }.get(unit, 1)
    value = int(amount * multiplier)
    return value if value > 0 else None


def _build_finance_answer(question: str, user_id: int) -> dict[str, Any]:
    """Compute trusted personal finance context, then ask Gemini to advise."""
    today = date.today()
    if today.month == 1:
        previous_year, previous_month = today.year - 1, 12
    else:
        previous_year, previous_month = today.year, today.month - 1
    previous_start = date(previous_year, previous_month, 1)
    previous_end = date(
        previous_year,
        previous_month,
        min(today.day, monthrange(previous_year, previous_month)[1]),
    )
    month_end = date(today.year, today.month, monthrange(today.year, today.month)[1])

    all_transactions = list_transactions(
        user_id, start_date=previous_start, end_date=today
    )
    current_transactions = [
        item for item in all_transactions
        if item.transaction_date.year == today.year
        and item.transaction_date.month == today.month
    ]
    previous_transactions = [
        item for item in all_transactions
        if item.transaction_date.year == previous_year
        and item.transaction_date.month == previous_month
        and item.transaction_date <= previous_end
    ]

    def totals(transactions: list[Any]) -> tuple[int, int]:
        income = sum(
            item.amount_vnd for item in transactions
            if item.transaction_type == "income"
        )
        expense = sum(
            item.amount_vnd for item in transactions
            if item.transaction_type == "expense"
        )
        return income, expense

    current_income, current_expense = totals(current_transactions)
    previous_income, previous_expense = totals(previous_transactions)
    category_totals: dict[str, int] = {}
    for item in current_transactions:
        if item.transaction_type == "expense":
            category_totals[item.category_name] = (
                category_totals.get(item.category_name, 0) + item.amount_vnd
            )
    sorted_categories = sorted(
        category_totals.items(), key=lambda pair: pair[1], reverse=True
    )

    budget = budgets.get_budget_settings(user_id)
    budget_limit = int(budget.monthly_budget_vnd) if budget else None
    reserve_amount = (
        int(Decimal(budget_limit) * Decimal(str(budget.reserve_rate)))
        if budget else None
    )
    remaining_budget = budget_limit - current_expense if budget_limit is not None else None

    unpaid_expenses = expenses.get_required_expenses(user_id, status="unpaid")
    upcoming_expenses = [
        item for item in unpaid_expenses
        if today <= item.due_date <= month_end
    ]
    upcoming_required_amount = sum(item.amount_vnd for item in upcoming_expenses)
    discretionary_budget = (
        max(0, remaining_budget - reserve_amount - upcoming_required_amount)
        if remaining_budget is not None and reserve_amount is not None
        else None
    )

    active_goals = goals.get_saving_goals(user_id, status="active")
    goal_context = [
        {
            "name": item.name,
            "remaining_vnd": max(0, item.target_amount_vnd - item.progress_vnd),
            "deadline": item.deadline.isoformat(),
        }
        for item in active_goals
    ]

    purchase_amount = _parse_amount_from_question(question)
    purchase_assessment = None
    if purchase_amount is not None:
        if discretionary_budget is None:
            purchase_assessment = {
                "amount_vnd": purchase_amount,
                "needs_amount_confirmation": purchase_amount >= 1_000_000_000,
                "can_fit_monthly_plan": None,
                "reason": "Chưa thiết lập ngân sách tháng nên chưa thể đánh giá theo hạn mức.",
            }
        else:
            purchase_assessment = {
                "amount_vnd": purchase_amount,
                "needs_amount_confirmation": purchase_amount >= 1_000_000_000,
                "discretionary_budget_before_purchase_vnd": discretionary_budget,
                "remaining_after_purchase_vnd": discretionary_budget - purchase_amount,
                "can_fit_monthly_plan": purchase_amount <= discretionary_budget,
                "reason": (
                    "Khoản mua nằm trong phần ngân sách linh hoạt ước tính còn lại."
                    if purchase_amount <= discretionary_budget
                    else "Khoản mua vượt phần ngân sách linh hoạt ước tính còn lại."
                ),
            }

    context = {
        "period": today.strftime("%Y-%m"),
        "period_scope": "Từ đầu tháng đến hôm nay",
        "transaction_count": len(current_transactions),
        "income_vnd": current_income,
        "expense_vnd": current_expense,
        "net_cash_flow_vnd": current_income - current_expense,
        "saving_rate_percent": round(
            (current_income - current_expense) / current_income * 100, 1
        ) if current_income > 0 else None,
        "top_expense_categories": [
            {"category": name, "amount_vnd": amount,
             "share_percent": round(amount / current_expense * 100, 1) if current_expense else 0}
            for name, amount in sorted_categories[:5]
        ],
        "same_days_previous_month": {
            "period": f"{previous_year:04d}-{previous_month:02d}-01 to {previous_end.isoformat()}",
            "income_vnd": previous_income,
            "expense_vnd": previous_expense,
            "expense_change_vnd": current_expense - previous_expense,
            "expense_change_percent": round(
                (current_expense - previous_expense) / previous_expense * 100, 1
            ) if previous_expense > 0 else None,
        },
        "monthly_budget_vnd": budget_limit,
        "budget_used_percent": round(current_expense / budget_limit * 100, 1)
            if budget_limit and budget_limit > 0 else None,
        "budget_remaining_vnd": remaining_budget,
        "reserve_target_vnd": reserve_amount,
        "upcoming_unpaid_required_expenses_this_month": [
            {"name": item.name, "amount_vnd": item.amount_vnd,
             "due_date": item.due_date.isoformat()}
            for item in upcoming_expenses
        ],
        "upcoming_required_total_vnd": upcoming_required_amount,
        "estimated_discretionary_budget_vnd": discretionary_budget,
        "active_saving_goals": goal_context,
        "purchase_assessment": purchase_assessment,
    }

    answer = answer_finance_question(question, financial_context=context)
    summary = {
        "period": today.strftime("%m/%Y"),
        "income_vnd": current_income,
        "expense_vnd": current_expense,
        "budget_remaining_vnd": remaining_budget,
        "top_category": sorted_categories[0][0] if sorted_categories else None,
        "purchase_assessment": purchase_assessment,
        "has_transactions": bool(current_transactions),
    }
    return {"answer": answer, "summary": summary}


def execute(command: str, data: dict[str, Any]) -> Any:
    user_id = data.get("user_id")
    if command == "auth.login":
        user = user_service.authenticate_user(data["username"], data["password"])
        if user is None:
            raise ValueError("Tên đăng nhập hoặc mật khẩu không đúng.")
        return user
    if command == "auth.register":
        return user_service.create_user(
            data["username"], data["password"], data["display_name"]
        )
    if command == "transaction.categories":
        return get_categories(data.get("transaction_type"))
    if command == "transaction.list":
        return list_transactions(
            user_id, data.get("start_date"), data.get("end_date")
        )
    if command == "transaction.create":
        return save_transaction(user_id, data)
    if command == "transaction.create_many":
        return save_transactions(user_id, data.get("transactions", []))
    if command == "transaction.update":
        return save_transaction(user_id, data, data["transaction_id"])
    if command == "transaction.delete":
        return remove_transaction(user_id, data["transaction_id"])
    if command == "budget.get":
        return budgets.get_budget_settings(user_id)
    if command == "budget.save":
        return budgets.save_budget_settings(
            user_id,
            int(data["monthly_budget_vnd"]),
            data.get("payday"),
            int(data.get("weekday_daily_limit_vnd", 0)),
            int(data.get("weekend_daily_limit_vnd", 0)),
        )
    if command == "expense.list":
        return expenses.get_required_expenses(user_id, data.get("status"))
    if command == "expense.create":
        return expenses.create_required_expense(
            user_id, data["name"], int(data["amount_vnd"]), data["due_date"]
        )
    if command == "expense.update":
        return expenses.update_required_expense(
            user_id, data["expense_id"], data["name"],
            int(data["amount_vnd"]), data["due_date"]
        )
    if command == "expense.delete":
        return expenses.delete_required_expense(user_id, data["expense_id"])
    if command == "goal.list":
        return goals.get_saving_goals(user_id, data.get("status"))
    if command == "goal.create":
        return goals.create_saving_goal(
            user_id, data["name"], int(data["target_amount_vnd"]), data["deadline"]
        )
    if command == "goal.update":
        return goals.update_saving_goal_details(
            user_id, data["goal_id"], int(data["target_amount_vnd"]), data["deadline"]
        )
    if command == "goal.cancel":
        return goals.cancel_saving_goal(user_id, data["goal_id"])
    if command == "ai.extract":
        return extract_with_gemini(data["text"])
    if command == "ai.explain":
        return explain_finance_result(data["result"])
    if command == "finance.ask":
        return _build_finance_answer(data["question"], user_id)
    if command == "finance.summary":
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        records = list_transactions(user_id, start_date, end_date)
        summary = FinanceService.summarize_transactions(records)
        return {"transactions": records, **summary}
    raise ValueError(f"Lệnh không được hỗ trợ: {command}")
