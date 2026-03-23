import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const assignmentRoutes = new Hono<AuthEnv>()
assignmentRoutes.use("*", jwtRequired)

assignmentRoutes.get("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = Number(c.req.query("course_id"))
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  const assignments = await q.listAssignments(sql, courseId, userId)
  return c.json({ assignments })
})

assignmentRoutes.post("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const body = await c.req.json()
  const { course_id, module_label, title = "New Assignment" } = body
  if (!course_id || !module_label) return c.json({ error: "course_id and module_label required" }, 400)
  const position = await q.nextPositionInModule(sql, course_id, userId, module_label)
  const assignment = await q.createAssignment(sql, userId, course_id, module_label, title, position)
  return c.json(assignment, 201)
})

assignmentRoutes.patch("/:assignmentId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!await q.getAssignment(sql, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const assignment = await q.updateAssignment(sql, assignmentId, userId, body)
  return c.json(assignment)
})

assignmentRoutes.post("/:assignmentId/snapshots", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!await q.getAssignment(sql, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const snapshot = await q.createSnapshot(sql, assignmentId, userId, body.content, body.label)
  return c.json(snapshot, 201)
})

assignmentRoutes.get("/:assignmentId/snapshots", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!await q.getAssignment(sql, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const snapshots = await q.listSnapshots(sql, assignmentId)
  return c.json({ snapshots })
})
