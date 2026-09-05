/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  outputFileTracingRoot: __dirname,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8001/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
