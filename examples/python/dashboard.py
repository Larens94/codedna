"""python/dashboard.py — Render monthly revenue KPI dashboard as HTML.

exports: render(execute_query_func)
used_by: none
rules:   rules: |
  - The `render()` function must accept `execute_query_func` as a callable parameter and use it exclusively for all database operations; no direct database connections are permitted.
  - All output must be generated from the result of `execute_query_func()` calls; hardcoded data or external API calls are not allowed.
agent:   claude-haiku-4-5-20251001 | 2026-03-27 | initial CodeDNA annotation pass
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

    Rules:   execute_query_func must return list[dict] with keys 'month', 'revenue', 'cost'; all numeric columns must be non-null integers
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
