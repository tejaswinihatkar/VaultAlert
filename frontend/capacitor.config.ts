import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "io.vaultalert.app",
  appName: "VaultAlert",
  // Next.js static export lands in ./out; Capacitor bundles it into the APK.
  webDir: "out",
  server: {
    androidScheme: "https",
    cleartext: true,
  },
};

export default config;
