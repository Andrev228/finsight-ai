"use client";

import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Stack from "@mui/material/Stack";

import { usePlaidLink } from "@/features/plaid/usePlaidLink";

/**
 * Runs Plaid Link, saves the resulting item, and navigates to the chat page.
 */
export default function PlaidLinkButton() {
  const { connectBank, loading, message, error } = usePlaidLink();

  return (
    <Stack spacing={2} alignItems="flex-start">
      <Button
        variant="contained"
        onClick={connectBank}
        disabled={loading}
        startIcon={loading ? <CircularProgress size={18} /> : undefined}
      >
        {loading ? "Connecting..." : "Connect a bank"}
      </Button>
      {message && <Alert severity="success">{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
    </Stack>
  );
}
