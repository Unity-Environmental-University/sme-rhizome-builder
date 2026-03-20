/**
 * JWT middleware for Hono.
 * Same cookie name and secret as Flask (JWT_SECRET_KEY).
 * Identity is user.id (number), same as Flask's get_jwt_identity().
 */

import { createMiddleware } from "hono/factory"
import { getCookie } from "hono/cookie"
import { jwtVerify, SignJWT } from "jose"

const JWT_SECRET = process.env.JWT_SECRET_KEY ?? "dev-secret-change-in-production"
const SECRET_KEY = new TextEncoder().encode(JWT_SECRET)
const COOKIE_NAME = "access_token_cookie"

export type AuthEnv = {
  Variables: { userId: number }
}

export const jwtRequired = createMiddleware<AuthEnv>(async (c, next) => {
  const token = getCookie(c, COOKIE_NAME)
  if (!token) return c.json({ error: "Missing token" }, 401)
  try {
    const { payload } = await jwtVerify(token, SECRET_KEY)
    const sub = payload.sub
    if (!sub) return c.json({ error: "Invalid token" }, 401)
    c.set("userId", Number(sub))
    await next()
  } catch {
    return c.json({ error: "Invalid or expired token" }, 401)
  }
})

export async function signToken(userId: number): Promise<string> {
  return new SignJWT({ sub: String(userId) })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("7d")
    .sign(SECRET_KEY)
}
