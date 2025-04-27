import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body>
          <div className="min-h-screen bg-gray-50">
            {children}
          </div>
        </body>
      </html>
    </ClerkProvider>
  );
} 