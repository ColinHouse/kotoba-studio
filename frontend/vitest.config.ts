import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  // happy-dom mounts the components; it is lighter than jsdom and the tests here
  // assert text and events, never layout.
  test: { include: ['src/**/*.test.ts'], environment: 'happy-dom' },
})
