import { describe, it, expect } from "vitest"
import fc from "fast-check"
import { numParam } from "../helpers.js"

describe("numParam", () => {
  it("always returns a positive finite number or null", () => {
    fc.assert(
      fc.property(fc.oneof(fc.string(), fc.constant(undefined)), (input) => {
        const result = numParam(input)
        if (result !== null) {
          expect(result).toBeGreaterThan(0)
          expect(Number.isFinite(result)).toBe(true)
        }
      })
    )
  })

  it("round-trips positive finite numbers through string representation", () => {
    fc.assert(
      fc.property(
        fc.double({ min: 0.001, max: 1e15, noNaN: true }),
        (n) => {
          const result = numParam(String(n))
          // If the number is positive and finite, numParam should return it
          if (n > 0 && Number.isFinite(n)) {
            expect(result).toBe(n)
          }
        }
      )
    )
  })

  it("rejects everything that is not a positive finite number", () => {
    fc.assert(
      fc.property(
        fc.oneof(
          fc.constant(undefined),
          fc.constant(""),
          fc.constant("NaN"),
          fc.constant("Infinity"),
          fc.constant("-Infinity"),
          fc.constant("0"),
          // negative numbers as strings
          fc.double({ max: 0, noNaN: true }).map(String),
          // non-numeric strings
          fc.string().filter((s) => isNaN(Number(s)) || !Number.isFinite(Number(s)))
        ),
        (input) => {
          expect(numParam(input)).toBeNull()
        }
      )
    )
  })

  it("never throws", () => {
    fc.assert(
      fc.property(
        fc.oneof(fc.string(), fc.constant(undefined)),
        (input) => {
          // should not throw, regardless of input
          numParam(input)
        }
      )
    )
  })
})
