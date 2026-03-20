import { Hono } from "hono"
import { getDb } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const assignmentRoutes = new Hono<AuthEnv>()
assignmentRoutes.use("*", jwtRequired)

assignmentRoutes.get("/", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courseId = Number(c.req.query("course_id"))
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  return c.json(q.listAssignments(db, courseId, userId))
})

assignmentRoutes.post("/", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const body = await c.req.json()
  const { course_id, module_label, title = "New Assignment" } = body
  if (!course_id || !module_label) return c.json({ error: "course_id and module_label required" }, 400)
  const position = q.nextPositionInModule(db, course_id, userId, module_label)
  const assignment = q.createAssignment(db, userId, course_id, module_label, title, position)
  return c.json(assignment, 201)
})

assignmentRoutes.patch("/:assignmentId", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!q.getAssignment(db, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const assignment = q.updateAssignment(db, assignmentId, userId, body)
  return c.json(assignment)
})

assignmentRoutes.post("/:assignmentId/snapshots", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!q.getAssignment(db, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const snapshot = q.createSnapshot(db, assignmentId, userId, body.content, body.label)
  return c.json(snapshot, 201)
})

assignmentRoutes.get("/:assignmentId/snapshots", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")
  if (!q.getAssignment(db, assignmentId, userId)) return c.json({ error: "Not found" }, 404)
  const snapshots = q.listSnapshots(db, assignmentId)
  return c.json({ snapshots })
})
