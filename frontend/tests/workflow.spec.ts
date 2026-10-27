import { randomBytes } from 'node:crypto'
import { readFileSync, readdirSync } from 'node:fs'
import { join } from 'node:path'
import { expect, test, type Page } from '@playwright/test'

function hotelDate(offset = 0) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Phnom_Penh', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map(({ type, value }) => [type, value]))
  const current = new Date(`${values.year}-${values.month}-${values.day}T00:00:00Z`)
  current.setUTCDate(current.getUTCDate() + offset)
  return current.toISOString().slice(0, 10)
}

async function signIn(page: Page, username: string, password: string) {
  await page.goto('/staff')
  await page.getByRole('textbox', { name: 'Username' }).fill(username)
  await page.getByRole('textbox', { name: 'Password' }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: `Good to see you, ${username}.` })).toBeVisible()
}

test('guest booking, simulated payment, verification, stay, checkout and room inspection', async ({ page, browser }) => {
  const { mailDir, staffPassword } = test.info().config.metadata as { mailDir: string; staffPassword: string }
  const email = `visitor-${randomBytes(6).toString('hex')}@example.test`
  await page.goto('/')
  await page.getByLabel('Arrival').fill(hotelDate())
  await page.getByLabel('Departure').fill(hotelDate(1))
  await page.getByLabel('Guests').fill('1')
  await page.getByRole('button', { name: 'Search rooms →' }).click()
  const room = page.getByRole('article').filter({ hasText: 'Room 101' })
  await expect(room).toBeVisible()
  await room.getByRole('button', { name: 'Select →' }).click()
  await page.getByLabel('Full name').fill('Playwright Demo Guest')
  await page.getByLabel('Email for verification').fill(email)
  await page.getByRole('button', { name: 'Hold this room →' }).click()
  await expect(page).toHaveURL(/\/booking\/\d+$/)
  const bookingId = Number(page.url().match(/booking\/(\d+)/)?.[1])
  const reference = (await page.getByText(/Booking [A-F0-9]{16}/).textContent())!.match(/[A-F0-9]{16}/)![0]
  await page.getByRole('button', { name: /Pay balance \(simulation\)/ }).click()
  await expect(page.getByText(/DEVELOPMENT SIMULATION/)).toBeVisible()
  await page.getByRole('button', { name: 'Simulate success' }).click()
  await expect(page.getByText('CONFIRMED', { exact: true })).toBeVisible()

  await page.goto('/verify')
  await page.getByLabel('Booking reference').fill(reference)
  await page.getByLabel('Email address').fill(email)
  const before = new Set(readdirSync(mailDir))
  await page.getByRole('button', { name: 'Send verification code' }).click()
  await expect.poll(() => readdirSync(mailDir).filter(name => !before.has(name)).length).toBe(1)
  const message = readFileSync(join(mailDir, readdirSync(mailDir).find(name => !before.has(name))!), 'utf8')
  const code = message.match(/Your verification code is (\d{6})/)?.[1]
  expect(code).toMatch(/^\d{6}$/)
  await page.getByLabel('Six-digit code').fill(code!)
  await page.getByRole('button', { name: 'Verify and continue' }).click()
  await expect(page).toHaveURL(new RegExp(`/booking/${bookingId}$`))

  const unauthorised = await browser.newContext()
  try {
    const response = await unauthorised.request.get(`http://127.0.0.1:8001/api/v1/reservations/${bookingId}`)
    expect(response.status()).toBe(403)
  } finally {
    await unauthorised.close()
  }

  await page.getByRole('button', { name: 'Check in' }).click()
  await expect(page.getByText('CHECKED IN', { exact: true })).toBeVisible()
  await page.getByPlaceholder('How can we help?').fill('Playwright demonstration towels')
  await page.getByRole('button', { name: 'Send request' }).click()
  await expect(page.getByText(/Playwright demonstration towels/)).toBeVisible()

  const staff = await browser.newContext()
  const staffPage = await staff.newPage()
  try {
    await signIn(staffPage, 'reception', staffPassword)
    const requestRow = staffPage.getByText('Towels · Playwright demonstration towels · SUBMITTED').locator('..')
    await requestRow.getByRole('button', { name: 'Complete' }).click()
    await expect(staffPage.getByText('Towels · Playwright demonstration towels · COMPLETED')).toBeVisible()
    await page.reload()
    await expect(page.getByText('COMPLETED', { exact: true })).toBeVisible()
    await expect(page.getByText('Balance $0.00')).toBeVisible()
    await page.getByRole('button', { name: 'Check out →' }).click()
    await expect(page.getByText('CHECKED OUT', { exact: true })).toBeVisible()
    await expect(page.getByText('Thank you for staying with us.')).toBeVisible()

    await staffPage.reload()
    await expect(staffPage.getByRole('heading', { name: 'Good to see you, reception.' })).toBeVisible()
    await expect(staffPage.getByRole('button', { name: 'Sign out' })).toBeVisible({ timeout: 10_000 })
    await staffPage.getByRole('button', { name: 'Sign out' }).click({ timeout: 10_000 })
    await expect(staffPage.getByRole('textbox', { name: 'Username' })).toBeVisible({ timeout: 5_000 })
    await signIn(staffPage, 'housekeeping', staffPassword)
    for (const status of ['DIRTY', 'CLEANING']) {
      const task = staffPage.getByText(`Room 101 · ${status}`).locator('..')
      await task.getByRole('button', { name: 'Next step →' }).click()
    }
    await expect(staffPage.getByText('Room 101 · INSPECTION')).toBeVisible()
    const forbidden = await staff.request.get('http://127.0.0.1:8001/api/v1/staff/reservations')
    expect(forbidden.status()).toBe(403)
    await staffPage.getByRole('button', { name: 'Sign out' }).click()
    await expect(staffPage.getByRole('textbox', { name: 'Username' })).toBeVisible({ timeout: 5_000 })
    await signIn(staffPage, 'reception', staffPassword)
    const inspection = staffPage.getByText('Room 101 · INSPECTION').locator('..')
    await inspection.getByRole('button', { name: 'Next step →' }).click()
    await expect(staffPage.getByText('Room 101 · READY')).toBeVisible()
    const readyRoom = staffPage.getByText('Room 101', { exact: true }).locator('..')
    await expect(readyRoom.getByText('Vacant · READY · In service')).toBeVisible()
  } finally {
    await staff.close().catch(() => {})
  }
})

test('guest navigation is public while staff and admin portals enforce separate roles', async ({ page }) => {
  const { staffPassword } = test.info().config.metadata as { staffPassword: string }
  await page.goto('/')
  await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: /staff|admin/i })).toHaveCount(0)

  await signIn(page, 'reception', staffPassword)
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Administrator access required' })).toBeVisible()
  expect((await page.request.get('http://127.0.0.1:8001/api/v1/admin/staff')).status()).toBe(403)
  await page.getByRole('link', { name: 'Open staff workspace' }).click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Staff sign in' })).toBeVisible()

  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Administrator sign in' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Username' }).fill('admin')
  await page.getByRole('textbox', { name: 'Password' }).fill(staffPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.getByRole('heading', { name: 'Administration overview' })).toBeVisible()

  await page.getByRole('button', { name: 'Staff accounts' }).click()
  await expect(page.getByRole('row').filter({ hasText: 'admin' })).toContainText('ADMIN')
  await page.getByRole('button', { name: 'Audit history' }).click()
  await expect(page.getByRole('heading', { name: 'Audit history' })).toBeVisible()
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByText('Asia/Phnom_Penh')).toBeVisible()
  await page.getByRole('button', { name: 'Reports' }).click()
  await expect(page.getByText('Sold room-nights')).toBeVisible()
  const csv = await page.request.get(`http://127.0.0.1:8001/api/v1/reports/summary?start=${hotelDate()}&end=${hotelDate(1)}&export=csv`)
  expect(csv.status()).toBe(200)
  expect(csv.headers()['content-type']).toContain('text/csv')
  expect(await csv.text()).toContain('net_room_revenue_minor')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Download CSV' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('hotel-report.csv')

  await page.goto('/staff')
  await expect(page).toHaveURL(/\/admin$/)
})
