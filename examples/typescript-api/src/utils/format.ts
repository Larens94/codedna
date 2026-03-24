/**
 * format.ts — Currency, date, and string formatting utilities.
 *
 * exports: formatCurrency(amountCents, currency): string | formatDate(date, locale): string
 *          truncate(text, maxLen, suffix): string | formatUserLabel(name, email): string
 * used_by: src/services/revenue.ts → monthlyRevenue, topCustomers | src/routes.ts → (indirect)
 * rules:   formatCurrency expects cents (number), not dollars — always pass raw cents.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */

const CURRENCY_SYMBOLS: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
};

export function formatCurrency(amountCents: number, currency = "USD"): string {
  const symbol = CURRENCY_SYMBOLS[currency] ?? `${currency} `;
  return `${symbol}${(amountCents / 100).toFixed(2)}`;
}

export function formatDate(date: Date, locale = "en-US"): string {
  return date.toLocaleDateString(locale, { year: "numeric", month: "2-digit", day: "2-digit" });
}

export function truncate(text: string, maxLen = 80, suffix = "..."): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen - suffix.length) + suffix;
}

export function formatUserLabel(name: string, email: string): string {
  const clean = name.trim();
  return clean.length > 0 ? `${clean} <${email}>` : email;
}
