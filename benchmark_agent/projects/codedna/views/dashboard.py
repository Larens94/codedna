"""views/dashboard.py -- Revenue dashboard render.

Depends on: analytics/revenue.py :: get_revenue_rows(), get_monthly_totals()
Exports:
    register(app) -> None
    render(year) -> str (HTML)
Used by: app.py :: create_app()
"""
from analytics.revenue import get_revenue_rows, get_monthly_totals

def register(app):
    @app.route("/dashboard")
    def dashboard():
        return render()

def render(year=None):
    rows = get_revenue_rows(year)
    totals = get_monthly_totals(year)
    return f"<h1>Dashboard</h1><pre>{totals}</pre>"
