/**
 * Concierge — responds to sme_anchor log entries with margin notes.
 * Same logic as Flask's /api/concierge/<assignment_id>.
 * alkahest-ts is a direct import here — no subprocess bridge needed.
 */

import { Hono } from "hono"
import { getDb } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"
import { callAi } from "../ai/index.js"
import { buildSystemPrompt, CONCIERGE_DECK } from "../ai/prompts.js"

export const conciergeRoutes = new Hono<AuthEnv>()
conciergeRoutes.use("*", jwtRequired)

conciergeRoutes.post("/:assignmentId", async (c) => {
  const db = getDb()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")

  const assignment = q.getAssignment(db, assignmentId, userId)
  if (!assignment) return c.json({ error: "Not found" }, 404)

  const body = await c.req.json()
  const { anchor_id, comment_id, endpoint, api_key, model } = body
  if (!anchor_id || !comment_id) return c.json({ error: "anchor_id and comment_id required" }, 400)

  const anchor = q.getLogEntry(db, Number(anchor_id))
  if (!anchor) return c.json({ error: "Anchor not found" }, 404)

  let anchorContent: Record<string, unknown> = {}
  try { anchorContent = JSON.parse(anchor.content as string) } catch {}

  // Gather context
  const snapshot = q.latestSnapshot(db, assignmentId)
  let draftHtml = ""
  if (snapshot) {
    const content = typeof snapshot.content === "string" ? JSON.parse(snapshot.content) : snapshot.content
    draftHtml = (content as Record<string, unknown>).description as string ?? ""
  }

  const course = q.getCourse(db, assignment.course_id as number, userId)
  let courseData: Record<string, unknown> | undefined
  if (course) {
    const outcomes = q.listLearningOutcomes(db, course.id as number)
    const bearings = q.listBearings(db, course.id as number)
    const statements = bearings.flatMap(b => q.listStatements(db, b.id as number))
    courseData = {
      ...course,
      learning_outcome_rows: outcomes,
      bearings: bearings.map(b => ({
        ...b,
        statements: statements.filter(s => s.bearing_id === b.id),
      })),
    }
  }

  const selectionText = anchorContent.text as string ?? ""
  const hasSelection = anchorContent.from != null && anchorContent.to != null

  const userMsg = hasSelection
    ? `The SME selected this passage and asked for help:\n\n"${selectionText}"\n\nFull draft:\n${draftHtml}`
    : `The SME asked for help with the whole draft:\n\n${draftHtml}`

  const systemPrompt = buildSystemPrompt(courseData as Parameters<typeof buildSystemPrompt>[0], CONCIERGE_DECK)
  const resolvedEndpoint = (endpoint ?? process.env.CONCIERGE_ENDPOINT ?? "local") as "local" | "anthropic" | "openai" | "ollama"

  let responseText: string
  try {
    responseText = await callAi({
      endpoint: resolvedEndpoint,
      systemPrompt,
      messages: [{ role: "user", content: userMsg }],
      apiKey: api_key ?? process.env.ANTHROPIC_API_KEY,
      model,
    })
  } catch (e) {
    console.error("[concierge] AI error:", e)
    return c.json({ error: String(e) }, 500)
  }

  const note = q.appendLog(
    db, userId, "assignment", assignmentId,
    "agent_note",
    JSON.stringify({ comment_id, text: responseText, source: "agent" }),
    Number(anchor_id),
  )

  return c.json(note, 201)
})
