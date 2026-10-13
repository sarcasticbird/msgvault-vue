// @vitest-environment node
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createServer as createHttpServer } from 'node:http'
import type { AddressInfo } from 'node:net'
import { execFile } from 'node:child_process'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { resolve, join } from 'node:path'
import { promisify } from 'node:util'
import { createServer, type UserConfig, type ViteDevServer } from 'vite'
import config from '../vite.config'

describe('server-side archive authentication', () => {
  let vite: ViteDevServer | undefined
  afterEach(async () => {
    await vite?.close()
    vi.unstubAllEnvs()
  })

  it('keeps a file-based server credential out of Vite debug output', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'msgvault-debug-'))
    const credential = 'debug-output-private-fixture-key'
    const env = { HOME: directory, PATH: process.env.PATH || '' }
    try {
      await writeFile(join(directory, '.env'), `MSGVAULT_API_KEY=${credential}\n`)
      await writeFile(join(directory, 'index.html'), '<html><body>fixture</body></html>')
      const { stdout, stderr } = await promisify(execFile)(process.execPath, [
        resolve('node_modules/vite/bin/vite.js'), 'build', '--debug',
        '--config', resolve('vite.config.ts'),
      ], { cwd: directory, env, timeout: 15000 })
      expect(stdout).toContain('built in')
      expect((stdout + stderr).includes(credential)).toBe(false)
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('authenticates JSON and inline image requests without a browser key', async () => {
    const upstream = createHttpServer((request, response) => {
      if (request.headers['x-api-key'] !== 'server-only-trial-key') {
        response.writeHead(401).end('missing server credential')
        return
      }
      response.end(request.url?.includes('/inline?') ? 'image bytes' : 'archive data')
    })
    await new Promise<void>((resolve) => upstream.listen(0, '127.0.0.1', resolve))
    const target = `http://127.0.0.1:${(upstream.address() as AddressInfo).port}`
    vi.stubEnv('MSGVAULT_API_KEY', 'server-only-trial-key')
    vi.stubEnv('MSGVAULT_API_URL', target)
    try {
      const resolved = typeof config === 'function'
        ? await config({ command: 'serve', mode: 'test', isSsrBuild: false, isPreview: false })
        : await config
      const options = resolved as UserConfig
      const proxies = options.server?.proxy ?? {}
      // Use a private fixture port even when testing the old fixed-port config.
      for (const value of Object.values(proxies)) {
        if (typeof value !== 'string') value.target = target
      }
      vite = await createServer({
        ...options,
        configFile: false,
        server: { ...options.server, host: '127.0.0.1', port: 0, open: false },
      })
      await vite.listen()
      const port = (vite.httpServer!.address() as AddressInfo).port
      for (const path of ['/api/v1/stats/total', '/api/v1/messages/42/inline?cid=part']) {
        const result = await fetch(`http://127.0.0.1:${port}${path}`)
        expect(result.status).toBe(200)
        expect(await result.text()).toBe(path.includes('/inline?') ? 'image bytes' : 'archive data')
      }
    } finally {
      await vite?.close()
      vite = undefined
      await new Promise<void>((resolve, reject) => upstream.close((error) => error ? reject(error) : resolve()))
    }
  })
})
