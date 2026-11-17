from datetime import date


def format_vnd(amount: int) -> str:
    """Format an integer amount with the dashboard's Vietnamese currency style."""
    return f"{amount:,.0f} đ".replace(",", ".")


def format_date(value: date) -> str:
    """Format a date as day/month/year for display."""
    return value.strftime("%d/%m/%Y")
