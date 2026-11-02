// Postgres local (PGlite, dữ liệu nằm trong RAM) + stub các phần Supabase quản lý.
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
  create schema extensions; create schema auth; create schema storage;
  grant usage on schema auth, storage, extensions to anon, authenticated, service_role;
  create table auth.users (id uuid primary key default gen_random_uuid(), phone text unique, raw_user_meta_data jsonb default '{}');
  create table auth.sessions (id uuid primary key default gen_random_uuid(), user_id uuid not null references auth.users (id) on delete cascade);
  create function auth.uid() returns uuid language sql stable as
    $$ select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid $$;
  grant execute on function auth.uid() to anon, authenticated;
  create table storage.buckets (id text primary key, name text, public boolean, file_size_limit bigint, allowed_mime_types text[]);
  create table storage.objects (id uuid primary key default gen_random_uuid(), bucket_id text, name text);
  alter table storage.objects enable row level security;
  create function storage.foldername(name text) returns text[] language sql immutable as
    $$ select (string_to_array(name, '/'))[1:array_length(string_to_array(name, '/'),1)-1] $$;
  create publication supabase_realtime;
`)
const server = new PGLiteSocketServer({ db, port: Number(process.argv[2] || 54329), host: '127.0.0.1', maxConnections: 20 })
await server.start()
console.log('ready')
