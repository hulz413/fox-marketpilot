import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { cookies } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MarketPilot",
  description: "面向中文演示场景的商机顾问 Agent",
};

const languageStorageKey = "marketpilot:language";

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const initialLanguage =
    cookieStore.get(languageStorageKey)?.value === "en" ? "en" : "zh";

  return (
    <html
      lang={initialLanguage === "zh" ? "zh-CN" : "en"}
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body>
        <Providers initialLanguage={initialLanguage}>{children}</Providers>
      </body>
    </html>
  );
}
