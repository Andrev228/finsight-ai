"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/features/auth/AuthProvider";
import {
  createLinkToken,
  exchangePublicToken,
} from "@/api/plaid/plaidApi";
import { PLAID_SCRIPT_URL } from "@/features/plaid/constants";

type PlaidHandler = {
  open: () => void;
};

type PlaidConfiguration = {
  token: string;
  onSuccess: (publicToken: string) => void;
  onExit: (error: unknown) => void;
};

declare global {
  interface Window {
    Plaid?: {
      create: (configuration: PlaidConfiguration) => PlaidHandler;
    };
  }
}

let plaidScriptPromise: Promise<void> | undefined;

function loadPlaidScript(): Promise<void> {
  if (window.Plaid) {
    return Promise.resolve();
  }
  if (plaidScriptPromise) {
    return plaidScriptPromise;
  }

  plaidScriptPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = PLAID_SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Plaid Link"));
    document.head.appendChild(script);
  });
  return plaidScriptPromise;
}

type PlaidLinkState = {
  connectBank: () => Promise<void>;
  loading: boolean;
  message?: string;
  error?: string;
};

/**
 * Orchestrates the Plaid Link flow: loads the script, exchanges tokens,
 * and navigates to the chat page, exposing only UI-facing state.
 */
export function usePlaidLink(): PlaidLinkState {
  const router = useRouter();
  const { accessToken, markBankConnected } = useAuth();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();

  const connectBank = async () => {
    setLoading(true);
    setMessage(undefined);
    setError(undefined);

    try {
      const [token] = await Promise.all([
        createLinkToken(accessToken),
        loadPlaidScript(),
      ]);

      const handler = window.Plaid?.create({
        token,
        onSuccess: async (publicToken) => {
          try {
            await exchangePublicToken(publicToken, accessToken);
            markBankConnected();
            setMessage("Bank account connected");
            router.push("/chat");
          } catch {
            setError("Plaid connected, but saving the connection failed");
          } finally {
            setLoading(false);
          }
        },
        onExit: (exitError) => {
          if (exitError) {
            setError("Plaid Link closed with an error");
          }
          setLoading(false);
        },
      });

      if (!handler) {
        throw new Error("Plaid Link is unavailable");
      }
      handler.open();
    } catch {
      setError("Could not start Plaid Link");
      setLoading(false);
    }
  };

  return { connectBank, loading, message, error };
}
