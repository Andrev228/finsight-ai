import { describe, expect, it } from "vitest";

import { createApiHeaders } from "@/api/http";

describe("createApiHeaders", () => {
  it("omits optional headers in local bypass mode", () => {
    expect(createApiHeaders("")).toEqual({});
  });

  it("adds bearer authentication and JSON content type", () => {
    expect(createApiHeaders("token", true)).toEqual({
      Authorization: "Bearer token",
      "Content-Type": "application/json",
    });
  });
});
