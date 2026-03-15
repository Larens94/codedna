# === CODEDNA:0.2 ==============================================
# FILE: dashboard.py
# PURPOSE: Monthly revenue KPI dashboard with chart and table
# DEPENDS_ON: utils.py → calculate_kpi(), format_currency()
# EXPORTS: render(execute_query_func) → HTML string
# STYLE: tailwind, chart.js
# DB_TABLES: orders (month, revenue, cost)
# LAST_MODIFIED: added Level 2 CodeDNA inline hyperlinks
# ==============================================================

from .utils import calculate_kpi, format_currency


def render(execute_query_func: callable) -> str:
    """
    Main entry point called by the view engine.

    Args:
        execute_query_func: callable(sql: str) -> list[dict]
    Returns:
        Rendered HTML string

    # @SEE: utils.py → calculate_kpi() (returns dict with 'total', 'average', 'margin_pct')
    # @REQUIRES-READ: schema.sql → orders (month: str, revenue: int, cost: int)
    # @MODIFIES-ALSO: utils.py → calculate_kpi() if changing column names in SQL
    """
    rows = execute_query_func(
        "SELECT month, revenue, cost FROM orders ORDER BY month"
        # @REQUIRES-READ: schema.sql → orders (column types are int, not decimal)
    )

    # → from utils.py: calculate_kpi handles normalization, margins, and formatting
    kpi = calculate_kpi(rows)

    rows_html = ""
    for r in rows:
        margin = r["revenue"] - r["cost"]
        margin_pct = round((margin / r["revenue"]) * 100, 1) if r["revenue"] else 0

        rows_html += f"""
        <tr class="even:bg-gray-50">
            <td class="px-4 py-2">{r['month']}</td>
            <td class="px-4 py-2 text-right">{format_currency(r['revenue'])}</td>
            <td class="px-4 py-2 text-right">{format_currency(r['cost'])}</td>
            <td class="px-4 py-2 text-right">{format_currency(margin)}</td>
            <td class="px-4 py-2 text-right text-green-600">{margin_pct}%</td>
        </tr>"""

    return f"""
    <div class="p-6">
        <h1 class="text-xl font-bold mb-4">Monthly Revenue Report</h1>
        <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-blue-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Total Revenue</p>
                <p class="text-2xl font-bold">{kpi['total']}</p>
            </div>
            <div class="bg-green-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Monthly Average</p>
                <p class="text-2xl font-bold">{kpi['average']}</p>
            </div>
            <div class="bg-purple-50 rounded-lg p-4">
                <p class="text-sm text-gray-500">Margin %</p>
                <p class="text-2xl font-bold">{kpi['margin_pct']}%</p>
            </div>
        </div>
        <table class="w-full text-sm">
            <thead>
                <tr class="bg-gray-100">
                    <th class="px-4 py-2 text-left">Month</th>
                    <th class="px-4 py-2 text-right">Revenue</th>
                    <th class="px-4 py-2 text-right">Cost</th>
                    <th class="px-4 py-2 text-right">Margin</th>
                    <th class="px-4 py-2 text-right">Margin %</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>"""
