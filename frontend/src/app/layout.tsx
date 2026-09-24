/**
 * Root layout for the AI Car Mechanic app.
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AI Car Mechanic — Powered by Gemini",
  description:
    "Describe your car problem and get an AI-powered diagnosis and service booking from a senior automobile technician.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="bg-slate-950 text-slate-100 antialiased h-full">
        {children}
      </body>
    </html>
  );
}
