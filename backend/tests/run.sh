#!/bin/sh
# Dựng Postgres local mới tinh, migrate + seed, chạy toàn bộ test, rồi tắt. KHÔNG đụng tới Supabase.
set -e
cd "$(dirname "$0")/.."
PORT="${TEST_PG_PORT:-54329}"
[ -d tests/local_pg/node_modules ] || (cd tests/local_pg && npm install --silent)
node tests/local_pg/server.mjs "$PORT" > /dev/null 2>&1 &
PG_PID=$!
trap 'kill $PG_PID 2>/dev/null' EXIT
URL="postgresql://postgres@127.0.0.1:$PORT/postgres?sslmode=disable"
for _ in $(seq 1 60); do nc -z 127.0.0.1 "$PORT" 2>/dev/null && break; sleep 0.5; done
export DATABASE_URL="$URL" DB_PASSWORD=
uv run python manage.py migrate 2>&1 | grep -v "^INFO" || true
uv run python manage.py seed
TEST_DATABASE_URL="$URL" uv run pytest -q "$@"
