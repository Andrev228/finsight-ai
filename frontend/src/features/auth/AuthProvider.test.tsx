import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import {
  AuthProvider,
  useAuth,
} from "@/features/auth/AuthProvider";

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

describe("AuthProvider", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("starts disconnected when the session has no Plaid connection", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => expect(result.current.connectionStateReady).toBe(true));
    expect(result.current.bankConnected).toBe(false);
  });

  it("persists a successful bank connection for the browser session", async () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    await waitFor(() => expect(result.current.connectionStateReady).toBe(true));

    act(() => result.current.markBankConnected());

    expect(result.current.bankConnected).toBe(true);
    expect(sessionStorage.getItem("bankConnected")).toBe("true");
  });
});
