import { Hono } from "hono"
import { getDb } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const logRoutes = new Hono<AuthEnv>()
logRoutes.use("*", jwtRequired)

logRoutes.get("/:assignmentId", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!q.getAssignment(db, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const entries = q.listLog(db, "assignment", assignmentId)
  return c.json(entries)
})

logRoutes.post("/:assignmentId", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!q.getAssignment(db, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const { action_type, content = "", replied_to } = body
  if (!action_type) return c.json({ error: "action_type required" }, 400)
  const entry = q.appendLog(db, userId, "assignment", assignmentId, action_type, content, replied_to)
  return c.json(entry, 201)
})
