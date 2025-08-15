"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">MI</span>
              </div>
              <span className="font-semibold text-lg text-gray-900">
                Meeting Insights
              </span>
            </Link>

            {/* Navigation Links */}
            <div className="flex space-x-8">
              <Link
                href="/"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                  pathname === "/"
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Meeting List
              </Link>
              <Link
                href="/upload"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                  pathname === "/upload"
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Upload Meeting
              </Link>
              <Link
                href="/language-samples"
                className={`px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200 ${
                  pathname === "/language-samples"
                    ? "bg-blue-100 text-blue-700"
                    : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
                }`}
              >
                Language Samples
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        {children}
      </main>
    </div>
  );
}