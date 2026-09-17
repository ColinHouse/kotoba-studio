import { defineConfig } from '@playwright/test'

/**
 * The smoke test runs against the real server (temp data dir, see e2e/serve.mjs)
 * serving the built web app — the same shape the user runs.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:8731',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'node e2e/serve.mjs',
    url: 'http://127.0.0.1:8731/api/health',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
