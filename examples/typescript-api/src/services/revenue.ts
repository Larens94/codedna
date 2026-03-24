/**
 * revenue.ts — Monthly/annual revenue aggregation from paid invoices.
 *
 * exports: monthlyRevenue(year, month, users): Promise<object>
 *          annualSummary(year, users): Promise<object[]>
 *          topCustomers(year, month, users, limit): Promise<object[]>
 * used_by: src/routes.ts → router handlers
 * rules:   getInvoicesForPeriod returns ALL invoices including suspended users —
 *          always pass a pre-filtered users array. Filtering happens via activeIds set.
 *          message: "getInvoicesForPeriod is a stub — when replaced with real DB call,
 *                    ensure the WHERE clause does not silently include suspended users"
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */

import { Invoice, User, isSuspended } from "../models/user";
import { formatCurrency } from "../utils/format";

// NOTE: returns ALL invoices including suspended users — callers must filter
async function getInvoicesForPeriod(year: number, month: number): Promise<Invoice[]> {
  const start = new Date(year, month - 1, 1);
  const end = new Date(year, month, 1);
  // db call placeholder
  return [];
}

export async function monthlyRevenue(year: number, month: number, users: User[]) {
  const activeIds = new Set(users.filter(u => !isSuspended(u)).map(u => u.id));
  const invoices = await getInvoicesForPeriod(year, month);
  const filtered = invoices.filter(inv => activeIds.has(inv.userId));
  const totalCents = filtered.reduce((sum, inv) => sum + inv.amountCents, 0);
  return {
    year,
    month,
    totalCents,
    totalFormatted: formatCurrency(totalCents),
    invoiceCount: filtered.length,
  };
}

export async function annualSummary(year: number, users: User[]) {
  const months = Array.from({ length: 12 }, (_, i) => i + 1);
  return Promise.all(months.map(m => monthlyRevenue(year, m, users)));
}

export async function topCustomers(year: number, month: number, users: User[], limit = 10) {
  const activeMap = new Map(users.filter(u => !isSuspended(u)).map(u => [u.id, u]));
  const invoices = await getInvoicesForPeriod(year, month);
  const totals = new Map<number, number>();
  for (const inv of invoices) {
    if (activeMap.has(inv.userId)) {
      totals.set(inv.userId, (totals.get(inv.userId) ?? 0) + inv.amountCents);
    }
  }
  return [...totals.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([id, cents]) => ({ user: activeMap.get(id)!.name, total: formatCurrency(cents) }));
}
