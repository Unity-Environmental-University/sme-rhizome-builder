/**
 * Bearing evaluation — the otter step.
 *
 * For each bearing's statements, ask the AI in one batched call:
 * does the current draft content confirm, disconfirm, or not address each statement?
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

const EVAL_SYSTEM = `You evaluate whether a piece of writing addresses pedagogical statements.
The writing is a draft assignment description. Each statement describes something the course is meant to move toward.

You will receive numbered statements. For each, respond with exactly one word on its own line:
- confirmed   — the draft clearly addresses or supports this statement
- disconfirmed — the draft clearly contradicts or moves away from this statement
- not_addressed — the draft does not meaningfully touch this statement

One word per line, in order. No explanation.`

function parseEval(raw: string): boolean | null {
  const s = raw.trim().toLowerCase()
  if (s.startsWith("confirmed")) return true
  if (s.startsWith("disconfirmed")) return false
  return null
}

function parseBatchEval(raw: string, count: number): (boolean | null)[] {
  const lines = raw.trim().split(/\n/).map(l => l.trim()).filter(Boolean)
  const results: (boolean | null)[] = []
  for (let i = 0; i < count; i++) {
    results.push(lines[i] ? parseEval(lines[i]) : null)
  }
  return results
}

function rollupLikelihood(statements: Statement[]): number | null {
  const evaluated = statements.filter(s => s.observed !== null)
  if (!evaluated.length) return null
  const confirmed = evaluated.filter(s => s.observed === true).length
  return confirmed / evaluated.length
}

export type BearingPulse = {
  bearings: { text: string; likelihood: number; statements: { text: string; observed: boolean | null }[] }[]
}

export async function runBearingEval(opts: {
  sql: Sql
  bearings: Bearing[]
  draftHtml: string
  endpoint: "local" | "anthropic" | "openai" | "ollama"
  apiKey?: string
  model?: string
}): Promise<BearingPulse> {
  const { sql, bearings, draftHtml, endpoint, apiKey, model } = opts
  const pulse: BearingPulse = { bearings: [] }

  for (const bearing of bearings) {
    if (!bearing.statements.length) continue

    const stmtBlock = bearing.statements
      .map((s, i) => `${i + 1}. ${s.text}`)
      .join("\n")

    let results: (boolean | null)[]
    try {
      const raw = await callAi({
        endpoint,
        systemPrompt: EVAL_SYSTEM,
        messages: [{
          role: "user",
          content: `Statements:\n${stmtBlock}\n\nDraft content:\n${draftHtml}`,
        }],
        apiKey,
        model,
      })
      results = parseBatchEval(raw, bearing.statements.length)
    } catch (e) {
      console.error(`[bearingEval] batch eval for bearing ${bearing.id} failed:`, e)
      results = bearing.statements.map(() => null)
    }

    const updatedStatements: Statement[] = []
    for (let i = 0; i < bearing.statements.length; i++) {
      const stmt = bearing.statements[i]
      const observed = results[i] ?? null
      try {
        await q.updateStatement(sql, stmt.id, { observed })
      } catch (e) {
        console.error(`[bearingEval] statement ${stmt.id} update failed:`, e)
      }
      updatedStatements.push({ ...stmt, observed })
    }

    const newLikelihood = rollupLikelihood(updatedStatements)
    if (newLikelihood !== null) {
      try {
        await q.updateBearing(sql, bearing.id, { likelihood: newLikelihood })
      } catch (e) {
        console.error(`[bearingEval] likelihood update for bearing ${bearing.id} failed:`, e)
      }
    }

    pulse.bearings.push({
      text: bearing.text,
      likelihood: newLikelihood ?? bearing.likelihood,
      statements: updatedStatements.map(s => ({ text: s.text, observed: s.observed })),
    })
  }

  return pulse
}
