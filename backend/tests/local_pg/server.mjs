// Postgres local (PGlite, dữ liệu nằm trong RAM) + các role và schema extensions giống Supabase.
// Dùng: node server.mjs [port]   (mặc định 54329)
import { PGlite } from '@electric-sql/pglite'
import { pg_trgm } from '@electric-sql/pglite/contrib/pg_trgm'
import { unaccent } from '@electric-sql/pglite/contrib/unaccent'
import { PGLiteSocketServer } from '@electric-sql/pglite-socket'

const db = await PGlite.create({ extensions: { pg_trgm, unaccent } })
await db.exec(`
  create role anon nologin; create role authenticated nologin; create role service_role nologin bypassrls;
  grant usage on schema public to anon, authenticated, service_role;
  alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
  alter default privileges in schema public grant all on functions to anon, authenticated, service_role;
  create schema extensions;
  grant usage on schema extensions to anon, authenticated, service_role;
  create publication supabase_realtime;
`)
const server = new PGLiteSocketServer({ db, port: Number(process.argv[2] || 54329), host: '127.0.0.1', maxConnections: 20 })
await server.start()
console.log('ready')
