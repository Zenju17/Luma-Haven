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

// The staff acceptable-use agreement (P1) appears once per account after sign-in and blocks the page until accepted.
async function acceptAgreement(page: Page) {
  const dialog = page.getByRole('dialog', { name: 'Staff agreement' })
  try {
    await dialog.waitFor({ state: 'visible', timeout: 4000 })
  } catch {
    return // already accepted for this account
  }
  await dialog.getByRole('checkbox').check()
  await dialog.getByRole('button', { name: 'Accept and continue' }).click()
  await expect(dialog).toBeHidden()
}

async function signIn(page: Page, username: string, password: string) {
  await page.goto('/staff')
  await page.getByRole('textbox', { name: 'Username' }).fill(username)
  await page.getByRole('textbox', { name: 'Password' }).fill(password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await acceptAgreement(page)
  await expect(page.getByRole('heading', { name: `Good to see you, ${username}.` })).toBeVisible()
}

test('availability errors are distinct from sold-out dates and can be retried', async ({ page }) => {
  let attempts = 0
  await page.route('**/api/v1/availability?**', async route => {
    attempts += 1
    await route.fulfill({ status: attempts === 1 ? 503 : 200, contentType: 'application/json',
      body: attempts === 1 ? JSON.stringify({ detail: 'Availability service is temporarily unavailable.' }) : '[]' })
  })
  await page.goto(`/rooms?arrival=${hotelDate()}&departure=${hotelDate(1)}&occupants=1`)
  await expect(page.getByRole('alert')).toContainText("We couldn't load room availability")
  await expect(page.getByText('No rooms are available for these dates and guest count.')).toBeHidden()
  await page.getByRole('button', { name: 'Try again', exact: true }).click()
  await expect(page.getByText('No rooms are available for these dates and guest count.')).toBeVisible()
  await expect(page.getByRole('alert')).toBeHidden()
})

test('reception records an explicit in-person identity check on a confirmed booking', async ({ page }) => {
  const { staffPassword } = test.info().config.metadata as { staffPassword: string }
  await signIn(page, 'reception', staffPassword)
  await page.goto('/staff?tab=reservations')
  const row = page.getByRole('row').filter({ hasText: 'Demo Future Guest' })
  await row.getByRole('button', { name: 'Folio', exact: true }).click()
  const dialog = page.getByRole('dialog')
  const verify = dialog.getByRole('button', { name: 'Record in-person verification' })
  await expect(verify).toBeDisabled()
  await dialog.getByLabel("I checked this guest's identity in person.").check()
  await verify.click()
  await expect(dialog.getByText('Guest verification completed.')).toBeVisible()
  await expect(dialog.getByRole('button', { name: 'Check in guest', exact: true })).toBeDisabled()
  await dialog.getByRole('button', { name: 'Close', exact: true }).click()
  const activeStay = page.getByRole('row').filter({ hasText: 'Demo Active Guest' })
  await activeStay.getByRole('button', { name: 'Folio', exact: true }).click()
  await dialog.getByRole('button', { name: 'Check out guest', exact: true }).click()
  await expect(dialog.getByText('CHECKED_OUT', { exact: true })).toBeVisible()
})

test('guest booking, simulated payment, verification, stay, checkout and room inspection', async ({ page, browser }) => {
  const { mailDir, staffPassword, presentationDemo } = test.info().config.metadata as { mailDir: string; staffPassword: string; presentationDemo: boolean }
  const email = `visitor-${randomBytes(6).toString('hex')}@example.test`
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Rest by the river in Phnom Penh' })).toBeVisible()
  await page.getByLabel('Arrival').fill(hotelDate())
  await page.getByLabel('Departure').fill(hotelDate(1))
  await page.getByLabel('Guests').fill('1')
  await page.getByRole('button', { name: 'Search rooms' }).click()
  const room = page.getByRole('article').filter({ hasText: 'Room 101' })
  await expect(room).toBeVisible()
  await room.getByRole('button', { name: 'See price' }).click()
  await page.getByLabel('Full name').fill('Playwright Demo Guest')
  await page.getByLabel('Email for verification').fill(email)
  await page.getByLabel(/I have read and accept/).check()
  await page.getByRole('button', { name: 'Hold this room' }).click()
  await expect(page).toHaveURL(/\/booking\/\d+$/)
  const bookingId = Number(page.url().match(/booking\/(\d+)/)?.[1])
  const reference = (await page.getByText(/Booking [A-F0-9]{16}/).textContent())!.match(/[A-F0-9]{16}/)![0]
  await page.getByRole('button', { name: /Pay balance \(simulation\)/ }).click()
  await expect(page.getByText(/Simulated payment · development only/)).toBeVisible()
  await page.getByRole('button', { name: 'Simulate success' }).click()
  await expect(page.getByText('CONFIRMED', { exact: true })).toBeVisible()

  if (presentationDemo) {
    await expect(page.getByLabel('University demonstration')).toBeVisible()
    await page.getByRole('button', { name: 'Verify demo booking' }).click()
    await expect(page.getByRole('button', { name: 'Check in', exact: true })).toBeVisible()
  } else {
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
  }

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
    await page.getByRole('button', { name: 'Check out' }).click()
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
      await task.getByRole('button', { name: 'Next step' }).click()
    }
    await expect(staffPage.getByText('Room 101 · INSPECTION')).toBeVisible()
    const forbidden = await staff.request.get('http://127.0.0.1:8001/api/v1/staff/reservations')
    expect(forbidden.status()).toBe(403)
    await staffPage.getByRole('button', { name: 'Sign out' }).click()
    await expect(staffPage.getByRole('textbox', { name: 'Username' })).toBeVisible({ timeout: 5_000 })
    await signIn(staffPage, 'reception', staffPassword)
    const inspection = staffPage.getByText('Room 101 · INSPECTION').locator('..')
    await inspection.getByRole('button', { name: 'Next step' }).click()
    await expect(staffPage.getByText('Room 101 · READY')).toBeVisible()
    const readyRoom = staffPage.getByText('Room 101', { exact: true }).locator('..')
    await expect(readyRoom.getByText('Vacant · READY · In service')).toBeVisible()
  } finally {
    await staff.close().catch(() => {})
  }
})

test('guest navigation is public while staff and admin portals enforce separate roles', async ({ page }) => {
  const { staffPassword, mailDir } = test.info().config.metadata as { staffPassword: string; mailDir: string }
  await page.goto('/')
  await expect(page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: /staff|admin/i })).toHaveCount(0)

  await signIn(page, 'reception', staffPassword)
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Administrator sign in' })).toBeVisible()
  expect((await page.request.get('http://127.0.0.1:8001/api/v1/admin/staff')).status()).toBe(403)
  await page.getByRole('textbox', { name: 'Username' }).fill('admin')
  await page.getByRole('textbox', { name: 'Password' }).fill(staffPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await acceptAgreement(page)
  await expect(page.getByRole('heading', { name: 'Administration overview' })).toBeVisible()

  await page.getByRole('button', { name: 'Staff accounts' }).click()
  await expect(page.getByRole('row').filter({ hasText: 'admin' })).toContainText('ADMIN')
  const changedPassword = `Staff${randomBytes(3).toString('hex')}!`
  await page.getByRole('row').filter({ hasText: 'accountant' }).getByRole('button', { name: 'Change password' }).click()
  const passwordDialog = page.getByRole('dialog', { name: 'Change staff password' })
  await passwordDialog.getByLabel('New password', { exact: true }).fill(changedPassword)
  await passwordDialog.getByLabel('Confirm new password').fill(changedPassword)
  await passwordDialog.getByRole('button', { name: 'Save password' }).click()
  await expect(page.getByText('Password changed for accountant. The private local credentials file was updated.')).toBeVisible()
  expect(readFileSync(join(mailDir, 'staff-credentials'), 'utf8')).toContain(`accountant\t${changedPassword}`)

  const changedStaff = await page.context().browser()!.newContext()
  try {
    const staffPage = await changedStaff.newPage()
    await signIn(staffPage, 'accountant', changedPassword)
  } finally {
    await changedStaff.close()
  }
  await page.getByRole('button', { name: 'Audit history' }).click()
  await expect(page.getByText('STAFF_PASSWORD_CHANGED')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Audit history' })).toBeVisible()
  await page.getByRole('button', { name: 'Settings' }).click()
  await expect(page.getByText('Asia/Phnom_Penh')).toBeVisible()
  await page.getByRole('button', { name: 'Reports' }).click()
  await expect(page.getByText('Sold room-nights')).toBeVisible()
  const csv = await page.request.get(`http://127.0.0.1:8001/api/v1/admin/reports/summary?start=${hotelDate()}&end=${hotelDate(1)}&export=csv`)
  expect(csv.status()).toBe(200)
  expect(csv.headers()['content-type']).toContain('text/csv')
  expect(await csv.text()).toContain('net_room_revenue_minor')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: 'Download CSV' }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toBe('hotel-report.csv')

  await page.goto('/staff')
  await expect(page.getByRole('heading', { name: 'Good to see you, reception.' })).toBeVisible()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Staff sign in' })).toBeVisible()

  // The administrator cookie remains valid when the staff session signs out.
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: 'Administration overview' })).toBeVisible()
  await page.goto('/staff')
  await expect(page.getByRole('heading', { name: 'Staff sign in' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Username' }).fill('admin')
  await page.getByRole('textbox', { name: 'Password' }).fill(staffPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await acceptAgreement(page)
  await expect(page.getByRole('heading', { name: 'Good to see you, admin.' })).toBeVisible()
  await page.goto('/admin')
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page.getByRole('heading', { name: 'Administrator sign in' })).toBeVisible()
  await page.goto('/staff')
  await expect(page.getByRole('heading', { name: 'Good to see you, admin.' })).toBeVisible()
})

test('MIS manager journey: executive dashboard, decision support, room types, and reports', async ({ page }) => {
  const { staffPassword } = test.info().config.metadata as { staffPassword: string }

  // 1. Sign in as manager
  await page.goto('/manager')
  await expect(page.getByRole('heading', { name: 'Executive sign in' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Username' }).fill('manager')
  await page.getByRole('textbox', { name: 'Password' }).fill(staffPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await acceptAgreement(page)

  // 2. Verify Manager Intelligence Dashboard loads
  await expect(page.getByRole('heading', { name: 'Manager Intelligence Dashboard' })).toBeVisible()
  await expect(page.getByText('Attention Needed · Decision Support')).toBeVisible()

  // 3. Verify KPI cards
  await expect(page.getByText('Occupancy Rate', { exact: true })).toBeVisible()
  await expect(page.getByText('Average Daily Rate (ADR)', { exact: true })).toBeVisible()
  await expect(page.getByText('Net Room Revenue', { exact: true })).toBeVisible()
  await expect(page.getByText('Net Settled Cash', { exact: true })).toBeVisible()

  // 4. Verify Room-Type breakdown
  await expect(page.getByRole('heading', { name: 'Room-Type Performance Breakdown' })).toBeVisible()

  // 5. Navigate to staff operations to view workflow tabs
  await page.goto('/staff')
  await expect(page.getByRole('heading', { name: 'Good to see you, manager.' })).toBeVisible()
  await page.getByRole('button', { name: 'Reservations & Amendments' }).click()
  await expect(page.getByRole('heading', { name: 'Reservation Management' })).toBeVisible()

  await page.getByRole('button', { name: 'Refunds & Reconciliation' }).click()
  await expect(page.getByRole('heading', { name: 'Refund Management & Ledger Reconciliation' })).toBeVisible()

  await page.getByRole('button', { name: 'Room Rates & Pricing' }).click()
  await expect(page.getByRole('heading', { name: 'Room Rate Management' })).toBeVisible()
})

test('administrator publishes a CMS page and the guest site shows it', async ({ page, browser }) => {
  const { staffPassword } = test.info().config.metadata as { staffPassword: string }
  await page.goto('/admin')
  await page.getByRole('textbox', { name: 'Username' }).fill('admin')
  await page.getByRole('textbox', { name: 'Password' }).fill(staffPassword)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await acceptAgreement(page)
  await page.getByRole('button', { name: 'Content (CMS)' }).click()
  await page.getByRole('button', { name: 'New page' }).click()
  await page.getByLabel('Slug').fill('about-e2e')
  await page.getByLabel('Title').fill('About the E2E Hotel')
  await page.getByLabel('Body (Markdown)').fill('## Welcome\n\nA quiet courtyard.')
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByText('Draft saved.')).toBeVisible()

  const guest = await browser.newContext()
  const guestPage = await guest.newPage()
  try {
    await guestPage.goto('/p/about-e2e')
    await expect(guestPage.getByRole('heading', { name: 'Page not found' })).toBeVisible() // drafts are private
    await page.getByRole('button', { name: 'Publish', exact: true }).click()
    await expect(page.getByText('Published. Guests now see this version.')).toBeVisible()
    await guestPage.goto('/p/about-e2e')
    await expect(guestPage.getByRole('heading', { name: 'About the E2E Hotel' })).toBeVisible()
    await expect(guestPage.getByText('A quiet courtyard.')).toBeVisible()
  } finally {
    await guest.close()
  }
})

