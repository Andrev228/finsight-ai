import { createApiHeaders } from "@/api/http";
import { API_URL } from "@/shared/config/environment";
import type {
  ChatStreamEvent,
  ConversationDetail,
  ConversationSummary,
} from "@/api/chat/types";

async function getJson<T>(
  path: string,
  accessToken: string,
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    headers: createApiHeaders(accessToken),
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/**
 * Returns the current user's conversations ordered by recent activity.
 */
export function listConversations(
  accessToken: string,
): Promise<ConversationSummary[]> {
  return getJson("/api/ai/conversations", accessToken);
}

/**
 * Returns one conversation with its ordered messages.
 */
export function getConversation(
  conversationId: string,
  accessToken: string,
): Promise<ConversationDetail> {
  return getJson(`/api/ai/conversations/${conversationId}`, accessToken);
}

/**
 * Streams parsed chat events from the FastAPI NDJSON endpoint.
 *
 * @param message - User's financial question.
 * @param accessToken - Optional bearer JWT.
 * @param signal - Cancels the underlying HTTP request.
 * @param conversationId - Existing conversation, or undefined for a new chat.
 */
export async function* streamChat(
  message: string,
  accessToken: string,
  signal: AbortSignal,
  conversationId?: string,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${API_URL}/api/ai/chat/stream`, {
    method: "POST",
    headers: createApiHeaders(accessToken, true),
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? null,
    }),
    signal,
  });
  if (!response.ok || !response.body) {
    throw new Error(`Chat request failed with status ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line) yield JSON.parse(line) as ChatStreamEvent;
    }
    if (done) break;
  }
  if (buffer.trim()) yield JSON.parse(buffer) as ChatStreamEvent;
}
