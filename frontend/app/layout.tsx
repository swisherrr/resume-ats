import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Toaster } from 'react-hot-toast';

const inter = Inter({ 
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Resume ATS - Optimize Your Resume for ATS Systems',
  description: 'Upload your resume and get instant ATS compatibility analysis with keyword matching, scoring, and improvement suggestions.',
  keywords: 'ATS, resume, optimization, keywords, job application, career',
  authors: [{ name: 'Resume ATS' }],
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
  openGraph: {
    title: 'Resume ATS - Optimize Your Resume for ATS Systems',
    description: 'Upload your resume and get instant ATS compatibility analysis with keyword matching, scoring, and improvement suggestions.',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Resume ATS - Optimize Your Resume for ATS Systems',
    description: 'Upload your resume and get instant ATS compatibility analysis with keyword matching, scoring, and improvement suggestions.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className={`${inter.className} antialiased`}>
        {children}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#22c55e',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ef4444',
                secondary: '#fff',
              },
            },
          }}
        />
      </body>
    </html>
  );
}
