import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "@/lib/session-context";
import CommandHeader from "@/components/CommandHeader";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Crisis Command — Emergency Response Decision Intelligence",
  description:
    "Don't just find a response plan. Find a plan that survives the next surprise. " +
    "Crisis Command stress-tests emergency response plans against failure scenarios " +
    "and keeps a human commander in control.",
  keywords: ["emergency response", "crisis management", "AI", "resilience", "decision intelligence"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased">
        <SessionProvider>
          <CommandHeader />
          <main className="min-h-[calc(100vh-88px)]">
            {children}
          </main>
        </SessionProvider>
      </body>
    </html>
  );
}
