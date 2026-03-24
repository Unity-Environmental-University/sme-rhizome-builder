/**
 * Property-based tests for prompt assembly.
 */

import { describe, it, expect } from "vitest"
import fc from "fast-check"
import { buildSystemPrompt, CARDS, CONCIERGE_DECK } from "../ai/prompts.js"

describe("buildSystemPrompt", () => {
  it("without course context, includes only deck cards", () => {
    const prompt = buildSystemPrompt(undefined, CONCIERGE_DECK)
    for (const key of CONCIERGE_DECK) {
      expect(prompt).toContain(CARDS[key])
    }
    expect(prompt).not.toContain("COURSE CONTEXT")
    expect(prompt).not.toContain("bearings")
  })

  it("with course, includes course section", () => {
    fc.assert(
      fc.property(
        fc.record({
          course_code: fc.string({ minLength: 1 }),
          course_title: fc.string({ minLength: 1 }),
        }),
        (course) => {
          const prompt = buildSystemPrompt(course, CONCIERGE_DECK)
          expect(prompt).toContain("COURSE CONTEXT")
          expect(prompt).toContain(course.course_code!.trim())
        }
      )
    )
  })

  it("includes bearings section when bearings present", () => {
    const course = {
      course_code: "TEST 101",
      bearings: [
        { text: "deep ecology", weight: 0.8, likelihood: 0.5 },
      ],
    }
    const prompt = buildSystemPrompt(course, CONCIERGE_DECK)
    expect(prompt).toContain("deep ecology")
    expect(prompt).toContain("sailing toward")
  })

  it("negative weight shows 'away from'", () => {
    const course = {
      course_code: "TEST",
      bearings: [
        { text: "rote memorization", weight: -0.7, likelihood: 0.3 },
      ],
    }
    const prompt = buildSystemPrompt(course, CONCIERGE_DECK)
    expect(prompt).toContain("away from")
  })

  it("shows observed statements", () => {
    const course = {
      course_code: "TEST",
      bearings: [{
        text: "test bearing",
        weight: 0.5,
        likelihood: 0.5,
        statements: [
          { text: "seen it", observed: 1 as const },
          { text: "not seen", observed: 0 as const },
          { text: "dunno", observed: null },
        ],
      }],
    }
    const prompt = buildSystemPrompt(course, CONCIERGE_DECK)
    expect(prompt).toContain("✓ observed: seen it")
    expect(prompt).toContain("✗ not observed: not seen")
    expect(prompt).not.toContain("dunno")
  })

  it("learning_outcome_rows render as numbered list", () => {
    fc.assert(
      fc.property(
        fc.array(fc.record({ text: fc.string({ minLength: 1 }) }), { minLength: 1, maxLength: 10 }),
        (rows) => {
          const course = { course_code: "X", learning_outcome_rows: rows }
          const prompt = buildSystemPrompt(course, CONCIERGE_DECK)
          for (let i = 0; i < rows.length; i++) {
            expect(prompt).toContain(`${i + 1}. ${rows[i].text}`)
          }
        }
      )
    )
  })

  it("never throws regardless of course shape", () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.constant(undefined),
          fc.record({
            course_code: fc.option(fc.string(), { nil: undefined }),
            course_title: fc.option(fc.string(), { nil: undefined }),
            learning_outcomes: fc.option(fc.string(), { nil: undefined }),
          }),
        ),
        (course) => {
          buildSystemPrompt(course)
        }
      )
    )
  })
})
