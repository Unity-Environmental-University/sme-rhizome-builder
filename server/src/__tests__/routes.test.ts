/**
 * Property-based route tests.
 *
 * These test the Hono app's HTTP behavior without a database.
 * The DB module is mocked — we test the route layer's contract:
 * - unauthenticated → 401
 * - bad params → 400
 * - valid auth + valid params → delegates to queries (200/201)
 * - missing resources → 404
 */

import { describe, it, expect, vi, beforeEach } from "vitest"
import fc from "fast-check"
import { Hono } from "hono"
import { signToken, type AuthEnv } from "../auth.js"

// ── Mock the DB before importing routes ────────────────────────────────

vi.mock("../db/index.js", () => ({
  getSql: () => ({}),
}))

vi.mock("../db/queries.js", () => ({
  listCourses: vi.fn(),
  getCourse: vi.fn(),
  createCourse: vi.fn(),
  updateCourse: vi.fn(),
  listAssignments: vi.fn(),
  getAssignment: vi.fn(),
  createAssignment: vi.fn(),
  updateAssignment: vi.fn(),
  nextPositionInModule: vi.fn(),
  listSnapshots: vi.fn(),
  createSnapshot: vi.fn(),
  listBearings: vi.fn(),
  getBearing: vi.fn(),
  createBearing: vi.fn(),
  updateBearing: vi.fn(),
  deleteBearing: vi.fn(),
  listStatements: vi.fn(),
  createStatement: vi.fn(),
  updateStatement: vi.fn(),
  listModules: vi.fn(),
  createModule: vi.fn(),
  updateModule: vi.fn(),
  listLearningOutcomes: vi.fn(),
  listLog: vi.fn(),
  appendLog: vi.fn(),
  getLogEntry: vi.fn(),
  latestSnapshot: vi.fn(),
  getUser: vi.fn(),
}))

vi.mock("../ai/index.js", () => ({ callAi: vi.fn() }))
vi.mock("../ai/prompts.js", () => ({ buildSystemPrompt: vi.fn(() => ""), CONCIERGE_DECK: [] }))
vi.mock("../ai/bearingEval.js", () => ({ runBearingEval: vi.fn() }))

// ── Import routes and mocked queries after mocking ─────────────────────

import * as q from "../db/queries.js"
const { assignmentRoutes } = await import("../routes/assignments.js")
const { courseRoutes } = await import("../routes/courses.js")
const { bearingRoutes } = await import("../routes/bearings.js")
const { moduleRoutes } = await import("../routes/modules.js")
const { logRoutes } = await import("../routes/log.js")

// ── Test app ───────────────────────────────────────────────────────────

function buildApp() {
  const app = new Hono()
  app.route("/api/courses", courseRoutes)
  app.route("/api/assignments", assignmentRoutes)
  app.route("/api/bearings", bearingRoutes)
  app.route("/api/modules", moduleRoutes)
  app.route("/api/log", logRoutes)
  return app
}

async function authedRequest(app: Hono, method: string, path: string, body?: unknown) {
  const token = await signToken(1)
  const headers: Record<string, string> = {
    Cookie: `access_token_cookie=${token}`,
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json"
  }
  return app.request(path, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

function resetAllMocks() {
  Object.values(q).forEach((fn) => {
    if (typeof fn === "function" && "mockReset" in fn) {
      (fn as ReturnType<typeof vi.fn>).mockReset()
    }
  })
}

// ── Properties ─────────────────────────────────────────────────────────

describe("authentication property", () => {
  const protectedPaths = [
    ["GET", "/api/courses"],
    ["GET", "/api/assignments?course_id=1"],
    ["GET", "/api/bearings?course_id=1"],
    ["GET", "/api/modules?course_id=1"],
  ] as const

  it("unauthenticated requests always return 401", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom(...protectedPaths),
        async ([method, path]) => {
          const res = await app.request(path, { method })
          expect(res.status).toBe(401)
        }
      )
    )
  })
})

describe("param validation property", () => {
  beforeEach(resetAllMocks)

  it("non-numeric course_id in query always returns 400", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.string().filter((s) => {
          const n = Number(s)
          return isNaN(n) || !Number.isFinite(n) || n <= 0
        }),
        async (badId) => {
          const res = await authedRequest(app, "GET", `/api/assignments?course_id=${encodeURIComponent(badId)}`)
          expect(res.status).toBe(400)
        }
      )
    )
  })

  it("non-numeric path param returns 400, never 500", async () => {
    const app = buildApp()
    // Generate strings that look like plausible IDs but aren't valid positive numbers
    await fc.assert(
      fc.asyncProperty(
        fc.oneof(
          fc.stringMatching(/^[a-zA-Z][a-zA-Z0-9]*$/),  // alpha IDs
          fc.stringMatching(/^-\d+$/),                    // negative numbers
          fc.constant("0"),
          fc.constant("NaN"),
          fc.constant("Infinity"),
        ),
        async (badId) => {
          const res = await authedRequest(app, "GET", `/api/courses/${badId}`)
          // Should be 400 (bad param), never 500 (unhandled)
          expect([400, 404]).toContain(res.status)
        }
      )
    )
  })
})

describe("valid auth + resource lifecycle", () => {
  beforeEach(resetAllMocks)

  it("GET /api/courses returns whatever the DB returns", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.record({
          id: fc.nat(),
          courseCode: fc.string(),
          courseTitle: fc.string(),
        })),
        async (fakeCourses) => {
          vi.mocked(q.listCourses).mockResolvedValue(fakeCourses)
          const res = await authedRequest(app, "GET", "/api/courses")
          expect(res.status).toBe(200)
          const data = await res.json() as { courses: unknown[] }
          expect(data.courses).toEqual(fakeCourses)
        }
      )
    )
  })

  it("missing resource always returns 404, never 500", async () => {
    const app = buildApp()
    vi.mocked(q.getCourse).mockResolvedValue(null)
    const res = await authedRequest(app, "GET", "/api/courses/999")
    expect(res.status).toBe(404)
  })

  it("GET /api/assignments with valid course_id returns assignments", async () => {
    const app = buildApp()
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.record({
          id: fc.string(),
          title: fc.string(),
          moduleLabel: fc.string(),
          position: fc.nat(),
        })),
        async (fakeAssignments) => {
          vi.mocked(q.listAssignments).mockResolvedValue(fakeAssignments)
          const res = await authedRequest(app, "GET", "/api/assignments?course_id=1")
          expect(res.status).toBe(200)
          const data = await res.json() as { assignments: unknown[] }
          expect(data.assignments).toEqual(fakeAssignments)
        }
      )
    )
  })
})
