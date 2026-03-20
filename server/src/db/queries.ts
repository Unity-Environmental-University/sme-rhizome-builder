/**
 * All SQL as named parameterized functions.
 * The garden wall: SQL lives here.
 * Returns plain objects (better-sqlite3 rows with .toJSON() applied).
 */

import type Database from "better-sqlite3"
import { v4 as uuidv4 } from "uuid"

// ── Users ─────────────────────────────────────────────────────────────────────

export function getUser(db: Database.Database, userId: number) {
  return db.prepare("SELECT * FROM users WHERE id = ?").get(userId) as Record<string, unknown> | undefined
}

export function getUserByCanvasId(db: Database.Database, canvasUserId: string) {
  return db.prepare("SELECT * FROM users WHERE canvas_user_id = ?").get(canvasUserId) as Record<string, unknown> | undefined
}

export function upsertUser(
  db: Database.Database,
  canvasUserId: string,
  name: string,
  email: string,
  canvasAccessToken?: string,
  canvasRefreshToken?: string,
  tokenExpiresAt?: string,
  canvasBaseUrl = "https://unity.instructure.com",
) {
  const existing = getUserByCanvasId(db, canvasUserId)
  if (existing) {
    db.prepare(
      `UPDATE users SET name=?, email=?, canvas_access_token=?,
       canvas_refresh_token=?, token_expires_at=?, canvas_base_url=?
       WHERE canvas_user_id=?`
    ).run(name, email, canvasAccessToken ?? null, canvasRefreshToken ?? null, tokenExpiresAt ?? null, canvasBaseUrl, canvasUserId)
  } else {
    db.prepare(
      `INSERT INTO users (canvas_user_id, name, email, canvas_access_token,
       canvas_refresh_token, token_expires_at, canvas_base_url)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    ).run(canvasUserId, name, email, canvasAccessToken ?? null, canvasRefreshToken ?? null, tokenExpiresAt ?? null, canvasBaseUrl)
  }
  return getUserByCanvasId(db, canvasUserId)!
}

export function createDemoUser(db: Database.Database) {
  const existing = getUserByCanvasId(db, "demo")
  if (existing) return existing
  db.prepare(
    "INSERT INTO users (canvas_user_id, name, email) VALUES ('demo', 'Demo User', 'demo@localhost')"
  ).run()
  return getUserByCanvasId(db, "demo")!
}

// ── Courses ───────────────────────────────────────────────────────────────────

export function getCourse(db: Database.Database, courseId: number, userId: number) {
  return db.prepare("SELECT * FROM courses WHERE id = ? AND user_id = ?").get(courseId, userId) as Record<string, unknown> | undefined
}

export function listCourses(db: Database.Database, userId: number) {
  return db.prepare("SELECT * FROM courses WHERE user_id = ? ORDER BY created_at DESC").all(userId) as Record<string, unknown>[]
}

export function createCourse(
  db: Database.Database,
  userId: number,
  courseCode = "",
  courseTitle = "",
  learningOutcomes = "",
  canvasCourseId?: string,
  periodType = "Week",
) {
  const result = db.prepare(
    `INSERT INTO courses (user_id, course_code, course_title, learning_outcomes, canvas_course_id, period_type)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(userId, courseCode, courseTitle, learningOutcomes, canvasCourseId ?? null, periodType)
  return db.prepare("SELECT * FROM courses WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function updateCourse(
  db: Database.Database,
  courseId: number,
  courseCode: string,
  courseTitle: string,
  learningOutcomes: string,
  canvasCourseId?: string,
) {
  db.prepare(
    `UPDATE courses SET course_code=?, course_title=?, learning_outcomes=?, canvas_course_id=? WHERE id=?`
  ).run(courseCode, courseTitle, learningOutcomes, canvasCourseId ?? null, courseId)
  return db.prepare("SELECT * FROM courses WHERE id = ?").get(courseId) as Record<string, unknown>
}

export function listLearningOutcomes(db: Database.Database, courseId: number) {
  return db.prepare("SELECT * FROM learning_outcomes WHERE course_id = ? ORDER BY position").all(courseId) as Record<string, unknown>[]
}

export function getLearningOutcomesByIds(db: Database.Database, ids: number[], courseId: number) {
  if (!ids.length) return []
  const placeholders = ids.map(() => "?").join(",")
  return db.prepare(
    `SELECT * FROM learning_outcomes WHERE id IN (${placeholders}) AND course_id = ?`
  ).all(...ids, courseId) as Record<string, unknown>[]
}

export function createLearningOutcome(
  db: Database.Database,
  courseId: number,
  text: string,
  position: number,
  canvasOutcomeId?: string,
) {
  const result = db.prepare(
    "INSERT INTO learning_outcomes (course_id, text, position, canvas_outcome_id) VALUES (?, ?, ?, ?)"
  ).run(courseId, text, position, canvasOutcomeId ?? null)
  return db.prepare("SELECT * FROM learning_outcomes WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

// ── Modules ───────────────────────────────────────────────────────────────────

export function listModules(db: Database.Database, courseId: number) {
  return db.prepare("SELECT * FROM modules WHERE course_id = ? ORDER BY position").all(courseId) as Record<string, unknown>[]
}

export function getModule(db: Database.Database, moduleId: number, courseId: number) {
  return db.prepare("SELECT * FROM modules WHERE id = ? AND course_id = ?").get(moduleId, courseId) as Record<string, unknown> | undefined
}

export function createModule(
  db: Database.Database,
  courseId: number,
  title: string,
  description = "",
  position = 0,
  outcomeIds: number[] = [],
  canvasModuleId?: string,
) {
  const result = db.prepare(
    `INSERT INTO modules (course_id, canvas_module_id, title, description, position, outcome_ids)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(courseId, canvasModuleId ?? null, title, description, position, JSON.stringify(outcomeIds))
  return db.prepare("SELECT * FROM modules WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function updateModule(
  db: Database.Database,
  moduleId: number,
  courseId: number,
  fields: Partial<{ title: string; description: string; position: number; outcome_ids: number[]; canvas_module_id: string }>,
) {
  const allowed = ["title", "description", "position", "outcome_ids", "canvas_module_id"] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) {
    if (key in fields) {
      updates[key] = key === "outcome_ids" ? JSON.stringify(fields[key]) : fields[key]
    }
  }
  if (!Object.keys(updates).length) return getModule(db, moduleId, courseId)
  const setClause = Object.keys(updates).map(k => `${k} = ?`).join(", ")
  db.prepare(`UPDATE modules SET ${setClause} WHERE id = ? AND course_id = ?`).run(...Object.values(updates), moduleId, courseId)
  return getModule(db, moduleId, courseId)
}

// ── Assignments ───────────────────────────────────────────────────────────────

export function getAssignment(db: Database.Database, assignmentId: string, userId: number) {
  return db.prepare("SELECT * FROM assignments WHERE id = ? AND user_id = ?").get(assignmentId, userId) as Record<string, unknown> | undefined
}

export function listAssignments(db: Database.Database, courseId: number, userId: number) {
  return db.prepare(
    `SELECT * FROM assignments WHERE course_id = ? AND user_id = ?
     ORDER BY CASE WHEN position IS NULL THEN 1 ELSE 0 END, position, created_at`
  ).all(courseId, userId) as Record<string, unknown>[]
}

export function nextPositionInModule(db: Database.Database, courseId: number, userId: number, moduleLabel: string) {
  const row = db.prepare(
    `SELECT MAX(position) as max_pos FROM assignments
     WHERE course_id = ? AND user_id = ? AND module_label = ? AND position IS NOT NULL`
  ).get(courseId, userId, moduleLabel) as { max_pos: number | null }
  return row.max_pos != null ? row.max_pos + 1 : 0
}

export function createAssignment(
  db: Database.Database,
  userId: number,
  courseId: number,
  moduleLabel: string,
  title: string,
  position?: number,
) {
  const id = uuidv4()
  db.prepare(
    "INSERT INTO assignments (id, user_id, course_id, module_label, title, position) VALUES (?, ?, ?, ?, ?, ?)"
  ).run(id, userId, courseId, moduleLabel, title, position ?? null)
  return getAssignment(db, id, userId)!
}

export function updateAssignment(
  db: Database.Database,
  assignmentId: string,
  userId: number,
  fields: Partial<{ title: string; module_label: string; position: number }>,
) {
  const allowed = ["title", "module_label", "position"] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) { if (key in fields) updates[key] = fields[key] }
  if (!Object.keys(updates).length) return getAssignment(db, assignmentId, userId)
  const setClause = Object.keys(updates).map(k => `${k} = ?`).join(", ")
  db.prepare(`UPDATE assignments SET ${setClause} WHERE id = ? AND user_id = ?`).run(...Object.values(updates), assignmentId, userId)
  return getAssignment(db, assignmentId, userId)
}

// ── Snapshots ─────────────────────────────────────────────────────────────────

export function createSnapshot(
  db: Database.Database,
  assignmentId: string,
  userId: number,
  content: Record<string, unknown>,
  label?: string,
) {
  const result = db.prepare(
    "INSERT INTO snapshots (assignment_id, user_id, content, label) VALUES (?, ?, ?, ?)"
  ).run(assignmentId, userId, JSON.stringify(content), label ?? null)
  return db.prepare("SELECT * FROM snapshots WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function listSnapshots(db: Database.Database, assignmentId: string) {
  return db.prepare("SELECT * FROM snapshots WHERE assignment_id = ? ORDER BY snapshot_at").all(assignmentId) as Record<string, unknown>[]
}

export function latestSnapshot(db: Database.Database, assignmentId: string) {
  return db.prepare("SELECT * FROM snapshots WHERE assignment_id = ? ORDER BY snapshot_at DESC LIMIT 1").get(assignmentId) as Record<string, unknown> | undefined
}

// ── Log ───────────────────────────────────────────────────────────────────────

export function listLog(db: Database.Database, contextType: string, contextId: string) {
  return db.prepare(
    "SELECT * FROM log_entries WHERE context_type = ? AND context_id = ? ORDER BY created_at"
  ).all(contextType, contextId) as Record<string, unknown>[]
}

export function appendLog(
  db: Database.Database,
  userId: number,
  contextType: string,
  contextId: string,
  actionType: string,
  content = "",
  repliedTo?: number,
) {
  const result = db.prepare(
    `INSERT INTO log_entries (user_id, context_type, context_id, action_type, content, replied_to)
     VALUES (?, ?, ?, ?, ?, ?)`
  ).run(userId, contextType, contextId, actionType, content, repliedTo ?? null)
  return db.prepare("SELECT * FROM log_entries WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function getLogEntry(db: Database.Database, entryId: number) {
  return db.prepare("SELECT * FROM log_entries WHERE id = ?").get(entryId) as Record<string, unknown> | undefined
}

// ── Bearings ──────────────────────────────────────────────────────────────────

export function listBearings(db: Database.Database, courseId: number) {
  return db.prepare("SELECT * FROM bearings WHERE course_id = ? ORDER BY created_at").all(courseId) as Record<string, unknown>[]
}

export function getBearing(db: Database.Database, bearingId: number) {
  return db.prepare("SELECT * FROM bearings WHERE id = ?").get(bearingId) as Record<string, unknown> | undefined
}

export function createBearing(
  db: Database.Database,
  courseId: number,
  text: string,
  weight = 0.5,
  likelihood = 0.5,
  learningOutcomeId?: number,
) {
  const result = db.prepare(
    `INSERT INTO bearings (course_id, learning_outcome_id, text, weight, likelihood)
     VALUES (?, ?, ?, ?, ?)`
  ).run(courseId, learningOutcomeId ?? null, text, weight, likelihood)
  return db.prepare("SELECT * FROM bearings WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function updateBearing(
  db: Database.Database,
  bearingId: number,
  fields: Partial<{ text: string; weight: number; likelihood: number }>,
) {
  const allowed = ["text", "weight", "likelihood"] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) { if (key in fields) updates[key] = fields[key] }
  if (!Object.keys(updates).length) return getBearing(db, bearingId)
  const setClause = Object.keys(updates).map(k => `${k} = ?`).join(", ")
  db.prepare(`UPDATE bearings SET ${setClause}, updated_at=datetime('now') WHERE id = ?`).run(...Object.values(updates), bearingId)
  return getBearing(db, bearingId)
}

export function deleteBearing(db: Database.Database, bearingId: number) {
  db.prepare("DELETE FROM bearings WHERE id = ?").run(bearingId)
}

export function listStatements(db: Database.Database, bearingId: number) {
  return db.prepare("SELECT * FROM bearing_statements WHERE bearing_id = ? ORDER BY created_at").all(bearingId) as Record<string, unknown>[]
}

export function getStatement(db: Database.Database, statementId: number) {
  return db.prepare("SELECT * FROM bearing_statements WHERE id = ?").get(statementId) as Record<string, unknown> | undefined
}

export function createStatement(db: Database.Database, bearingId: number, text: string) {
  const result = db.prepare("INSERT INTO bearing_statements (bearing_id, text) VALUES (?, ?)").run(bearingId, text)
  return db.prepare("SELECT * FROM bearing_statements WHERE id = ?").get(result.lastInsertRowid) as Record<string, unknown>
}

export function updateStatement(db: Database.Database, statementId: number, fields: Partial<{ text: string; observed: number | null }>) {
  const allowed = ["text", "observed"] as const
  const updates: Record<string, unknown> = {}
  for (const key of allowed) { if (key in fields) updates[key] = fields[key] }
  if (!Object.keys(updates).length) return getStatement(db, statementId)
  const setClause = Object.keys(updates).map(k => `${k} = ?`).join(", ")
  db.prepare(`UPDATE bearing_statements SET ${setClause} WHERE id = ?`).run(...Object.values(updates), statementId)
  return getStatement(db, statementId)
}
