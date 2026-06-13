import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { ThemeProvider } from "@/components/theme/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Novel Forge — AI 辅助小说创作",
  description: "基于 LLM 的小说创作辅助工具",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="zh-CN"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="flex h-full">
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem("novel-forge-theme")||"dark";if(t==="system")t=window.matchMedia("(prefers-color-scheme: light)").matches?"sepia":"dark";document.documentElement.classList.add(t);document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.classList.add("dark");document.documentElement.setAttribute("data-theme","dark")}})()`,
          }}
        />
        <QueryProvider>
          <ThemeProvider>
            <Sidebar />
            <main className="flex-1 overflow-auto pl-[var(--layout-sidebar-expanded)]">
              {children}
            </main>
          </ThemeProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
