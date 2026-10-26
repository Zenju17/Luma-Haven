import { execFileSync, spawn } from 'node:child_process'
import { resolve } from 'node:path'

const root = resolve(import.meta.dirname, '../..')
const python = process.env.E2E_PYTHON
const admin = process.env.E2E_DATABASE_URL
const name = process.env.E2E_TEST_DATABASE_NAME
const env = { ...process.env, DATABASE_URL: process.env.DATABASE_URL }

// This script is invoked by Playwright's backend webServer, before it waits
// for the health endpoint. Both the database and its seed remain isolated.
execFileSync(python, ['-c', `import psycopg
from psycopg import sql
with psycopg.connect(${JSON.stringify(admin)}, autocommit=True) as conn:
    conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(${JSON.stringify(name)})))`], { cwd: root, stdio: 'pipe' })
execFileSync(python, ['backend/manage.py', 'migrate', '--noinput'], { cwd: root, env, stdio: 'pipe' })
execFileSync(python, ['backend/manage.py', 'seed_demo'], {
  cwd: root, env: { ...env, SEED_PASSWORD: process.env.E2E_STAFF_PASSWORD }, stdio: 'pipe',
})

const backend = spawn(python, ['backend/manage.py', 'runserver', '127.0.0.1:8001', '--noreload'], {
  cwd: root, env, stdio: 'inherit',
})
process.on('SIGINT', () => backend.kill('SIGINT'))
process.on('SIGTERM', () => backend.kill('SIGTERM'))
backend.on('exit', code => process.exit(code ?? 0))
