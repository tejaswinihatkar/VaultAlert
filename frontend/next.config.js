/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so the app can be bundled into a native Capacitor Android shell (APK).
  output: "export",
  images: {
    // The static export has no image optimizer; the app uses plain <img> tags anyway.
    unoptimized: true,
  },
  // Type/lint checks run separately (npm run type-check); skip during the native
  // build so page-data collection stays in-process and doesn't fork extra workers.
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  experimental: { cpus: 1, workerThreads: false },
  // NOTE: async headers() and middleware are unsupported with output:"export"
  // (they require a running Next server). Removed for the native WebView bundle.
};

module.exports = nextConfig;
