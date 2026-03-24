import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"
import { numParam, enrichBearings } from "../helpers.js"

export const bearingRoutes = new Hono<AuthEnv>()
bearingRoutes.use("*", jwtRequired)

bearingRoutes.get("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = numParam(c.req.query("course_id"))
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "Not found" }, 404)
  return c.json(await enrichBearings(sql, courseId))
})

bearingRoutes.post("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const body = await c.req.json()
  const { course_id, text, weight = 0.5, likelihood = 0.5, learning_outcome_id } = body
  if (!course_id || !text) return c.json({ error: "course_id and text required" }, 400)
  if (!await q.getCourse(sql, course_id, userId)) return c.json({ error: "Not found" }, 404)
  const bearing = await q.createBearing(sql, course_id, text, weight, likelihood, learning_outcome_id)
  return c.json({ ...bearing, delta: weight - likelihood, statements: [] }, 201)
})

bearingRoutes.patch("/:bearingId", async (c) => {
  const sql = getSql()
  const bearingId = numParam(c.req.param("bearingId"))
  if (!bearingId) return c.json({ error: "Invalid bearingId" }, 400)
  const body = await c.req.json()
  const bearing = await q.updateBearing(sql, bearingId, body)
  if (!bearing) return c.json({ error: "Not found" }, 404)
  const statements = await q.listStatements(sql, bearingId)
  return c.json({ ...bearing, delta: (bearing.weight as number) - (bearing.likelihood as number), statements })
})

bearingRoutes.delete("/:bearingId", async (c) => {
  const sql = getSql()
  const bearingId = numParam(c.req.param("bearingId"))
  if (!bearingId) return c.json({ error: "Invalid bearingId" }, 400)
  if (!await q.getBearing(sql, bearingId)) return c.json({ error: "Not found" }, 404)
  await q.deleteBearing(sql, bearingId)
  return c.json({ ok: true })
})

bearingRoutes.post("/:bearingId/statements", async (c) => {
  const sql = getSql()
  const bearingId = numParam(c.req.param("bearingId"))
  if (!bearingId) return c.json({ error: "Invalid bearingId" }, 400)
  if (!await q.getBearing(sql, bearingId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  if (!body.text) return c.json({ error: "text required" }, 400)
  const statement = await q.createStatement(sql, bearingId, body.text)
  return c.json(statement, 201)
})

bearingRoutes.patch("/statements/:statementId", async (c) => {
  const sql = getSql()
  const statementId = numParam(c.req.param("statementId"))
  if (!statementId) return c.json({ error: "Invalid statementId" }, 400)
  const body = await c.req.json()
  const statement = await q.updateStatement(sql, statementId, body)
  if (!statement) return c.json({ error: "Not found" }, 404)
  return c.json(statement)
})
