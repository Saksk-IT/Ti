import { fileURLToPath, URL } from 'node:url';

import vue from '@vitejs/plugin-vue';
import { defineConfig, type Plugin } from 'vitest/config';

import {
  fixtureRequestId,
  makeBoardsResponse,
  makeDetailResponse,
  makeHotResponse,
  makePlazaListResponse,
  makeSummaryResponse,
} from './src/testing/publicBankFixtures';

function requestIdFromHeader(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? fixtureRequestId : value ?? fixtureRequestId;
}

function mockPublicBankApi(): Plugin {
  return {
    name: 'ti-web-public-bank-mock',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (!request.url) return next();
        const url = new URL(request.url, 'http://127.0.0.1');
        if (!url.pathname.startsWith('/api/public/banks')) return next();

        const requestId = requestIdFromHeader(request.headers['x-request-id']);
        response.setHeader('Content-Type', 'application/json; charset=utf-8');
        response.setHeader('X-Request-ID', requestId);

        if (url.searchParams.get('keyword') === 'error') {
          response.statusCode = 503;
          response.end(JSON.stringify({
            success: false,
            error: { code: 'SERVICE_UNAVAILABLE', message: '服务暂时不可用', details: [] },
            meta: { request_id: requestId },
          }));
          return;
        }

        let payload: object | undefined;
        if (url.pathname === '/api/public/banks/list') payload = makePlazaListResponse(url.searchParams);
        else if (url.pathname === '/api/public/banks/boards') payload = makeBoardsResponse(url.searchParams);
        else if (url.pathname === '/api/public/banks/hot') payload = makeHotResponse(url.searchParams);
        else if (url.pathname === '/api/public/banks/summary') payload = makeSummaryResponse(url.searchParams);
        else {
          const match = url.pathname.match(/^\/api\/public\/banks\/card\/([^/]+)\/([^/]+)$/u);
          if (match) payload = makeDetailResponse(decodeURIComponent(match[1]!), decodeURIComponent(match[2]!));
        }

        if (payload === undefined) {
          response.statusCode = 404;
          response.end(JSON.stringify({
            status: 'error',
            code: 1,
            message: '题库不存在或未公开',
            status_code: 404,
            request_id: requestId,
          }));
          return;
        }

        response.statusCode = 200;
        response.end(JSON.stringify({ ...payload, request_id: requestId }));
      });
    },
  };
}

export default defineConfig(({ mode }) => ({
  plugins: [vue(), ...(mode === 'mock' ? [mockPublicBankApi()] : [])],
  publicDir: false,
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: mode === 'mock'
    ? {}
    : {
        proxy: {
          '/api': {
            target: process.env.TI_JAVA_DEV_ORIGIN ?? 'http://127.0.0.1:18080',
            changeOrigin: true,
          },
        },
      },
  test: {
    environment: 'jsdom',
    environmentOptions: {
      jsdom: { url: 'http://127.0.0.1/' },
    },
    globals: false,
    include: ['tests/unit/**/*.spec.ts'],
    setupFiles: ['./tests/unit/setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
    },
  },
}));
