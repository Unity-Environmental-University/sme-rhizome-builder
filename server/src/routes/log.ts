import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const logRoutes = new Hono<AuthEnv>()
logRoutes.use("*", jwtRequired)

logRoutes.get("/:assignmentId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!await q.getAssignment(sql, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const entries = await q.listLog(sql, "assignment", assignmentId)
  return c.json({ entries })
})

logRoutes.post("/:assignmentId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!await q.getAssignment(sql, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const { action_type, content = "", replied_to } = body
  if (!action_type) return c.json({ error: "action_type required" }, 400)
  const entry = await q.appendLog(sql, userId, "assignment", assignmentId, action_type, content, replied_to)
  return c.json(entry, 201)
})
