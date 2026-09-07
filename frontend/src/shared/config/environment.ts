/**
 * Public backend origin embedded into the browser bundle at build time.
 */
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
