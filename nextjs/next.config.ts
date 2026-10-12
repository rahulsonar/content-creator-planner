import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    // Enable server actions for better server-side processing
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  // Enable WebSocket connections in development
  webpack: (config, { dev, isServer }) => {
    if (dev && !isServer) {
      // Allow HMR WebSocket to work with custom server
      config.infrastructureLogging = {
        level: 'error',
      };
    }
    return config;
  },
};

export default nextConfig;
