import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AuthProvider } from "@/features/auth/AuthProvider";
import { usePlaidLink } from "@/features/plaid/usePlaidLink";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/api/plaid/plaidApi", () => ({
  createLinkToken: vi.fn(),
  exchangePublicToken: vi.fn(),
}));

import {
  createLinkToken,
  exchangePublicToken,
} from "@/api/plaid/plaidApi";

const createLinkTokenMock = vi.mocked(createLinkToken);
const exchangePublicTokenMock = vi.mocked(exchangePublicToken);

type PlaidConfiguration = {
  token: string;
  onSuccess: (publicToken: string) => void;
  onExit: (error: unknown) => void;
};

function wrapper({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}

function stubPlaid(): { getConfig: () => PlaidConfiguration; open: ReturnType<typeof vi.fn> } {
  let config: PlaidConfiguration | undefined;
  const open = vi.fn();
  window.Plaid = {
    create: (received: PlaidConfiguration) => {
      config = received;
      return { open };
    },
  };
  return {
    getConfig: () => {
      if (!config) throw new Error("Plaid.create was not called");
      return config;
    },
    open,
  };
}

describe("usePlaidLink", () => {
  afterEach(() => {
    delete window.Plaid;
    sessionStorage.clear();
    push.mockReset();
    createLinkTokenMock.mockReset();
    exchangePublicTokenMock.mockReset();
  });

  it("opens Plaid Link with a fetched link token", async () => {
    createLinkTokenMock.mockResolvedValue("link-sandbox-test");
    const plaid = stubPlaid();

    const { result } = renderHook(() => usePlaidLink(), { wrapper });

    await act(async () => {
      await result.current.connectBank();
    });

    expect(createLinkTokenMock).toHaveBeenCalledOnce();
    expect(plaid.getConfig().token).toBe("link-sandbox-test");
    expect(plaid.open).toHaveBeenCalledOnce();
    expect(result.current.loading).toBe(true);
  });

  it("exchanges the token, marks the session, and navigates on success", async () => {
    createLinkTokenMock.mockResolvedValue("link-sandbox-test");
    exchangePublicTokenMock.mockResolvedValue(undefined);
    const plaid = stubPlaid();

    const { result } = renderHook(() => usePlaidLink(), { wrapper });
    await act(async () => {
      await result.current.connectBank();
    });

    await act(async () => {
      await plaid.getConfig().onSuccess("public-token");
    });

    expect(exchangePublicTokenMock).toHaveBeenCalledWith("public-token", "");
    expect(sessionStorage.getItem("bankConnected")).toBe("true");
    expect(push).toHaveBeenCalledWith("/chat");
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.message).toBe("Bank account connected");
  });

  it("reports an error when saving the connection fails", async () => {
    createLinkTokenMock.mockResolvedValue("link-sandbox-test");
    exchangePublicTokenMock.mockRejectedValue(new Error("boom"));
    const plaid = stubPlaid();

    const { result } = renderHook(() => usePlaidLink(), { wrapper });
    await act(async () => {
      await result.current.connectBank();
    });
    await act(async () => {
      await plaid.getConfig().onSuccess("public-token");
    });

    expect(push).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(result.current.error).toBe(
        "Plaid connected, but saving the connection failed",
      ),
    );
    expect(result.current.loading).toBe(false);
  });

  it("reports an error when the link token request fails", async () => {
    createLinkTokenMock.mockRejectedValue(new Error("network"));

    const { result } = renderHook(() => usePlaidLink(), { wrapper });
    await act(async () => {
      await result.current.connectBank();
    });

    await waitFor(() =>
      expect(result.current.error).toBe("Could not start Plaid Link"),
    );
    expect(result.current.loading).toBe(false);
  });

  it("stops loading when the user exits Plaid Link with an error", async () => {
    createLinkTokenMock.mockResolvedValue("link-sandbox-test");
    const plaid = stubPlaid();

    const { result } = renderHook(() => usePlaidLink(), { wrapper });
    await act(async () => {
      await result.current.connectBank();
    });

    act(() => plaid.getConfig().onExit(new Error("exit")));

    await waitFor(() =>
      expect(result.current.error).toBe("Plaid Link closed with an error"),
    );
    expect(result.current.loading).toBe(false);
  });
});
