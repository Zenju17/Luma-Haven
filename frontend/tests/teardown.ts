import { execFileSync } from 'node:child_process'
import { rmSync } from 'node:fs'
import { resolve } from 'node:path'

export default function teardown() {
  try {
    const root = resolve(import.meta.dirname, '../..')
    const python = resolve(root, '.venv/bin/python')
    const admin = process.env.E2E_DATABASE_URL!
    const name = process.env.E2E_TEST_DATABASE_NAME!
    execFileSync(python, ['-c', `import psycopg
from psycopg import sql
with psycopg.connect(${JSON.stringify(admin)}, autocommit=True) as conn:
    conn.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(${JSON.stringify(name)})))`], { cwd: root, stdio: 'pipe' })
  } finally {
    rmSync(process.env.E2E_MAIL_DIR!, { recursive: true, force: true })
  }
}
