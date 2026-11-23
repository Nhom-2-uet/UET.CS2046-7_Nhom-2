"""Use case layer used by the command router."""

from datetime import date
from typing import Any

from APP.services import user_service
from services.ai_service import explain_finance_result, extract_with_gemini
from services.logic.repositories import budget_repository as budgets
from services.logic.repositories import required_expense_repository as expenses
from services.logic.repositories import saving_goal_repository as goals
from services.logic.repositories.transaction_repository import get_categories
from services.transaction_service import (
    list_transactions,
    remove_transaction,
    save_transaction,
)
from services.logic.analytics.finance_service import FinanceService


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
    if command == "transaction.update":
        return save_transaction(user_id, data, data["transaction_id"])
    if command == "transaction.delete":
        return remove_transaction(user_id, data["transaction_id"])
    if command == "budget.get":
        return budgets.get_budget_settings(user_id)
    if command == "budget.save":
        return budgets.save_budget_settings(
            user_id, int(data["monthly_budget_vnd"]), data.get("payday")
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
        today = date.today()
        records = list_transactions(user_id, start_date=None, end_date=today)
        summary = FinanceService.calculate_net_balance(
            records, month=today.month, year=today.year
        )
        category_summary = FinanceService.get_expense_by_category(
            records, month=today.month, year=today.year
        )
        return explain_finance_result({
            "question": data["question"],
            "period": today.strftime("%Y-%m"),
            "monthly_summary": summary,
            "expense_by_category": category_summary,
        })
    if command == "finance.summary":
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        records = list_transactions(user_id, start_date, end_date)
        summary = FinanceService.summarize_transactions(records)
        return {"transactions": records, **summary}
    raise ValueError(f"Lệnh không được hỗ trợ: {command}")
