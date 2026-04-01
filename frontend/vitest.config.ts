import { defineConfig } from 'vitest/config';
import { resolve } from 'path';

export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    include: ['src/**/*.spec.ts'],
    setupFiles: [],
  },
  resolve: {
    alias: {
      '@app/core': resolve(__dirname, 'src/app/core/index.ts'),
      '@app/core/': resolve(__dirname, 'src/app/core/'),
      '@app/shared': resolve(__dirname, 'src/app/shared/index.ts'),
      '@app/shared/': resolve(__dirname, 'src/app/shared/'),
      '@app/data-access': resolve(__dirname, 'src/app/data-access/index.ts'),
      '@app/data-access/': resolve(__dirname, 'src/app/data-access/'),
    },
  },
});
