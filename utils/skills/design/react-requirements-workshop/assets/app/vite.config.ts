import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

const reviewPort = Number(process.env.REVIEW_RECEIVER_PORT ?? 8765)
if (!Number.isInteger(reviewPort) || reviewPort < 1 || reviewPort > 65535) {
  throw new Error('REVIEW_RECEIVER_PORT must be a valid TCP port')
}

export default defineConfig({ plugins: [react(), tailwindcss()], resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } }, server: { host: '127.0.0.1', proxy: { '/api': `http://127.0.0.1:${reviewPort}` } } })
