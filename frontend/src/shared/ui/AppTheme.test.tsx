import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import AppTheme from "@/shared/ui/AppTheme";

function stubMatchMedia(prefersDark: boolean) {
  vi.stubGlobal(
    "matchMedia",
    vi.fn().mockImplementation((query: string) => ({
      matches: prefersDark,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  );
}

describe("AppTheme", () => {
  beforeEach(() => {
    localStorage.clear();
    stubMatchMedia(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders children and defaults to a light-theme toggle", () => {
    render(
      <AppTheme>
        <p>Content</p>
      </AppTheme>,
    );

    expect(screen.getByText("Content")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    ).toBeInTheDocument();
  });

  it("toggles to dark mode and persists the choice", async () => {
    render(
      <AppTheme>
        <p>Content</p>
      </AppTheme>,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Switch to dark theme" }),
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Switch to light theme" }),
      ).toBeInTheDocument(),
    );
    expect(localStorage.getItem("themeMode")).toBe("dark");
  });

  it("restores a saved dark preference on mount", async () => {
    localStorage.setItem("themeMode", "dark");

    render(
      <AppTheme>
        <p>Content</p>
      </AppTheme>,
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Switch to light theme" }),
      ).toBeInTheDocument(),
    );
  });

  it("falls back to the OS dark preference when nothing is saved", async () => {
    stubMatchMedia(true);

    render(
      <AppTheme>
        <p>Content</p>
      </AppTheme>,
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Switch to light theme" }),
      ).toBeInTheDocument(),
    );
  });
});
