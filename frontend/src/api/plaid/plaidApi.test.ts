import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createLinkToken,
  exchangePublicToken,
} from "@/api/plaid/plaidApi";

describe("Plaid API", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("creates a Link token with authentication", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ link_token: "link-sandbox-test" }), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(createLinkToken("jwt")).resolves.toBe("link-sandbox-test");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/plaid/link-token",
      expect.objectContaining({
        method: "POST",
        headers: { Authorization: "Bearer jwt" },
      }),
    );
  });

  it("exchanges the public token as JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await exchangePublicToken("public-token", "");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/plaid/exchange-token",
      expect.objectContaining({
        body: JSON.stringify({ public_token: "public-token" }),
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("rejects failed backend responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 502 })),
    );

    await expect(createLinkToken("")).rejects.toThrow(
      "Request failed with status 502",
    );
  });
});
