import { randomBytes } from 'node:crypto'
import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'

const frontend = dirname(fileURLToPath(import.meta.url))
const root = resolve(frontend, '..')
const adminUrl = process.env.E2E_DATABASE_URL
if (!adminUrl) throw new Error('Set E2E_DATABASE_URL to a disposable loopback PostgreSQL server before running browser tests.')
const database = new URL(adminUrl)
if (!['127.0.0.1', 'localhost'].includes(database.hostname) || database.port !== '55432' || database.pathname !== '/postgres') {
  throw new Error('Browser tests require an isolated local PostgreSQL server on port 55432 and the postgres admin database.')
}

process.env.E2E_TEST_DATABASE_NAME = `hims_e2e_${randomBytes(5).toString('hex')}`
database.pathname = `/${process.env.E2E_TEST_DATABASE_NAME}`
process.env.E2E_TEST_DATABASE_URL = database.toString()
process.env.E2E_STAFF_PASSWORD = randomBytes(24).toString('hex')
process.env.E2E_MAIL_DIR = mkdtempSync(join(tmpdir(), 'luma-haven-e2e-mail-'))

const python = join(root, '.venv', 'bin', 'python')
export default defineConfig({
  testDir: './tests',
  testMatch: '*.spec.ts',
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 12_000 },
  retries: 0,
  reporter: [['list']],
  metadata: { mailDir: process.env.E2E_MAIL_DIR, staffPassword: process.env.E2E_STAFF_PASSWORD },
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure', ...devices['Desktop Chrome'] },
  globalTeardown: './tests/teardown.ts',
  webServer: [
    {
      command: `node "${join(frontend, 'tests', 'start-backend.mjs')}"`,
      url: 'http://127.0.0.1:8001/api/v1/health',
      cwd: root,
      reuseExistingServer: false,
      timeout: 30_000,
      env: {
        DATABASE_URL: process.env.E2E_TEST_DATABASE_URL,
        E2E_DATABASE_URL: adminUrl,
        E2E_TEST_DATABASE_NAME: process.env.E2E_TEST_DATABASE_NAME,
        E2E_STAFF_PASSWORD: process.env.E2E_STAFF_PASSWORD,
        E2E_PYTHON: python,
        DJANGO_SECRET_KEY: randomBytes(32).toString('hex'),
        DJANGO_DEBUG: 'false',
        DJANGO_ALLOWED_HOSTS: '127.0.0.1,localhost',
        FRONTEND_ORIGIN: 'http://127.0.0.1:5174',
        APP_ENV: 'development',
        NOTIFICATION_MODE: 'file',
        EMAIL_FILE_PATH: process.env.E2E_MAIL_DIR,
      },
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174 --strictPort',
      url: 'http://127.0.0.1:5174/',
      cwd: frontend,
      reuseExistingServer: false,
      timeout: 30_000,
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8001' },
    },
  ],
})
