import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { Toaster } from "sonner";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "VaultAlert — AI Smart Locker Security Platform",
  description:
    "Enterprise-grade AI-powered smart locker monitoring, multi-factor authentication, surveillance, and threat intelligence platform.",
  keywords: ["smart locker", "security", "IoT", "AI surveillance", "biometric", "enterprise security"],
  authors: [{ name: "VaultAlert", url: "https://vaultalert.io" }],
  openGraph: {
    title: "VaultAlert Security Platform",
    description: "AI-Powered Smart Locker Monitoring & Security",
    type: "website",
    url: "https://app.vaultalert.io",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>
          {children}
          <Toaster
            position="bottom-right"
            toastOptions={{
              style: {
                background: "rgba(15,23,42,0.95)",
                border: "1px solid rgba(255,255,255,0.08)",
                color: "#e2e8f0",
                borderRadius: "12px",
                backdropFilter: "blur(12px)",
              },
            }}
          />
        </Providers>
      </body>
    </html>
  );
}
