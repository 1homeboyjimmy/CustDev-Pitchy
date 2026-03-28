import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    tailwindcss(),
  ],
  server: {
    host: true, // Позволяет Vite принимать подключения извне (важно для Docker)
    port: 3000,
    open: false,
    allowedHosts: [
      'custdev.pitchy.pro' // Разрешаем наш боевой домен
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
        secure: false
      }
    }
  }
})