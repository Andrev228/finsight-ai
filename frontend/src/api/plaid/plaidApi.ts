import { createApiHeaders } from "@/api/http";
import { API_URL } from "@/shared/config/environment";

type LinkTokenResponse = {
  link_token: string;
};

async function post(
  path: string,
  accessToken: string,
  body?: object,
): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: createApiHeaders(accessToken, body !== undefined),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response;
}

/**
 * Creates a short-lived Plaid Link token for the current user.
 */
export async function createLinkToken(
  accessToken: string,
): Promise<string> {
  const response = await post("/api/plaid/link-token", accessToken);
  const payload = (await response.json()) as LinkTokenResponse;
  return payload.link_token;
}

/**
 * Exchanges Plaid's temporary public token for a stored backend connection.
 */
export async function exchangePublicToken(
  publicToken: string,
  accessToken: string,
): Promise<void> {
  await post("/api/plaid/exchange-token", accessToken, {
    public_token: publicToken,
  });
}
