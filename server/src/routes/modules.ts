import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const moduleRoutes = new Hono<AuthEnv>()
moduleRoutes.use("*", jwtRequired)

moduleRoutes.get("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = Number(c.req.query("course_id"))
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "not found" }, 404)
  const modules = await q.listModules(sql, courseId)
  return c.json({ modules })
})

moduleRoutes.post("/", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const body = await c.req.json()
  const { course_id, title = "", description = "", position = 0, outcome_ids = [], canvas_module_id } = body
  if (!course_id) return c.json({ error: "course_id required" }, 400)
  if (!await q.getCourse(sql, course_id, userId)) return c.json({ error: "not found" }, 404)
  const module_ = await q.createModule(sql, course_id, title, description, position, outcome_ids, canvas_module_id)
  return c.json(module_, 201)
})

moduleRoutes.patch("/:moduleId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const moduleId = Number(c.req.param("moduleId"))
  const body = await c.req.json()
  const courseId = Number(body.course_id)
  if (!courseId) return c.json({ error: "course_id required" }, 400)
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "not found" }, 404)
  const module_ = await q.updateModule(sql, moduleId, courseId, body)
  if (!module_) return c.json({ error: "not found" }, 404)
  return c.json(module_)
})
