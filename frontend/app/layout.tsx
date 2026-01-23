import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { LanguageProvider } from '@/contexts/LanguageContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: "What's UP - Find Unique Events",
  description: 'Discover unique events in your area',
  manifest: '/manifest.json',
  icons: {
    icon: 'https://placehold.co/32x32/3B82F6/white?text=W',
    apple: 'https://placehold.co/180x180/3B82F6/white?text=W',
  },
}

export const viewport: Viewport = {
  themeColor: '#3B82F6',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body className={inter.className}>
        <LanguageProvider defaultLanguage="en">
          {children}
        </LanguageProvider>
      </body>
    </html>
  )
}
