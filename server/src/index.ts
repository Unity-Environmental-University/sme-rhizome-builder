/**
 * SME Rhizome Builder — Hono backend
 * Parallel to Flask on 5050. Runs on 5051.
 * PostgreSQL via postgres.js (transform: camel).
 * alkahest-ts is a direct import — no subprocess bridge.
 */

import { serve } from "@hono/node-server"
import { Hono } from "hono"
import { cors } from "hono/cors"
import { logger } from "hono/logger"


import { authRoutes } from "./routes/auth.js"
import { courseRoutes } from "./routes/courses.js"
import { assignmentRoutes } from "./routes/assignments.js"
import { logRoutes } from "./routes/log.js"
import { conciergeRoutes } from "./routes/concierge.js"
import { moduleRoutes } from "./routes/modules.js"
import { bearingRoutes } from "./routes/bearings.js"

const PORT = Number(process.env.HONO_PORT ?? 5051)

const app = new Hono()

app.use("*", logger())

app.use("*", cors({
  origin: ["http://localhost:5173", "http://localhost:5174"],
  credentials: true,
}))

app.route("/api/auth", authRoutes)
app.route("/api/courses", courseRoutes)
app.route("/api/assignments", assignmentRoutes)
app.route("/api/log", logRoutes)
app.route("/api/concierge", conciergeRoutes)
app.route("/api/modules", moduleRoutes)
app.route("/api/bearings", bearingRoutes)

app.get("/", (c) => c.json({ service: "sme-rhizome-server", port: PORT, backend: "hono" }))

serve({ fetch: app.fetch, port: PORT }, () => {
  console.log(`sme-rhizome-server (hono) → http://localhost:${PORT}`)
})
