import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";

import { AuthProvider } from "@/features/auth/AuthProvider";
import AppTheme from "@/shared/ui/AppTheme";

export const metadata = {
  title: "FinSight",
  description: "AI-powered personal finance insights (budgeting, not advice).",
};

/**
 * Wraps every route with the document shell, Material UI theme, and auth state.
 *
 * @param children - The active Next.js route.
 */
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider>
          <AppTheme>
            <AuthProvider>{children}</AuthProvider>
          </AppTheme>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
