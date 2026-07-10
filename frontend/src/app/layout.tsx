import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Northwind Gadgets AI Assistant",
  description:
    "Dual-mode agentic RAG chatbot — Ask about policies, orders, products, and more using intelligent document search and SQL queries.",
  icons: {
    icon: "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>",
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
