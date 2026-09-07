import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import RequireBankConnection from "@/features/auth/RequireBankConnection";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace }),
}));

const useAuthMock = vi.fn();

vi.mock("@/features/auth/AuthProvider", () => ({
  useAuth: () => useAuthMock(),
}));

describe("RequireBankConnection", () => {
  afterEach(() => {
    replace.mockReset();
    useAuthMock.mockReset();
  });

  it("shows a loading state until the connection state is known", () => {
    useAuthMock.mockReturnValue({
      bankConnected: false,
      connectionStateReady: false,
    });

    render(
      <RequireBankConnection>
        <div>Protected</div>
      </RequireBankConnection>,
    );

    expect(screen.getByText("Checking bank connection...")).toBeInTheDocument();
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects home when the session has no bank connection", async () => {
    useAuthMock.mockReturnValue({
      bankConnected: false,
      connectionStateReady: true,
    });

    render(
      <RequireBankConnection>
        <div>Protected</div>
      </RequireBankConnection>,
    );

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/"));
    expect(screen.queryByText("Protected")).not.toBeInTheDocument();
  });

  it("renders children once a bank connection exists", async () => {
    useAuthMock.mockReturnValue({
      bankConnected: true,
      connectionStateReady: true,
    });

    render(
      <RequireBankConnection>
        <div>Protected</div>
      </RequireBankConnection>,
    );

    expect(screen.getByText("Protected")).toBeInTheDocument();
    await waitFor(() => expect(replace).not.toHaveBeenCalled());
  });
});
