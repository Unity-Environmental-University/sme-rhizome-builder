import { Hono } from "hono"
import { getSql } from "../db/index.js"
import * as q from "../db/queries.js"
import { jwtRequired, type AuthEnv } from "../auth.js"
import { callAi } from "../ai/index.js"
import { buildSystemPrompt, CONCIERGE_DECK } from "../ai/prompts.js"
import { runBearingEval } from "../ai/bearingEval.js"

export const conciergeRoutes = new Hono<AuthEnv>()
conciergeRoutes.use("*", jwtRequired)

conciergeRoutes.post("/:assignmentId", async (c) => {
  const sql = getSql()
  const userId = c.get("userId")
  const assignmentId = c.req.param("assignmentId")

  const assignment = await q.getAssignment(sql, assignmentId, userId)
  if (!assignment) return c.json({ error: "Not found" }, 404)

  const body = await c.req.json()
  const { anchor_id, comment_id, endpoint, api_key, model } = body
  if (!anchor_id || !comment_id) return c.json({ error: "anchor_id and comment_id required" }, 400)

  const anchor = await q.getLogEntry(sql, Number(anchor_id))
  if (!anchor) return c.json({ error: "Anchor not found" }, 404)

  let anchorContent: Record<string, unknown> = {}
  try { anchorContent = JSON.parse(anchor.content as string) } catch {}

  const snapshot = await q.latestSnapshot(sql, assignmentId)
  let draftHtml = ""
  if (snapshot) {
    const content = snapshot.content as Record<string, unknown>
    draftHtml = (content.description as string) ?? ""
  }

  const course = await q.getCourse(sql, assignment.courseId as number, userId)
  let courseData: Record<string, unknown> | undefined
  if (course) {
    const [outcomes, bearings] = await Promise.all([
      q.listLearningOutcomes(sql, course.id as number),
      q.listBearings(sql, course.id as number),
    ])
    const statements = (await Promise.all(bearings.map((b: Record<string, unknown>) => q.listStatements(sql, b.id as number)))).flat()
    courseData = {
      ...course,
      learning_outcome_rows: outcomes,
      bearings: bearings.map((b: Record<string, unknown>) => ({
        ...b,
        statements: statements.filter((s: Record<string, unknown>) => s.bearingId === b.id),
      })),
    }
  }

  const hasSelection = anchorContent.from != null && anchorContent.to != null
  const selectionText = anchorContent.text as string ?? ""
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

  const note = await q.appendLog(
    sql, userId, "assignment", assignmentId,
    "agent_note",
    JSON.stringify({ comment_id, text: responseText, source: "agent" }),
    Number(anchor_id),
  )

  // Fire bearing eval without blocking — writes observed + rolls up likelihood
  if (courseData?.bearings && draftHtml) {
    type BearingWithStatements = { id: number; text: string; weight: number; likelihood: number; statements: { id: number; text: string; observed: boolean | null }[] }
    const bearings = (courseData.bearings as BearingWithStatements[]).filter(b => b.statements.length > 0)
    if (bearings.length) {
      runBearingEval({
        sql,
        bearings,
        draftHtml,
        endpoint: resolvedEndpoint,
        apiKey: api_key ?? process.env.ANTHROPIC_API_KEY,
        model,
      }).catch(e => console.error("[concierge] bearingEval failed:", e))
    }
  }

  return c.json(note, 201)
})
