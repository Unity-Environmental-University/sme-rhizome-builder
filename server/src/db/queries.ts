/**
 * All SQL as named parameterized functions.
 * The garden wall: SQL lives here. Business logic lives in routes.
 * Uses postgres.js tagged template literals — no string interpolation.
 */

import type postgres from "postgres"
import { v4 as uuidv4 } from "uuid"

type Sql = postgres.Sql

// ── Dynamic SET builder ──────────────────────────────────────────────────────

type FieldSpec = Record<string, unknown>

/**
 * Build a parameterized SET clause from a partial fields object.
 * Returns null if no fields to set. Uses `"observed" in fields` style
 * checks for fields where undefined vs missing matters.
 */
export function buildSetClause(
  fields: FieldSpec,
  extraSets: string[] = [],
): { clause: string; vals: unknown[] } | null {
  const sets: string[] = []
  const vals: unknown[] = []
  for (const [col, val] of Object.entries(fields)) {
    if (val !== undefined) {
      sets.push(`${col} = $${vals.push(val)}`)
    }
  }
  if (!sets.length && !extraSets.length) return null
  sets.push(...extraSets)
  return { clause: sets.join(", "), vals }
}

// ── Users ─────────────────────────────────────────────────────────────────────

export async function getUser(sql: Sql, userId: number) {
  const [row] = await sql`SELECT * FROM users WHERE id = ${userId}`
  return row ?? null
}

export async function getUserByCanvasId(sql: Sql, canvasUserId: string) {
  const [row] = await sql`SELECT * FROM users WHERE canvas_user_id = ${canvasUserId}`
  return row ?? null
}

export async function upsertUser(
  sql: Sql,
  canvasUserId: string,
  name: string,
  email: string,
  canvasAccessToken?: string,
  canvasRefreshToken?: string,
  tokenExpiresAt?: string,
  canvasBaseUrl = "https://unity.instructure.com",
) {
  const [row] = await sql`
    INSERT INTO users (canvas_user_id, name, email, canvas_access_token,
      canvas_refresh_token, token_expires_at, canvas_base_url)
    VALUES (${canvasUserId}, ${name}, ${email}, ${canvasAccessToken ?? null},
      ${canvasRefreshToken ?? null}, ${tokenExpiresAt ?? null}, ${canvasBaseUrl})
    ON CONFLICT (canvas_user_id) DO UPDATE SET
      name = EXCLUDED.name,
      email = EXCLUDED.email,
      canvas_access_token = EXCLUDED.canvas_access_token,
      canvas_refresh_token = EXCLUDED.canvas_refresh_token,
      token_expires_at = EXCLUDED.token_expires_at,
      canvas_base_url = EXCLUDED.canvas_base_url
    RETURNING *`
  return row
}

export async function createDemoUser(sql: Sql) {
  const [row] = await sql`
    INSERT INTO users (canvas_user_id, name, email)
    VALUES ('demo', 'Demo User', 'demo@localhost')
    ON CONFLICT (canvas_user_id) DO UPDATE SET name = EXCLUDED.name
    RETURNING *`
  return row
}

// ── Courses ───────────────────────────────────────────────────────────────────

export async function getCourse(sql: Sql, courseId: number, userId: number) {
  const [row] = await sql`SELECT * FROM courses WHERE id = ${courseId} AND user_id = ${userId}`
  return row ?? null
}

export async function listCourses(sql: Sql, userId: number) {
  return sql`SELECT * FROM courses WHERE user_id = ${userId} ORDER BY created_at DESC`
}

export async function createCourse(
  sql: Sql,
  userId: number,
  courseCode = "",
  courseTitle = "",
  learningOutcomes = "",
  canvasCourseId?: string,
  periodType = "Week",
) {
  const [row] = await sql`
    INSERT INTO courses (user_id, course_code, course_title, learning_outcomes, canvas_course_id, period_type)
    VALUES (${userId}, ${courseCode}, ${courseTitle}, ${learningOutcomes}, ${canvasCourseId ?? null}, ${periodType})
    RETURNING *`
  return row
}

export async function updateCourse(
  sql: Sql,
  courseId: number,
  courseCode: string,
  courseTitle: string,
  learningOutcomes: string,
  canvasCourseId?: string,
) {
  const [row] = await sql`
    UPDATE courses SET
      course_code = ${courseCode},
      course_title = ${courseTitle},
      learning_outcomes = ${learningOutcomes},
      canvas_course_id = ${canvasCourseId ?? null}
    WHERE id = ${courseId}
    RETURNING *`
  return row
}

export async function listLearningOutcomes(sql: Sql, courseId: number) {
  return sql`SELECT * FROM learning_outcomes WHERE course_id = ${courseId} ORDER BY position`
}

export async function getLearningOutcomesByIds(sql: Sql, ids: number[], courseId: number) {
  if (!ids.length) return []
  return sql`SELECT * FROM learning_outcomes WHERE id = ANY(${ids}) AND course_id = ${courseId}`
}

export async function createLearningOutcome(
  sql: Sql,
  courseId: number,
  text: string,
  position: number,
  canvasOutcomeId?: string,
) {
  const [row] = await sql`
    INSERT INTO learning_outcomes (course_id, text, position, canvas_outcome_id)
    VALUES (${courseId}, ${text}, ${position}, ${canvasOutcomeId ?? null})
    RETURNING *`
  return row
}

// ── Modules ───────────────────────────────────────────────────────────────────

export async function listModules(sql: Sql, courseId: number) {
  return sql`SELECT * FROM modules WHERE course_id = ${courseId} ORDER BY position`
}

export async function getModule(sql: Sql, moduleId: number, courseId: number) {
  const [row] = await sql`SELECT * FROM modules WHERE id = ${moduleId} AND course_id = ${courseId}`
  return row ?? null
}

export async function createModule(
  sql: Sql,
  courseId: number,
  title: string,
  description = "",
  position = 0,
  outcomeIds: number[] = [],
  canvasModuleId?: string,
) {
  const [row] = await sql`
    INSERT INTO modules (course_id, canvas_module_id, title, description, position, outcome_ids)
    VALUES (${courseId}, ${canvasModuleId ?? null}, ${title}, ${description}, ${position}, ${sql.json(outcomeIds)})
    RETURNING *`
  return row
}

export async function updateModule(
  sql: Sql,
  moduleId: number,
  courseId: number,
  fields: Partial<{ title: string; description: string; position: number; outcome_ids: number[]; canvas_module_id: string }>,
) {
  const mapped: FieldSpec = { ...fields }
  if (fields.outcome_ids !== undefined) mapped.outcome_ids = JSON.stringify(fields.outcome_ids)
  const built = buildSetClause(mapped)
  if (!built) return getModule(sql, moduleId, courseId)
  const { clause, vals } = built
  const [row] = await sql.unsafe(
    `UPDATE modules SET ${clause} WHERE id = $${vals.push(moduleId)} AND course_id = $${vals.push(courseId)} RETURNING *`,
    vals as any[],
  )
  return row ?? null
}

// ── Assignments ───────────────────────────────────────────────────────────────

export async function getAssignment(sql: Sql, assignmentId: string, userId: number) {
  const [row] = await sql`SELECT * FROM assignments WHERE id = ${assignmentId} AND user_id = ${userId}`
  return row ?? null
}

export async function listAssignments(sql: Sql, courseId: number, userId: number) {
  return sql`
    SELECT * FROM assignments WHERE course_id = ${courseId} AND user_id = ${userId}
    ORDER BY CASE WHEN position IS NULL THEN 1 ELSE 0 END, position, created_at`
}

export async function nextPositionInModule(sql: Sql, courseId: number, userId: number, moduleLabel: string) {
  const [row] = await sql`
    SELECT MAX(position) AS max_pos FROM assignments
    WHERE course_id = ${courseId} AND user_id = ${userId} AND module_label = ${moduleLabel} AND position IS NOT NULL`
  return row?.maxPos != null ? (row.maxPos as number) + 1 : 0
}

export async function createAssignment(
  sql: Sql,
  userId: number,
  courseId: number,
  moduleLabel: string,
  title: string,
  position?: number,
) {
  const id = uuidv4()
  const [row] = await sql`
    INSERT INTO assignments (id, user_id, course_id, module_label, title, position)
    VALUES (${id}, ${userId}, ${courseId}, ${moduleLabel}, ${title}, ${position ?? null})
    RETURNING *`
  return row
}

export async function updateAssignment(
  sql: Sql,
  assignmentId: string,
  userId: number,
  fields: Partial<{ title: string; module_label: string; position: number }>,
) {
  const built = buildSetClause(fields)
  if (!built) return getAssignment(sql, assignmentId, userId)
  const { clause, vals } = built
  const [row] = await sql.unsafe(
    `UPDATE assignments SET ${clause} WHERE id = $${vals.push(assignmentId)} AND user_id = $${vals.push(userId)} RETURNING *`,
    vals as any[],
  )
  return row ?? null
}

// ── Snapshots ─────────────────────────────────────────────────────────────────

export async function createSnapshot(
  sql: Sql,
  assignmentId: string,
  userId: number,
  content: Record<string, unknown>,
  label?: string,
) {
  const [row] = await sql`
    INSERT INTO snapshots (assignment_id, user_id, content, label)
    VALUES (${assignmentId}, ${userId}, ${sql.json(content as never)}, ${label ?? null})
    RETURNING *`
  return row
}

export async function listSnapshots(sql: Sql, assignmentId: string) {
  return sql`SELECT * FROM snapshots WHERE assignment_id = ${assignmentId} ORDER BY snapshot_at`
}

export async function latestSnapshot(sql: Sql, assignmentId: string) {
  const [row] = await sql`
    SELECT * FROM snapshots WHERE assignment_id = ${assignmentId}
    ORDER BY snapshot_at DESC LIMIT 1`
  return row ?? null
}

// ── Log ───────────────────────────────────────────────────────────────────────

export async function listLog(sql: Sql, contextType: string, contextId: string) {
  return sql`
    SELECT * FROM log_entries WHERE context_type = ${contextType} AND context_id = ${contextId}
    ORDER BY created_at`
}

export async function appendLog(
  sql: Sql,
  userId: number,
  contextType: string,
  contextId: string,
  actionType: string,
  content = "",
  repliedTo?: number,
) {
  const [row] = await sql`
    INSERT INTO log_entries (user_id, context_type, context_id, action_type, content, replied_to)
    VALUES (${userId}, ${contextType}, ${contextId}, ${actionType}, ${content}, ${repliedTo ?? null})
    RETURNING *`
  return row
}

export async function getLogEntry(sql: Sql, entryId: number) {
  const [row] = await sql`SELECT * FROM log_entries WHERE id = ${entryId}`
  return row ?? null
}

// ── Bearings ──────────────────────────────────────────────────────────────────

export async function listBearings(sql: Sql, courseId: number) {
  return sql`SELECT * FROM bearings WHERE course_id = ${courseId} ORDER BY created_at`
}

export async function getBearing(sql: Sql, bearingId: number) {
  const [row] = await sql`SELECT * FROM bearings WHERE id = ${bearingId}`
  return row ?? null
}

export async function createBearing(
  sql: Sql,
  courseId: number,
  text: string,
  weight = 0.5,
  likelihood = 0.5,
  learningOutcomeId?: number,
) {
  const [row] = await sql`
    INSERT INTO bearings (course_id, learning_outcome_id, text, weight, likelihood)
    VALUES (${courseId}, ${learningOutcomeId ?? null}, ${text}, ${weight}, ${likelihood})
    RETURNING *`
  return row
}

export async function updateBearing(
  sql: Sql,
  bearingId: number,
  fields: Partial<{ text: string; weight: number; likelihood: number }>,
) {
  const built = buildSetClause(fields, ["updated_at = now()"])
  if (!built) return getBearing(sql, bearingId)
  const { clause, vals } = built
  const [row] = await sql.unsafe(
    `UPDATE bearings SET ${clause} WHERE id = $${vals.push(bearingId)} RETURNING *`,
    vals as any[],
  )
  return row ?? null
}

export async function deleteBearing(sql: Sql, bearingId: number) {
  await sql`DELETE FROM bearings WHERE id = ${bearingId}`
}

export async function listStatements(sql: Sql, bearingId: number) {
  return sql`SELECT * FROM bearing_statements WHERE bearing_id = ${bearingId} ORDER BY created_at`
}

export async function getStatement(sql: Sql, statementId: number) {
  const [row] = await sql`SELECT * FROM bearing_statements WHERE id = ${statementId}`
  return row ?? null
}

export async function createStatement(sql: Sql, bearingId: number, text: string) {
  const [row] = await sql`
    INSERT INTO bearing_statements (bearing_id, text) VALUES (${bearingId}, ${text}) RETURNING *`
  return row
}

export async function updateStatement(
  sql: Sql,
  statementId: number,
  fields: Partial<{ text: string; observed: boolean | null }>,
) {
  // "observed" uses `in` check because null is a valid value (distinct from missing)
  const mapped: FieldSpec = {}
  if (fields.text !== undefined) mapped.text = fields.text
  if ("observed" in fields) mapped.observed = fields.observed ?? null
  const built = buildSetClause(mapped)
  if (!built) return getStatement(sql, statementId)
  const { clause, vals } = built
  const [row] = await sql.unsafe(
    `UPDATE bearing_statements SET ${clause} WHERE id = $${vals.push(statementId)} RETURNING *`,
    vals as any[],
  )
  return row ?? null
}
