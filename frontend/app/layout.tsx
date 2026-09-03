import { AppRouterCacheProvider } from "@mui/material-nextjs/v15-appRouter";

import AppTheme from "./theme";

export const metadata = {
  title: "finsight-ai",
  description: "AI-powered personal finance insights (budgeting, not advice).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppRouterCacheProvider>
          <AppTheme>{children}</AppTheme>
        </AppRouterCacheProvider>
      </body>
    </html>
  );
}
