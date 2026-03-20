/**
 * Bearing evaluation — the otter step.
 *
 * For each BearingStatement on a course's bearings, ask the AI:
 * does the current draft content confirm, disconfirm, or not address this statement?
 *
 * Writes observed: true/false/null to bearing_statements.
 * Rolls up likelihood on each bearing: confirmed / (confirmed + disconfirmed).
 * If no statements have been evaluated, likelihood stays as the designer set it.
 *
 * Called fire-and-forget from the concierge route after agent_note is written.
 * Does not block the response. Errors are logged, not thrown.
 */

import type postgres from "postgres"
import { callAi } from "./index.js"
import * as q from "../db/queries.js"

type Sql = postgres.Sql

type Statement = { id: number; text: string; observed: boolean | null }
type Bearing = { id: number; text: string; weight: number; likelihood: number; statements: Statement[] }

const EVAL_SYSTEM = `You evaluate whether a piece of writing addresses a pedagogical statement.
The writing is a draft assignment description. The statement describes something the course is meant to move toward.

Respond with exactly one word:
- confirmed   — the draft clearly addresses or supports this statement
- disconfirmed — the draft clearly contradicts or moves away from this statement
- not_addressed — the draft does not meaningfully touch this statement

No explanation. One word only.`

function parseEval(raw: string): boolean | null {
  const s = raw.trim().toLowerCase()
  if (s.startsWith("confirmed")) return true
  if (s.startsWith("disconfirmed")) return false
  return null
}

function rollupLikelihood(statements: Statement[]): number | null {
  const evaluated = statements.filter(s => s.observed !== null)
  if (!evaluated.length) return null
  const confirmed = evaluated.filter(s => s.observed === true).length
  return confirmed / evaluated.length
}

export async function runBearingEval(opts: {
  sql: Sql
  bearings: Bearing[]
  draftHtml: string
  endpoint: "local" | "anthropic" | "openai" | "ollama"
  apiKey?: string
  model?: string
}): Promise<void> {
  const { sql, bearings, draftHtml, endpoint, apiKey, model } = opts

  for (const bearing of bearings) {
    if (!bearing.statements.length) continue

    const updatedStatements: Statement[] = []

    for (const stmt of bearing.statements) {
      try {
        const raw = await callAi({
          endpoint,
          systemPrompt: EVAL_SYSTEM,
          messages: [{
            role: "user",
            content: `Statement: ${stmt.text}\n\nDraft content:\n${draftHtml}`,
          }],
          apiKey,
          model,
        })
        const observed = parseEval(raw)
        await q.updateStatement(sql, stmt.id, { observed })
        updatedStatements.push({ ...stmt, observed })
      } catch (e) {
        console.error(`[bearingEval] statement ${stmt.id} failed:`, e)
        updatedStatements.push(stmt)
      }
    }

    const newLikelihood = rollupLikelihood(updatedStatements)
    if (newLikelihood !== null) {
      try {
        await q.updateBearing(sql, bearing.id, { likelihood: newLikelihood })
      } catch (e) {
        console.error(`[bearingEval] likelihood update for bearing ${bearing.id} failed:`, e)
      }
    }
  }
}
