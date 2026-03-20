import { Hono } from "hono"
import { setCookie, deleteCookie } from "hono/cookie"
import { getDb } from "../db/index.js"
import { getUserByCanvasId, createDemoUser, getUser } from "../db/queries.js"
import { signToken, jwtRequired, type AuthEnv } from "../auth.js"

const CANVAS_CLIENT_ID = process.env.CANVAS_CLIENT_ID
const CANVAS_CLIENT_SECRET = process.env.CANVAS_CLIENT_SECRET
const CANVAS_BASE_URL = process.env.CANVAS_BASE_URL ?? "https://unity.instructure.com"

export const authRoutes = new Hono<AuthEnv>()

authRoutes.post("/demo", async (c) => {
  if (CANVAS_CLIENT_ID) return c.json({ error: "Demo mode disabled" }, 403)
  const db = getDb()
  const user = createDemoUser(db)
  const token = await signToken(user.id as number)
  setCookie(c, "access_token_cookie", token, { httpOnly: true, path: "/", sameSite: "Lax", maxAge: 60 * 60 * 24 * 7 })
  return c.json({ id: user.id, name: user.name, email: user.email })
})

authRoutes.get("/login", (c) => {
  if (!CANVAS_CLIENT_ID) return c.json({ error: "Canvas OAuth not configured" }, 503)
  const redirect = `${CANVAS_BASE_URL}/login/oauth2/auth?client_id=${CANVAS_CLIENT_ID}&response_type=code&redirect_uri=${encodeURIComponent(process.env.CANVAS_REDIRECT_URI ?? "http://localhost:5051/api/auth/callback")}`
  return c.redirect(redirect)
})

authRoutes.get("/callback", async (c) => {
  if (!CANVAS_CLIENT_ID || !CANVAS_CLIENT_SECRET) return c.json({ error: "Canvas OAuth not configured" }, 503)
  const code = c.req.query("code")
  if (!code) return c.json({ error: "Missing code" }, 400)

  const tokenRes = await fetch(`${CANVAS_BASE_URL}/login/oauth2/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: CANVAS_CLIENT_ID,
      client_secret: CANVAS_CLIENT_SECRET,
      code,
      redirect_uri: process.env.CANVAS_REDIRECT_URI ?? "http://localhost:5051/api/auth/callback",
    }),
  })
  if (!tokenRes.ok) return c.json({ error: "Token exchange failed" }, 502)
  const tokenData = await tokenRes.json() as { access_token: string; refresh_token?: string; user?: { id: number; name: string } }

  // Fetch user profile
  const profileRes = await fetch(`${CANVAS_BASE_URL}/api/v1/users/self/profile`, {
    headers: { Authorization: `Bearer ${tokenData.access_token}` },
  })
  const profile = await profileRes.json() as { id: number; name: string; primary_email?: string }

  const db = getDb()
  const { upsertUser } = await import("../db/queries.js")
  const user = upsertUser(db, String(profile.id), profile.name, profile.primary_email ?? "", tokenData.access_token, tokenData.refresh_token)
  const token = await signToken(user.id as number)
  setCookie(c, "access_token_cookie", token, { httpOnly: true, path: "/", sameSite: "Lax", maxAge: 60 * 60 * 24 * 7 })
  return c.redirect("/")
})

authRoutes.get("/me", jwtRequired, (c) => {
  const db = getDb()
  const user = getUser(db, c.get("userId"))
  if (!user) return c.json({ error: "Not found" }, 404)
  return c.json({ id: user.id, name: user.name, email: user.email })
})

authRoutes.post("/logout", (c) => {
  deleteCookie(c, "access_token_cookie", { path: "/" })
  return c.json({ ok: true })
})
