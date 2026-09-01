import type { NextConfig } from 'next';
import path from 'path';

const REPO_NAME = process.env.NEXT_PUBLIC_REPO_NAME || 'KnowFlow';
// 仅 GitHub Pages 静态导出（NEXT_PUBLIC_STATIC_EXPORT=true）时启用 basePath/静态导出；
// 本地 next dev / SSR 部署使用干净路径，保证 /api/* 代理路由可访问。
const isStatic = process.env.NEXT_PUBLIC_STATIC_EXPORT === 'true';

const nextConfig: NextConfig = {
  ...(isStatic
    ? {
        output: 'export' as const,
        trailingSlash: true,
        basePath: `/${REPO_NAME}`,
        assetPrefix: `/${REPO_NAME}/`,
      }
    : {}),
  allowedDevOrigins: ['*.dev.coze.site'],
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: '*',
        pathname: '/**',
      },
    ],
  },
  // GitHub Pages 静态导出不支持 rewrites / 服务端代理，
  // 仅在未启用静态导出时（比如本地 next dev / SSR 部署）启用 Dify 代理。
  ...(process.env.NEXT_PUBLIC_STATIC_EXPORT !== 'true' && {
    async rewrites() {
      const difyBase = process.env.DIFY_API_BASE_URL || 'http://127.0.0.1/v1';
      const difyUrl = difyBase.replace(/\/v1\/?$/, '');
      return [
        {
          source: '/dify/:path*',
          destination: `${difyUrl}/:path*`,
        },
      ];
    },
  }),
};

export default nextConfig;
