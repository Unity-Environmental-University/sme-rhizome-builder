/**
 * Property-based tests for bearingEval pure functions.
 * parseEval, parseBatchEval, rollupLikelihood.
 */

import { describe, it, expect } from "vitest"
import fc from "fast-check"
import { parseEval, parseBatchEval, rollupLikelihood } from "../ai/bearingEval.js"

describe("parseEval", () => {
  it("returns true only for exact 'confirmed'", () => {
    expect(parseEval("confirmed")).toBe(true)
    expect(parseEval("  Confirmed  ")).toBe(true)
    expect(parseEval("CONFIRMED")).toBe(true)
  })

  it("returns false only for exact 'disconfirmed'", () => {
    expect(parseEval("disconfirmed")).toBe(false)
    expect(parseEval("  Disconfirmed  ")).toBe(false)
  })

  it("returns null for 'not_addressed'", () => {
    expect(parseEval("not_addressed")).toBe(null)
    expect(parseEval("NOT_ADDRESSED")).toBe(null)
  })

  it("rejects partial matches that startsWith would accept", () => {
    // This was the bug: "confirming" would have matched with startsWith
    expect(parseEval("confirming")).toBe(null)
    expect(parseEval("confirmed_strongly")).toBe(null)
    expect(parseEval("disconfirmed_maybe")).toBe(null)
    expect(parseEval("confidence")).toBe(null)
  })

  it("returns null for arbitrary strings", () => {
    fc.assert(
      fc.property(
        fc.string().filter(s => {
          const t = s.trim().toLowerCase()
          return t !== "confirmed" && t !== "disconfirmed" && t !== "not_addressed"
        }),
        (s) => {
          expect(parseEval(s)).toBe(null)
        }
      )
    )
  })

  it("never throws", () => {
    fc.assert(
      fc.property(fc.string(), (s) => {
        parseEval(s)
      })
    )
  })
})

describe("parseBatchEval", () => {
  it("parses N lines into N results", () => {
    fc.assert(
      fc.property(
        fc.array(fc.constantFrom("confirmed", "disconfirmed", "not_addressed"), { minLength: 1, maxLength: 20 }),
        (lines) => {
          const raw = lines.join("\n")
          const results = parseBatchEval(raw, lines.length)
          expect(results).toHaveLength(lines.length)
          for (let i = 0; i < lines.length; i++) {
            if (lines[i] === "confirmed") expect(results[i]).toBe(true)
            else if (lines[i] === "disconfirmed") expect(results[i]).toBe(false)
            else expect(results[i]).toBe(null)
          }
        }
      )
    )
  })

  it("pads with null when fewer lines than count", () => {
    fc.assert(
      fc.property(
        fc.nat({ max: 5 }),
        fc.integer({ min: 1, max: 10 }),
        (nLines, extra) => {
          const lines = Array.from({ length: nLines }, () => "confirmed")
          const count = nLines + extra
          const results = parseBatchEval(lines.join("\n"), count)
          expect(results).toHaveLength(count)
          // Extra entries should be null
          for (let i = nLines; i < count; i++) {
            expect(results[i]).toBe(null)
          }
        }
      )
    )
  })
})

describe("rollupLikelihood", () => {
  it("returns null when no statements are evaluated", () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ id: fc.nat(), text: fc.string(), observed: fc.constant(null as boolean | null) })),
        (statements) => {
          expect(rollupLikelihood(statements)).toBe(null)
        }
      )
    )
  })

  it("returns confirmed / total_evaluated for evaluated statements", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.nat(),
            text: fc.string(),
            observed: fc.oneof(fc.constant(true), fc.constant(false)),
          }),
          { minLength: 1 },
        ),
        (statements) => {
          const result = rollupLikelihood(statements)!
          const confirmed = statements.filter(s => s.observed === true).length
          expect(result).toBeCloseTo(confirmed / statements.length)
        }
      )
    )
  })

  it("result is always between 0 and 1 when not null", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.nat(),
            text: fc.string(),
            observed: fc.oneof(fc.constant(true), fc.constant(false), fc.constant(null as boolean | null)),
          }),
          { minLength: 1 },
        ),
        (statements) => {
          const result = rollupLikelihood(statements)
          if (result !== null) {
            expect(result).toBeGreaterThanOrEqual(0)
            expect(result).toBeLessThanOrEqual(1)
          }
        }
      )
    )
  })

  it("ignores null observations in the ratio", () => {
    fc.assert(
      fc.property(
        fc.array(
          fc.record({
            id: fc.nat(),
            text: fc.string(),
            observed: fc.oneof(fc.constant(true), fc.constant(false)),
          }),
          { minLength: 1 },
        ),
        fc.array(
          fc.record({
            id: fc.nat(),
            text: fc.string(),
            observed: fc.constant(null as boolean | null),
          }),
        ),
        (evaluated, unevaluated) => {
          const withNulls = [...evaluated, ...unevaluated]
          const withoutNulls = evaluated
          expect(rollupLikelihood(withNulls)).toBeCloseTo(rollupLikelihood(withoutNulls)!)
        }
      )
    )
  })
})
