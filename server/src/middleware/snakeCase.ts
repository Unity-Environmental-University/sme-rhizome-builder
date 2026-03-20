/**
 * Response middleware — converts camelCase keys to snake_case.
 * Keeps the frontend compatible with the Flask API contract
 * without touching the query layer or route handlers.
 */

import { createMiddleware } from "hono/factory"

function toSnake(s: string): string {
  return s.replace(/[A-Z]/g, c => "_" + c.toLowerCase())
}

function snakify(val: unknown): unknown {
  if (Array.isArray(val)) return val.map(snakify)
  if (val !== null && typeof val === "object") {
    return Object.fromEntries(
      Object.entries(val as Record<string, unknown>).map(([k, v]) => [toSnake(k), snakify(v)])
    )
  }
  return val
}

export const snakeCaseResponse = createMiddleware(async (c, next) => {
  await next()
  const ct = c.res.headers.get("content-type") ?? ""
  if (!ct.includes("application/json")) return
  const body = await c.res.json()
  c.res = new Response(JSON.stringify(snakify(body)), {
    status: c.res.status,
    headers: c.res.headers,
  })
})
