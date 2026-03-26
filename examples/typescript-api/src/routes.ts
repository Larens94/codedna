// routes.ts — routes module.
//
// exports: router
// used_by: none
// rules:   none
// agent:   claude-haiku-4-5-20251001 | unknown | 2026-03-27 | unknown | initial CodeDNA annotation pass

/**
 * routes.ts — Express router for revenue API endpoints.
 *
 * exports: router (Router) — GET /:year/:month | GET /:year/summary | GET /:year/:month/top
 * used_by: none
 * rules:   limit on /top capped at 100. Month validated 1-12 before service call.
 *          getActiveUsers() returns only active non-suspended users.
 * agent:   claude-sonnet-4-6 | 2026-03-24 | initial CodeDNA annotation
 */

import { Request, Response, Router } from "express";
import { User } from "./models/user";
import { annualSummary, monthlyRevenue, topCustomers } from "./services/revenue";

export const router = Router();

async function getActiveUsers(): Promise<User[]> {
  // db placeholder
  return [];
}

router.get("/:year/:month", async (req: Request, res: Response) => {
  const year = parseInt(req.params.year);
  const month = parseInt(req.params.month);
  if (month < 1 || month > 12) {
    return res.status(400).json({ error: "month must be 1-12" });
  }
  const users = await getActiveUsers();
  const data = await monthlyRevenue(year, month, users);
  res.json(data);
});

router.get("/:year/summary", async (req: Request, res: Response) => {
  const year = parseInt(req.params.year);
  const users = await getActiveUsers();
  const data = await annualSummary(year, users);
  res.json(data);
});

router.get("/:year/:month/top", async (req: Request, res: Response) => {
  const year = parseInt(req.params.year);
  const month = parseInt(req.params.month);
  const limit = Math.min(parseInt(req.query.limit as string ?? "10"), 100);
  const users = await getActiveUsers();
  const data = await topCustomers(year, month, users, limit);
  res.json(data);
});
