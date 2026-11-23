import pandas as pd
from typing import Dict, Any

class FinanceService:

     @staticmethod
     def _prepare_df(transactions: list[Dict[str, Any]]) -> pd.DataFrame:
        """Chuẩn hóa dict hoặc Transaction thành các cột dùng trong tính toán."""
        required_cols = ["amount", "type", "category", "date"]
        if not transactions:
            return pd.DataFrame(columns=required_cols)

        rows = []
        for transaction in transactions:
            if isinstance(transaction, dict):
                rows.append({
                    "amount": transaction.get("amount", transaction.get("amount_vnd")),
                    "type": transaction.get("type", transaction.get("transaction_type")),
                    "category": transaction.get(
                        "category_name",
                        transaction.get("category", transaction.get("category_id")),
                    ),
                    "date": transaction.get("date", transaction.get("transaction_date")),
                })
            else:
                rows.append({
                    "amount": getattr(
                        transaction, "amount", getattr(transaction, "amount_vnd", None)
                    ),
                    "type": getattr(
                        transaction,
                        "type",
                        getattr(transaction, "transaction_type", None),
                    ),
                    "category": getattr(
                        transaction,
                        "category_name",
                        getattr(
                            transaction,
                            "category",
                            getattr(transaction, "category_id", None),
                        ),
                    ),
                    "date": getattr(
                        transaction,
                        "date",
                        getattr(transaction, "transaction_date", None),
                    ),
                })

        df = pd.DataFrame(rows, columns=required_cols)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        return df.dropna(subset=['date'])

     @staticmethod
     def _filter_by_date(df, day=None, month=None, year=None):
         "Hàm phụ trợ lọc DataFrame theo ngày, tháng, năm bằng Boolean Mask."
         mask = pd.Series(True, index=df.index)
         if day is not None:
            mask &= (df['date'].dt.day == day)
         if month is not None:
            mask &= (df['date'].dt.month == month)
         if year is not None:
            mask &= (df['date'].dt.year == year)
         return df.loc[mask]

     @staticmethod
     def _expense_category_amounts(exp_df):
        if exp_df.empty:
            return []
        grouped = (
            exp_df.groupby('category', as_index=False)['amount']
            .sum()
            .sort_values(by='amount', ascending=False)
        )
        return grouped.to_dict(orient='records')

     @classmethod
     def calculate_total_income(cls, transactions, month, year):
        df = cls._prepare_df(transactions)
        if df.empty:
            return 0.0

        inc_df = df[df['type'] == 'income']
        filtered = cls._filter_by_date(inc_df, month=month, year=year)
        return float(filtered['amount'].sum())

     @classmethod
     def calculate_expense_by_period(cls, transactions, day=None, month=None, year=None):
        df = cls._prepare_df(transactions)
        if df.empty:
            return 0.0

        exp_df = df[df['type'] == 'expense']
        filtered = cls._filter_by_date(exp_df, day=day, month=month, year=year)
        return float(filtered['amount'].sum())

     @classmethod
     def get_expense_by_category(cls, transactions, month, year):
        df = cls._prepare_df(transactions)
        if df.empty:
            return {"total_expense": 0.0, "categories": []}

        exp_df = cls._filter_by_date(df[df['type'] == 'expense'], month=month, year=year)
        total_exp = float(exp_df['amount'].sum())

        if total_exp == 0:
            return {"total_expense": 0.0, "categories": []}

        categories = cls._expense_category_amounts(exp_df)
        for item in categories:
            item['percentage'] = round(item['amount'] / total_exp * 100, 2)

        return {
            "total_expense": round(total_exp, 2),
            "categories": categories
        }

     @classmethod
     def summarize_transactions(cls, transactions):
        """Tổng hợp thu, chi và chi theo danh mục trên toàn bộ danh sách đầu vào."""
        df = cls._prepare_df(transactions)
        income_total = float(df.loc[df['type'] == 'income', 'amount'].sum())
        expense_df = df.loc[df['type'] == 'expense']
        expense_total = float(expense_df['amount'].sum())
        category_amounts = cls._expense_category_amounts(expense_df)

        return {
            "summary": {
                "total_income": round(income_total, 2),
                "total_expense": round(expense_total, 2),
                "net_balance": round(income_total - expense_total, 2),
            },
            "categories": {
                "total_expense": round(expense_total, 2),
                "categories": category_amounts,
            },
        }

     @classmethod
     def calculate_net_balance(cls, transactions, month, year):
        "Nhiệm vụ 4 (Gợi ý bổ sung): Tính cân đối thu chi và tỷ lệ tiết kiệm."
        total_income = cls.calculate_total_income(transactions, month=month, year=year)
        total_expense = cls.calculate_expense_by_period(transactions, month=month, year=year)
        net_savings = total_income - total_expense
        saving_rate = round((net_savings / total_income * 100), 2) if total_income > 0 else 0.0

        return {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "net_balance": round(net_savings, 2),
            "saving_rate_percent": saving_rate
        }

     @classmethod
     def check_budget_status(cls, transactions, budget_limit, month, year):
        from services.logic.analytics.budget_service import BudgetService

        total_expense = cls.calculate_expense_by_period(transactions, month=month, year=year)
        result = BudgetService.evaluate_budget_status(
            label="Ngân sách tổng",
            budget_limit=budget_limit,
            spent_amount=total_expense,
        )
        return {
            "budget_limit": budget_limit,
            "total_expense": round(total_expense, 2),
            "remaining_budget": result["remaining_amount"],
            "usage_percent": result["usage_percentage"],
            "status": result["status"],
        }

     @classmethod
     def analyze_spending_trends(cls, transactions):
        df = cls._prepare_df(transactions)
        exp_df = df[df['type'] == 'expense'].copy()
        if exp_df.empty:
            return {"monthly_trend": [], "mom_change_percent": 0.0, "trend_direction": "STABLE"}

        exp_df['year_month'] = exp_df['date'].dt.to_period('M')
        
        # Gom nhóm và điền đầy các tháng bị khuyết (nếu có tháng chi tiêu = 0)
        monthly = exp_df.groupby('year_month')['amount'].sum()
        full_period_idx = pd.period_range(start=monthly.index.min(), end=monthly.index.max(), freq='M')
        monthly = monthly.reindex(full_period_idx, fill_value=0.0).reset_index()
        monthly.columns = ['year_month', 'amount']
        monthly['year_month'] = monthly['year_month'].astype(str)

        # Phần trăm không xác định khi tháng trước bằng 0 và tháng này dương.
        # Giữ giá trị null cho trường hợp đó, nhưng vẫn xác định chiều theo số tiền.
        pct_changes: list[float | None] = [0.0]
        amounts = [float(amount) for amount in monthly['amount'].tolist()]
        for previous, current in zip(amounts[:-1], amounts[1:]):
            pct_change: float | None
            if previous > 0:
                pct_change = round((current - previous) / previous * 100, 2)
            elif current == 0:
                pct_change = 0.0
            else:
                pct_change = None
            pct_changes.append(pct_change)
        monthly['pct_change'] = pd.Series(
            pct_changes, index=monthly.index, dtype=object
        )

        latest_change = monthly.iloc[-1]['pct_change'] if len(monthly) >= 2 else 0.0
        if len(monthly) >= 2:
            previous_amount = monthly.iloc[-2]['amount']
            latest_amount = monthly.iloc[-1]['amount']
            if previous_amount == 0 and latest_amount > 0:
                direction = "INCREASING"
            elif latest_change is not None and latest_change > 5:
                direction = "INCREASING"
            elif latest_change is not None and latest_change < -5:
                direction = "DECREASING"
            else:
                direction = "STABLE"
        else:
            direction = "STABLE"

        return {
            "monthly_trend": monthly.to_dict(orient='records'),
            "mom_change_percent": latest_change,
            "trend_direction": direction
        }
