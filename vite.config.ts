import { defineConfig, type ProxyOptions } from 'vite'
import vue from '@vitejs/plugin-vue'
import { existsSync, readFileSync } from 'node:fs'
import { parseEnv } from 'node:util'

export default defineConfig(({ mode }) => {
  // Vite's loadEnv logs returned values with --debug. Parse server settings
  // privately, preserving file precedence and process-environment overrides.
  const env: NodeJS.ProcessEnv = Object.assign({}, ...[
    '.env', '.env.local', `.env.${mode}`, `.env.${mode}.local`,
  ].filter(existsSync).map((file) => parseEnv(readFileSync(file, 'utf8'))), process.env)
  if (env.VITE_API_KEY) {
    throw new Error('Use MSGVAULT_API_KEY in the server environment. VITE_API_KEY exposes the credential to browsers.')
  }
  const apiKey = env.MSGVAULT_API_KEY
  const proxy: ProxyOptions = {
    target: env.MSGVAULT_API_URL || 'http://127.0.0.1:8080',
    changeOrigin: true,
    configure(proxy) {
      // Keep the value out of the configuration printed by Vite debug logs.
      proxy.on('proxyReq', (request) => {
        if (apiKey) request.setHeader('X-API-Key', apiKey)
      })
    },
  }
  return {
    plugins: [vue()],
    build: {
      sourcemap: true,
    },
    server: {
      host: env.MSGVAULT_FRONTEND_HOST || '127.0.0.1',
      port: 3000,
      allowedHosts: env.MSGVAULT_FRONTEND_ALLOWED_HOSTS?.split(',').map((host) => host.trim()).filter(Boolean) || [],
      proxy: {
        '/api': { ...proxy },
        '/attachments': { ...proxy },
      },
    },
  }
})
