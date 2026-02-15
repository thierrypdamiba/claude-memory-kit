import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Amoeba Labs",
  description:
    "How far can one person go with AI? Building real tools, shipping solo.",
  icons: {
    icon: "/logo.png",
    apple: "/logo.png",
  },
  openGraph: {
    title: "Amoeba Labs",
    description:
      "How far can one person go with AI? Building real tools, shipping solo.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
