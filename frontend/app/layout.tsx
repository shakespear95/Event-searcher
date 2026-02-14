import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/ThemeProvider'
import { LanguageProvider } from '@/contexts/LanguageContext'
import { UserPreferencesProvider } from '@/contexts/UserPreferencesContext'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: "What's UP - Find Unique Events",
  description: 'Discover unique events in your area',
  manifest: '/manifest.json',
  icons: {
    icon: '/icon-192.svg',
    apple: '/icon-192.svg',
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
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="mobile-web-app-capable" content="yes" />
      </head>
      <body className={inter.className}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <LanguageProvider defaultLanguage="en">
            <UserPreferencesProvider>
              {children}
            </UserPreferencesProvider>
          </LanguageProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
