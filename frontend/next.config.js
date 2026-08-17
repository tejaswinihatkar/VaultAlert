/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export so the app can be bundled into a native Capacitor Android shell (APK).
  output: "export",
  images: {
    // The static export has no image optimizer; the app uses plain <img> tags anyway.
    unoptimized: true,
  },
  eslint: { ignoreDuringBuilds: true },
  typescript: { ignoreBuildErrors: true },
  // Cap build worker parallelism so page-data collection doesn't fork extra
  // workers (avoids EAGAIN spawn failures in constrained containers).
  experimental: { cpus: 1, workerThreads: false },
  // NOTE: middleware and async headers() are unsupported with output:"export".
};

module.exports = nextConfig;
