/** @type {import('next').NextConfig} */
const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=63072000; includeSubDomains; preload'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'X-Frame-Options',
            value: 'SAMEORIGIN'
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'geolocation=(), microphone=(), camera=()'
          }
        ]
      }
    ];
  },
  // Enable strict mode for better development experience
  reactStrictMode: true,
  // Disable source maps in production
  productionBrowserSourceMaps: false,
  // Configure image domains
  images: {
    domains: ['localhost'],
  },
  // Configure webpack
  webpack: (config, { dev, isServer }) => {
    // Add security-related webpack configurations
    if (!dev && !isServer) {
      // Enable source map protection in production
      config.devtool = 'source-map';
    }
    return config;
  }
};

module.exports = nextConfig; 