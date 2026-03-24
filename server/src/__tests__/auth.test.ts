/**
 * Property-based tests for JWT auth.
 */

import { describe, it, expect } from "vitest"
import fc from "fast-check"
import { Hono } from "hono"
import { signToken, jwtRequired, type AuthEnv } from "../auth.js"

function buildApp() {
  const app = new Hono<AuthEnv>()
  app.use("/protected/*", jwtRequired)
  app.get("/protected/me", (c) => c.json({ userId: c.get("userId") }))
  return app
}

describe("signToken + jwtRequired round-trip", () => {
  it("valid token round-trips any positive user id", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 1_000_000 }),
        async (userId) => {
          const token = await signToken(userId)
          const res = await app.request("/protected/me", {
            headers: { Cookie: `access_token_cookie=${token}` },
          })
          expect(res.status).toBe(200)
          const body = await res.json() as { userId: number }
          expect(body.userId).toBe(userId)
        }
      )
    )
  })

  it("missing cookie always returns 401", async () => {
    const app = buildApp()
    const res = await app.request("/protected/me")
    expect(res.status).toBe(401)
  })

  it("garbage token always returns 401", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.string({ minLength: 1 }),
        async (garbage) => {
          const res = await app.request("/protected/me", {
            headers: { Cookie: `access_token_cookie=${garbage}` },
          })
          expect(res.status).toBe(401)
        }
      )
    )
  })

  it("signToken always produces a non-empty string", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.integer({ min: 1, max: 1_000_000 }),
        async (userId) => {
          const token = await signToken(userId)
          expect(typeof token).toBe("string")
          expect(token.length).toBeGreaterThan(0)
        }
      )
    )
  })
})
