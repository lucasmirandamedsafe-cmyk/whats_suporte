import type { Metadata } from "next";

import { TopNav } from "@/components/nav/TopNav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Piauí Primeira Infância - Dashboard",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className="min-h-screen bg-[#fcfcfb] text-[#0b0b0b] antialiased">
        <TopNav />
        <main className="p-6">{children}</main>
      </body>
    </html>
  );
}
