import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"
import { numParam, enrichBearings } from "../helpers.js"

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
  const course = await q.createCourse(sql, c.get("userId"), body.courseCode, body.courseTitle, body.learningOutcomes, body.canvasCourseId, body.periodType)
  return c.json(course, 201)
})

courseRoutes.get("/:courseId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = numParam(c.req.param("courseId"))
  if (!courseId) return c.json({ error: "Invalid courseId" }, 400)
  const course = await q.getCourse(sql, courseId, userId)
  if (!course) return c.json({ error: "Not found" }, 404)

  const [outcomes, bearingList] = await Promise.all([
    q.listLearningOutcomes(sql, courseId),
    enrichBearings(sql, courseId),
  ])
  return c.json({ ...course, learningOutcomeRows: outcomes, bearings: bearingList })
})

courseRoutes.patch("/:courseId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = numParam(c.req.param("courseId"))
  if (!courseId) return c.json({ error: "Invalid courseId" }, 400)
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const course = await q.updateCourse(sql, courseId, body.courseCode, body.courseTitle, body.learningOutcomes, body.canvasCourseId)
  return c.json(course)
})

courseRoutes.get("/:courseId/modules", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const courseId = numParam(c.req.param("courseId"))
  if (!courseId) return c.json({ error: "Invalid courseId" }, 400)
  if (!await q.getCourse(sql, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const modules = await q.listModules(sql, courseId)
  return c.json(modules)
})
