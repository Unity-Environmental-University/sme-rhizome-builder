/**
 * SQLite connection — better-sqlite3, synchronous, request-scoped via closure.
 * Same DB file as the Flask backend. Schema lives in backend/schema.sql.
 */

import Database from "better-sqlite3"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const DB_PATH = join(__dirname, "../../../backend/rhizome.db")

let _db: Database.Database | null = null

export function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH)
    _db.pragma("journal_mode = WAL")
    _db.pragma("foreign_keys = ON")
  }
  return _db
}
