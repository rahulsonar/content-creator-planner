import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Content Creator Planner",
  description: "Plan, organize, and schedule your content creation journey",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <nav className="bg-gray-800 text-white shadow-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex space-x-8">
                <Link href="/" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                  Home
                </Link>
                <Link href="/kanban" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                  Board
                </Link>
                <Link href="/calendar" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                  Calendar
                </Link>
                <Link href="/chat" className="hover:bg-gray-700 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                  AI Chat
                </Link>
              </div>
            </div>
          </div>
        </nav>
        <main>
          {children}
        </main>
      </body>
    </html>
  );
}
