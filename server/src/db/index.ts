/**
 * PostgreSQL connection via postgres.js.
 * Configure via environment variables — see .env.example.
 *
 * If DATABASE_URL is not set, the server will refuse to start with a clear message.
 */

import postgres from "postgres"

const DATABASE_URL = process.env.DATABASE_URL

if (!DATABASE_URL) {
  console.error(`
╔══════════════════════════════════════════════════════════╗
║           DATABASE NOT CONFIGURED                        ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Set DATABASE_URL in your environment or .env file:      ║
║                                                          ║
║  DATABASE_URL=postgres://localhost/rhizome-builder       ║
║                                                          ║
║  PostgreSQL 17 is expected (brew services postgresql@17) ║
║  Run the schema:  psql rhizome-builder < schema.sql      ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
`)
  process.exit(1)
}

let _sql: ReturnType<typeof postgres> | null = null

export function getSql(): ReturnType<typeof postgres> {
  if (!_sql) {
    _sql = postgres(DATABASE_URL!, { transform: postgres.camel })
  }
  return _sql
}
