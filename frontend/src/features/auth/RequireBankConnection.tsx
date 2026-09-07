"use client";

import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import { useRouter } from "next/navigation";
import { ReactNode, useEffect } from "react";

import { useAuth } from "@/features/auth/AuthProvider";

/**
 * Renders children only after this browser session has connected a bank.
 *
 * @param children - Protected page content; otherwise the user returns to `/`.
 */
export default function RequireBankConnection({
  children,
}: {
  children: ReactNode;
}) {
  const router = useRouter();
  const { bankConnected, connectionStateReady } = useAuth();

  useEffect(() => {
    if (connectionStateReady && !bankConnected) router.replace("/");
  }, [bankConnected, connectionStateReady, router]);

  if (!connectionStateReady || !bankConnected) {
    return (
      <Stack alignItems="center" spacing={2} py={8}>
        <CircularProgress />
        <Typography color="text.secondary">
          Checking bank connection...
        </Typography>
      </Stack>
    );
  }

  return children;
}
