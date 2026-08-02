import type { Metadata } from "next";
import { Inter, Sora } from "next/font/google";
import "./globals.css";

import { Providers } from "@/app/providers";

const sora = Sora({
  variable: "--font-sora",
  subsets: ["latin"],
});

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LaariLaara — Modern matchmaking, timeless values",
  description:
    "A world-class matrimony experience for candidates and their parents — intelligent compatibility, respectful introductions, and privacy you control.",
};

// Applies the persisted bride/groom theme before first paint (avoids a flash
// of the wrong theme). Runs inline as the first thing in <body>.
const themeInit = `(function(){try{var t=localStorage.getItem("ll-theme");if(t==="bride"||t==="groom"){document.documentElement.dataset.theme=t;}}catch(e){}})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${sora.variable} ${inter.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col font-sans">
        <script dangerouslySetInnerHTML={{ __html: themeInit }} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
