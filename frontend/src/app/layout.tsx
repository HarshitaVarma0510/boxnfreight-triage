import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "BoxNFreight Support Portal & Ticket Triage",
  description: "AI-Powered Support Ticket Triage for BoxNFreight Logistics",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col bg-slate-50 text-slate-900 antialiased font-sans">
        {children}
      </body>
    </html>
  );
}
