import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  base: '/', // 确保静态资源使用根路径
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // 确保公共目录资源被复制
    copyPublicDir: true,
    // 分包策略，减少内存峰值
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-router': ['react-router-dom'],
          'vendor-antd': ['antd', '@ant-design/icons'],
        },
      },
    },
    chunkSizeWarningLimit: 2000,
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://140.143.125.234:8000',
        changeOrigin: true,
      },
    },
  },
})
