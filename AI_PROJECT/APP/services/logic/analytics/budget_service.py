from typing import Any
from services.logic.analytics.finance_service import FinanceService


class BudgetService:
    @staticmethod
    def evaluate_budget_status(
        label: str,
        budget_limit: float,
        spent_amount: float,
        warning_threshold: float = 80.0,
    ) -> dict[str, Any]:
        if budget_limit < 0 or spent_amount < 0:
            raise ValueError("Hạn mức ngân sách và số tiền chi tiêu không được âm.")
        if not 0 <= warning_threshold <= 100:
            raise ValueError("warning_threshold phải nằm trong khoảng 0 đến 100.")

        remaining = budget_limit - spent_amount

        if budget_limit > 0:
            usage_percent = round((spent_amount / budget_limit) * 100, 2)
        else:
            usage_percent = 100.0 if spent_amount > 0 else 0.0

        if spent_amount >= budget_limit and spent_amount > 0:
            status = "EXCEEDED"
            threshold_message = "đã vượt" if spent_amount > budget_limit else "đã chạm"
            alert_msg = (
                f"Cảnh báo: '{label}' {threshold_message} ngân sách "
                f"{abs(remaining):,.0f} VNĐ ({usage_percent}%)."
            )
        elif usage_percent >= warning_threshold:
            status = "WARNING"
            alert_msg = (
                f"Lưu ý: '{label}' đã dùng {usage_percent}% ngân sách. "
                f"Chỉ còn {remaining:,.0f} VNĐ."
            )
        else:
            status = "SAFE"
            alert_msg = (
                f"'{label}' đang trong tầm kiểm soát "
                f"(Còn lại {remaining:,.0f} VNĐ)."
            )

        return {
            "label": label,
            "budget_limit": budget_limit,
            "spent_amount": spent_amount,
            "remaining_amount": remaining,
            "usage_percentage": usage_percent,
            "status": status,
            "alert_message": alert_msg,
        }

    @classmethod
    def evaluate_category_budget(
        cls,
        category: str,
        budget_limit: float,
        spent_amount: float,
        warning_threshold: float = 80.0,
    ) -> dict[str, Any]:
        """Tương thích API cũ; dùng chung cách tính trạng thái ngân sách."""
        result = cls.evaluate_budget_status(
            category, budget_limit, spent_amount, warning_threshold
        )
        result["category"] = result.pop("label")
        return result

    @classmethod
    def check_all_budgets(
        cls,
        transactions: list[dict[str, Any]],
        budgets: dict[str, float],
        month: int,
        year: int,
        warning_threshold: float = 80.0,
    ) -> list[dict[str, Any]]:
       
        cat_summary = FinanceService.get_expense_by_category(transactions, month, year)
        spent_map = {
            item["category"]: item["amount"]
            for item in cat_summary.get("categories", [])
        }

        results = []
        for category, limit in budgets.items():
            spent = spent_map.get(category, 0.0)
            results.append(
                cls.evaluate_category_budget(
                    category=category,
                    budget_limit=limit,
                    spent_amount=spent,
                    warning_threshold=warning_threshold,
                )
            )

        return results
