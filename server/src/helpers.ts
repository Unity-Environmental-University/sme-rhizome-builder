/**
 * Shared route helpers for Hono routes.
 * Extracted from repeated patterns across assignments, courses, modules, bearings, log, concierge.
 */

import type { Context } from "hono"
import type postgres from "postgres"
import * as q from "./db/queries.js"

type Sql = postgres.Sql

/**
 * Parse a numeric param or query value. Returns the number, or null if missing/NaN.
 */
export function numParam(raw: string | undefined): number | null {
  if (raw == null) return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}

/**
 * Fetch bearings for a course with their statements and delta attached.
 * Used in courses/:id GET, bearings GET, and concierge POST.
 */
export async function enrichBearings(sql: Sql, courseId: number) {
  const bearings = await q.listBearings(sql, courseId)
  return Promise.all(
    bearings.map(async (b: Record<string, unknown>) => ({
      ...b,
      delta: (b.weight as number) - (b.likelihood as number),
      statements: await q.listStatements(sql, b.id as number),
    }))
  )
}
