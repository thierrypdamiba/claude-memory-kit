import type { Metadata } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { AuthProvider } from "@/components/auth-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument",
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "CMK",
  description: "Claude Memory Kit. Persistent memory for Claude.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const hasClerk = !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;

  const fontVars = `${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} antialiased`;

  if (hasClerk) {
    return (
      <html lang="en">
        <ClerkProvider>
          <body className={fontVars}>
            <AuthProvider>{children}</AuthProvider>
          </body>
        </ClerkProvider>
      </html>
    );
  }

  return (
    <html lang="en">
      <body className={fontVars}>
        {children}
      </body>
    </html>
  );
}
