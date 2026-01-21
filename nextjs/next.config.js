/**
 * Next.js Configuration
 * Enables WebSocket support for real-time chat
 */

const nextConfig = {
  /* config options here */
  experimental: {
    // Enable server actions for better server-side processing
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  // WebSocket support requires custom server setup
  // The /api/ws route handles WebSocket upgrades
};

module.exports = nextConfig;
