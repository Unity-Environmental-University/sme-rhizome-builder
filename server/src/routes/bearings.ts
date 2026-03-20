import { Hono } from "hono"
import { getDb } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const bearingRoutes = new Hono<AuthEnv>()
bearingRoutes.use("*", jwtRequired)

function bearingDict(b: Record<string, unknown>, statements: Record<string, unknown>[]) {
  return {
    ...b,
    delta: (b.weight as number) - (b.likelihood as number),
    statements,
  }
}

bearingRoutes.get("/", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courseId = Number(c.req.query("course_id"))
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  if (!q.getCourse(db, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const bearings = q.listBearings(db, courseId)
  return c.json(bearings.map(b => bearingDict(b, q.listStatements(db, b.id as number))))
})

bearingRoutes.post("/", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const body = await c.req.json()
  const { course_id, text, weight = 0.5, likelihood = 0.5, learning_outcome_id } = body
  if (!course_id || !text) return c.json({ error: "course_id and text required" }, 400)
  if (!q.getCourse(db, course_id, userId)) return c.json({ error: "Not found" }, 404)
  const bearing = q.createBearing(db, course_id, text, weight, likelihood, learning_outcome_id)
  return c.json(bearingDict(bearing, []), 201)
})

bearingRoutes.patch("/:bearingId", async (c) => {
  const db = getDb()
  const bearingId = Number(c.req.param("bearingId"))
  const body = await c.req.json()
  const bearing = q.updateBearing(db, bearingId, body)
  if (!bearing) return c.json({ error: "Not found" }, 404)
  return c.json(bearingDict(bearing, q.listStatements(db, bearingId)))
})

bearingRoutes.delete("/:bearingId", (c) => {
  const db = getDb()
  const bearingId = Number(c.req.param("bearingId"))
  if (!q.getBearing(db, bearingId)) return c.json({ error: "Not found" }, 404)
  q.deleteBearing(db, bearingId)
  return c.json({ ok: true })
})

bearingRoutes.post("/:bearingId/statements", async (c) => {
  const db = getDb()
  const bearingId = Number(c.req.param("bearingId"))
  if (!q.getBearing(db, bearingId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  if (!body.text) return c.json({ error: "text required" }, 400)
  const statement = q.createStatement(db, bearingId, body.text)
  return c.json(statement, 201)
})

bearingRoutes.patch("/statements/:statementId", async (c) => {
  const db = getDb()
  const statementId = Number(c.req.param("statementId"))
  const body = await c.req.json()
  const statement = q.updateStatement(db, statementId, body)
  if (!statement) return c.json({ error: "Not found" }, 404)
  return c.json(statement)
})
