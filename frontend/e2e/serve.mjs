// Start the real backend on a throwaway data directory for the smoke test.
//
// The user's KOTOBA_DATA_DIR is never touched (AGENTS.md hard rule). The data
// directory lives under test-results/, which Playwright wipes at the start of
// every run, so a hard kill cannot leave it behind for long.
import { spawn, spawnSync } from 'node:child_process'
import { mkdirSync, rmSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const dataDir = join(here, '..', 'test-results', 'e2e-data')
rmSync(dataDir, { recursive: true, force: true })
mkdirSync(dataDir, { recursive: true })

const isWindows = process.platform === 'win32'
const backend = join(here, '..', '..', 'backend')
// No `detached`: Playwright kills the webServer's whole process group when the
// run ends, which is exactly what has to die with it. Detaching put uv/python in
// a separate group, and they kept the inherited stdout open, so Playwright's
// teardown waited on a pipe that would never close (the job hung for 19 minutes
// after the test itself had passed on CI).
const child = spawn(
  'uv',
  ['run', 'python', '-m', 'kotoba', 'serve', '--data-dir', dataDir, '--port', '8731'],
  { cwd: backend, stdio: 'inherit' },
)

function killTree() {
  try {
    if (isWindows) {
      spawnSync('taskkill', ['/pid', String(child.pid), '/T', '/F'], { stdio: 'ignore' })
    } else {
      child.kill()
    }
  } catch {
    /* already gone */
  }
}

function cleanup() {
  killTree()
  try {
    rmSync(dataDir, { recursive: true, force: true })
  } catch {
    /* the next run wipes test-results anyway */
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    cleanup()
    process.exit(0)
  })
}
child.on('exit', (code) => {
  cleanup()
  process.exit(code ?? 1)
})
