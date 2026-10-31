#!/bin/sh
# Daily logical backup of the application database (custom-format pg_dump, compressed).
# Writes /backups/lumahaven-<UTC stamp>.dump + .sha256 and an atomic status marker that the
# Developer Console reads (last_backup.json). Never prints DATABASE_URL.
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
mkdir -p "$BACKUP_DIR"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
name="lumahaven-$stamp.dump"
file="$BACKUP_DIR/$name"

write_status() { # ok size
  tmp="$BACKUP_DIR/.last_backup.json.tmp"
  printf '{"ok": %s, "started_at": "%s", "finished_at": "%s", "file": "%s", "size_bytes": %s}\n' \
    "$1" "$started" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$name" "$2" > "$tmp"
  mv "$tmp" "$BACKUP_DIR/last_backup.json"
}

if pg_dump --format=custom --compress=6 --no-owner --no-acl --dbname="$DATABASE_URL" --file="$file.partial" 2>/dev/null; then
  mv "$file.partial" "$file"
  size=$(wc -c < "$file" | tr -d ' ')
  (cd "$BACKUP_DIR" && sha256sum "$name" > "$name.sha256")
  find "$BACKUP_DIR" -name 'lumahaven-*' -type f -mtime +"$KEEP_DAYS" -delete
  write_status true "$size"
  echo "backup ok: $name ($size bytes)"
else
  rm -f "$file.partial"
  write_status false 0
  echo "backup FAILED" >&2
  exit 1
fi
