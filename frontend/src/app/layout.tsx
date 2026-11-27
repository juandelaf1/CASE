import type { Metadata } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/layout/app-shell";

const plexSans = IBM_Plex_Sans({ variable: "--font-plex-sans", subsets: ["latin"], weight: ["400","500","600","700"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400","500"] });

export const metadata: Metadata = {
  title: "CASE — Hybrid Intelligence Platform",
  description: "Case Assessment and Structured Evaluation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${plexSans.variable} ${plexMono.variable} h-full`}>
      <body className="min-h-full bg-bg text-text antialiased">
        <Providers><AppShell>{children}</AppShell></Providers>
      </body>
    </html>
  );
}
