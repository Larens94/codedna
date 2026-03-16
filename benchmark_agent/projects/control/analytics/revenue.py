from orders.orders import get_active_orders

def get_revenue_rows(year=None):
    orders = get_active_orders()
    if year:
        orders = [o for o in orders if o.get("year") == year]
    return orders

def get_monthly_totals(year=None):
    rows = get_revenue_rows(year)
    totals = {}
    for row in rows:
        month = row.get("month")
        totals[month] = totals.get(month, 0) + row.get("amount", 0)
    return totals
