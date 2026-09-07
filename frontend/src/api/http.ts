/**
 * Creates common headers for requests to the FastAPI backend.
 *
 * @param accessToken - Optional bearer JWT.
 * @param json - Whether the request body contains JSON.
 */
export function createApiHeaders(
  accessToken: string,
  json = false,
): Record<string, string> {
  return {
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    ...(json ? { "Content-Type": "application/json" } : {}),
  };
}
