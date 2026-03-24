/**
 * Property-based tests for query helpers (buildSetClause).
 * No DB needed — tests the clause builder in isolation.
 */

import { describe, it, expect } from "vitest"
import fc from "fast-check"
import { buildSetClause } from "../db/queries.js"

describe("buildSetClause", () => {
  it("returns null for empty fields and no extras", () => {
    expect(buildSetClause({})).toBe(null)
    expect(buildSetClause({ a: undefined, b: undefined })).toBe(null)
  })

  it("includes only defined fields", () => {
    fc.assert(
      fc.property(
        fc.dictionary(fc.stringMatching(/^[a-z_]+$/), fc.oneof(fc.string(), fc.integer(), fc.boolean()), { minKeys: 1, maxKeys: 5 }),
        (fields) => {
          const result = buildSetClause(fields)!
          expect(result).not.toBe(null)
          const definedCount = Object.values(fields).filter(v => v !== undefined).length
          // Each defined field gets a "col = $N" entry
          expect(result.vals).toHaveLength(definedCount)
          // Clause has the right number of assignments
          const assignments = result.clause.split(",").map(s => s.trim())
          expect(assignments).toHaveLength(definedCount)
        }
      )
    )
  })

  it("parameter indices are sequential starting at 1", () => {
    fc.assert(
      fc.property(
        fc.dictionary(fc.stringMatching(/^[a-z_]+$/), fc.string(), { minKeys: 1, maxKeys: 5 }),
        (fields) => {
          const result = buildSetClause(fields)!
          for (let i = 0; i < result.vals.length; i++) {
            expect(result.clause).toContain(`$${i + 1}`)
          }
        }
      )
    )
  })

  it("extraSets are appended but don't add vals", () => {
    const result = buildSetClause({}, ["updated_at = now()"])!
    expect(result.clause).toBe("updated_at = now()")
    expect(result.vals).toHaveLength(0)
  })

  it("combines fields and extraSets", () => {
    const result = buildSetClause({ title: "hello" }, ["updated_at = now()"])!
    expect(result.clause).toContain("title = $1")
    expect(result.clause).toContain("updated_at = now()")
    expect(result.vals).toEqual(["hello"])
  })

  it("vals array can be extended for WHERE params", () => {
    // This tests the pattern used by all update functions
    const result = buildSetClause({ title: "test" })!
    const whereIdx = result.vals.push(42) // moduleId
    const whereIdx2 = result.vals.push(7)  // courseId
    const query = `UPDATE t SET ${result.clause} WHERE id = $${whereIdx} AND course_id = $${whereIdx2}`
    expect(query).toContain("$2")
    expect(query).toContain("$3")
    expect(result.vals).toEqual(["test", 42, 7])
  })
})
