"""dashboard.py — Render monthly revenue KPI dashboard as HTML.

exports: render(execute_query_func) -> str
used_by: none
rules:   execute_query_func must return list[dict] with keys: month, revenue, cost.
         revenue and cost are int (not Decimal) — see schema.sql.
         calculate_kpi() handles normalization, margins, and formatting — do not inline.
agent:   claude-haiku-4-5-20251001 | anthropic | 2026-03-27 | migrated docstring from v0.7 to v0.8 format
"""

from .utils import calculate_kpi, format_currency


def render(execute_query_func: callable) -> str:
    """Main entry point called by the view engine.

    Args:
        execute_query_func: callable(sql: str) -> list[dict]

    Returns:
        Rendered HTML string with KPI cards and revenue table.

    Depends:
        utils.calculate_kpi — returns dict with 'total', 'average', 'margin_pct'
        schema.sql — orders table (month: str, revenue: int, cost: int)

    Modifies:
        Nothing (read-only rendering).
    """
    rows = execute_query_func(
        "SELECT month, revenue, cost FROM orders ORDER BY month"
        # revenue, cost are int — see schema.sql; do NOT cast to Decimal
    )

    # calculate_kpi handles normalization and formatting — see utils.py
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
