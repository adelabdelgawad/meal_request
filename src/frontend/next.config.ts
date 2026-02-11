import type { NextConfig } from "next";
import createNextIntlPlugin from 'next-intl/plugin';

// Parse allowed dev origins from environment variable (comma-separated)
const allowedDevOrigins = process.env.ALLOWED_DEV_ORIGINS
  ? process.env.ALLOWED_DEV_ORIGINS.split(",").map((origin) => origin.trim())
  : [];

// Initialize next-intl plugin with i18n configuration
const withNextIntl = createNextIntlPlugin('./i18n.ts');

const nextConfig: NextConfig = {
  // Enable standalone output for efficient Docker builds
  output: 'standalone',
  // Allow cross-origin requests from specified origins during development
  // Configure via ALLOWED_DEV_ORIGINS env var (comma-separated list)
  // Example: ALLOWED_DEV_ORIGINS=192.168.1.195,192.168.1.100
  allowedDevOrigins,
};

export default withNextIntl(nextConfig);
