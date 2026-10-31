import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import ModelSelector from "@/components/ModelSelector";
import NavLinks from "@/components/NavLinks";
import "katex/dist/katex.min.css";
import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css";
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
  title: "Study Question Generator",
  description: "Extract and organize textbook questions for exam prep",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="ko"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col">
        <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
          <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-2.5 sm:h-14 sm:flex-nowrap sm:py-0">
            <Link href="/" className="flex shrink-0 items-center gap-2">
              <span className="grid h-6 w-6 place-items-center rounded-[7px] bg-primary text-[11px] font-semibold tracking-tight text-primary-foreground">
                Q
              </span>
              <span className="text-[15px] font-semibold tracking-[-0.02em]">
                Study Q-Gen
              </span>
            </Link>
            <NavLinks />
            <ModelSelector />
          </nav>
        </header>
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 pb-16 pt-10">
          {children}
        </main>
      </body>
    </html>
  );
}
