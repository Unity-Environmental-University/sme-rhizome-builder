import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const courseRoutes = new Hono<AuthEnv>()
courseRoutes.use("*", jwtRequired)

courseRoutes.get("/", async (c) => {
  const sql = getSql()
  const courses = await q.listCourses(sql, c.get("userId"))
  return c.json({ courses })
})

courseRoutes.post("/", async (c) => {
  const sql = getSql()
  const body = await c.req.json()
  const course = await q.createCourse(sql, c.get("userId"), body.course_code, body.course_title, body.learning_outcomes, body.canvas_course_id, body.period_type)
  return c.json(course, 201)
})

courseRoutes.get("/:courseId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  const course = await q.getCourse(sql, courseId, userId)
  if (!course) return c.json({ error: "Not found" }, 404)

  const [outcomes, bearings] = await Promise.all([
    q.listLearningOutcomes(sql, courseId),
    q.listBearings(sql, courseId),
  ])
  const statements = (await Promise.all(bearings.map(b => q.listStatements(sql, b.id as number)))).flat()
  const bearingList = bearings.map((b: Record<string, unknown>) => ({
    ...b,
    delta: (b.weight as number) - (b.likelihood as number),
    statements: statements.filter((s: Record<string, unknown>) => s.bearingId === b.id),
  }))
  return c.json({ ...course, learningOutcomeRows: outcomes, bearings: bearingList })
})

courseRoutes.patch("/:courseId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const course = await q.updateCourse(sql, courseId, body.course_code, body.course_title, body.learning_outcomes, body.canvas_course_id)
  return c.json(course)
})

courseRoutes.get("/:courseId/modules", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const modules = await q.listModules(sql, courseId)
  return c.json(modules)
})
