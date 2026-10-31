#!/bin/sh
# Restore drill: proves the latest backup can actually be restored. Run monthly.
# Restores into a THROWAWAY database on a disposable PostgreSQL server (never production):
#   DRILL_DATABASE_URL=postgresql://user:pass@127.0.0.1:55432/postgres scripts/restore_drill.sh [dump-file]
set -eu
: "${DRILL_DATABASE_URL:?DRILL_DATABASE_URL (admin URL of a disposable server) is required}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"

case "$DRILL_DATABASE_URL" in
  *@127.0.0.1:*|*@localhost:*|*@localhost/*|*@127.0.0.1/*) ;;
  *) [ "${DRILL_ALLOW_REMOTE:-0}" = "1" ] || { echo "Refusing: drill server is not local (set DRILL_ALLOW_REMOTE=1 to override)" >&2; exit 2; } ;;
esac
if [ -n "${DATABASE_URL:-}" ] && [ "$DATABASE_URL" = "$DRILL_DATABASE_URL" ]; then
  echo "Refusing: drill URL equals production DATABASE_URL" >&2; exit 2
fi

dump="${1:-$(ls -1t "$BACKUP_DIR"/lumahaven-*.dump 2>/dev/null | head -n 1)}"
[ -n "$dump" ] && [ -f "$dump" ] || { echo "No backup file found" >&2; exit 3; }
(cd "$(dirname "$dump")" && sha256sum -c "$(basename "$dump").sha256" >/dev/null) || { echo "Checksum mismatch" >&2; exit 4; }

db="drill_$(date -u +%Y%m%d%H%M%S)"
base="${DRILL_DATABASE_URL%/*}"
status="$BACKUP_DIR/last_restore_drill.json"
fail() { printf '{"ok": false, "at": "%s", "file": "%s"}\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(basename "$dump")" > "$status"; psql "$DRILL_DATABASE_URL" -qc "DROP DATABASE IF EXISTS $db" 2>/dev/null || true; echo "restore drill FAILED: $1" >&2; exit 1; }

psql "$DRILL_DATABASE_URL" -qc "CREATE DATABASE $db" || fail "cannot create drill database"
pg_restore --no-owner --no-acl --exit-on-error --dbname="$base/$db" "$dump" || fail "pg_restore error"

tables=$(psql "$base/$db" -Atc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name LIKE 'core_%'")
hotels=$(psql "$base/$db" -Atc "SELECT count(*) FROM core_hotel")
folio=$(psql "$base/$db" -Atc "SELECT count(*) FROM core_folioentry")
[ "$tables" -ge 20 ] || fail "only $tables core tables restored"

psql "$DRILL_DATABASE_URL" -qc "DROP DATABASE $db"
printf '{"ok": true, "at": "%s", "file": "%s", "core_tables": %s, "hotels": %s, "folio_entries": %s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(basename "$dump")" "$tables" "$hotels" "$folio" > "$status"
echo "restore drill OK: $tables tables, $hotels hotel(s), $folio folio entries"
