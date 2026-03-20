import { Hono } from "hono"
import { getDb } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"

export const courseRoutes = new Hono<AuthEnv>()
courseRoutes.use("*", jwtRequired)

function courseDict(course: Record<string, unknown>, outcomeRows: Record<string, unknown>[], bearings: Record<string, unknown>[], statements: Record<string, unknown>[]) {
  const bearingList = bearings.map(b => ({
    ...b,
    delta: (b.weight as number) - (b.likelihood as number),
    statements: statements.filter(s => s.bearing_id === b.id),
  }))
  return { ...course, learning_outcome_rows: outcomeRows, bearings: bearingList }
}

courseRoutes.get("/", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courses = q.listCourses(db, userId)
  return c.json(courses)
})

courseRoutes.post("/", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const body = await c.req.json()
  const course = q.createCourse(db, userId, body.course_code, body.course_title, body.learning_outcomes, body.canvas_course_id, body.period_type)
  return c.json(course, 201)
})

courseRoutes.get("/:courseId", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  const course = q.getCourse(db, courseId, userId)
  if (!course) return c.json({ error: "Not found" }, 404)
  const outcomes = q.listLearningOutcomes(db, courseId)
  const bearings = q.listBearings(db, courseId)
  const statements = bearings.flatMap(b => q.listStatements(db, b.id as number))
  return c.json(courseDict(course, outcomes, bearings, statements))
})

courseRoutes.patch("/:courseId", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  if (!q.getCourse(db, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const body = await c.req.json()
  const course = q.updateCourse(db, courseId, body.course_code, body.course_title, body.learning_outcomes, body.canvas_course_id)
  return c.json(course)
})

courseRoutes.get("/:courseId/modules", (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const courseId = Number(c.req.param("courseId"))
  if (!q.getCourse(db, courseId, userId)) return c.json({ error: "Not found" }, 404)
  const modules = q.listModules(db, courseId)
  return c.json(modules)
})
