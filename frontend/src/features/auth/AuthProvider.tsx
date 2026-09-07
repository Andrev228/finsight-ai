"use client";

import Alert from "@mui/material/Alert";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

type AuthContextValue = {
  accessToken: string;
  setAccessToken: (value: string) => void;
  bankConnected: boolean;
  connectionStateReady: boolean;
  markBankConnected: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Stores the in-memory access token and current browser-session bank state.
 *
 * @param children - Components that need authentication or connection state.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState("");
  const [bankConnected, setBankConnected] = useState(false);
  const [connectionStateReady, setConnectionStateReady] = useState(false);

  useEffect(() => {
    setBankConnected(sessionStorage.getItem("bankConnected") === "true");
    setConnectionStateReady(true);
  }, []);

  const markBankConnected = () => {
    sessionStorage.setItem("bankConnected", "true");
    setBankConnected(true);
  };

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        setAccessToken,
        bankConnected,
        connectionStateReady,
        markBankConnected,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * Returns authentication state and actions from the nearest AuthProvider.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthProvider is missing");
  return context;
}

/**
 * Renders the optional JWT input used when the backend local bypass is disabled.
 */
export function AccessTokenField() {
  const { accessToken, setAccessToken } = useAuth();

  return (
    <Stack spacing={1}>
      <TextField
        type="password"
        label="Access token"
        value={accessToken}
        onChange={(event) => setAccessToken(event.target.value.trim())}
        helperText="Required outside local development; kept only in memory."
        fullWidth
        autoComplete="off"
      />
      {!accessToken && (
        <Alert severity="info">
          Local mode can use the explicit authentication bypass.
        </Alert>
      )}
    </Stack>
  );
}
