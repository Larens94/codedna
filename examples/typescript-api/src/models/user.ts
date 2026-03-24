/**
 * user.ts — User and Invoice types with suspension helpers.
 *
 * exports: User | Invoice | isSuspended(user): boolean | displayName(user): string
 * used_by: src/services/revenue.ts → monthlyRevenue, topCustomers | src/routes.ts → getActiveUsers
 * rules:   always use isSuspended() to check suspension — never read suspendedAt directly.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */

export interface User {
  id: number;
  email: string;
  name: string;
  isActive: boolean;
  suspendedAt: Date | null;
}

export interface Invoice {
  id: number;
  userId: number;
  amountCents: number;
  paid: boolean;
  createdAt: Date;
}

export function isSuspended(user: User): boolean {
  return user.suspendedAt !== null;
}

export function displayName(user: User): string {
  const clean = user.name.trim();
  return clean.length > 0 ? clean : user.email.split("@")[0];
}
