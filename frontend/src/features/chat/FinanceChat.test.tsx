import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type {
  ChatStreamEvent,
  ConversationDetail,
  ConversationSummary,
} from "@/api/chat/types";
import FinanceChat from "@/features/chat/FinanceChat";

const listConversations = vi.fn();
const getConversation = vi.fn();
const streamChat = vi.fn();

vi.mock("@/api/chat/chatApi", () => ({
  listConversations: (...args: unknown[]) => listConversations(...args),
  getConversation: (...args: unknown[]) => getConversation(...args),
  streamChat: (...args: unknown[]) => streamChat(...args),
}));

vi.mock("@/features/auth/AuthProvider", () => ({
  useAuth: () => ({ accessToken: "" }),
}));

function eventStream(events: ChatStreamEvent[]) {
  return (async function* () {
    for (const event of events) yield event;
  })();
}

function typeQuestion(value: string) {
  const input = screen.getByPlaceholderText("Message FinSight");
  fireEvent.change(input, { target: { value } });
  return input;
}

describe("FinanceChat", () => {
  afterEach(() => {
    listConversations.mockReset();
    getConversation.mockReset();
    streamChat.mockReset();
  });

  it("shows the empty state and loaded conversation history", async () => {
    const history: ConversationSummary[] = [
      {
        id: "c1",
        title: "Groceries spend",
        created_at: "2026-09-06T00:00:00Z",
        updated_at: "2026-09-06T00:00:00Z",
      },
    ];
    listConversations.mockResolvedValue(history);

    render(<FinanceChat />);

    expect(screen.getByText("Ask about your finances")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("Groceries spend")).toBeInTheDocument(),
    );
  });

  it("sends on Enter, renders optimistic messages, and refreshes history", async () => {
    listConversations.mockResolvedValue([]);
    streamChat.mockReturnValue(
      eventStream([
        { type: "status", status: "planning" },
        {
          type: "result",
          conversation_id: "c9",
          data: {
            answer: "You spent the most on Travel [analytics]",
            tools_used: ["financial_overview"],
            sources: [],
          },
        },
      ]),
    );

    render(<FinanceChat />);
    await waitFor(() => expect(listConversations).toHaveBeenCalledTimes(1));

    const input = typeQuestion("Where did I spend most?");
    fireEvent.keyDown(input, { key: "Enter" });

    expect(screen.getByText("Where did I spend most?")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/You spent the most on Travel/)).toBeInTheDocument(),
    );
    expect(streamChat).toHaveBeenCalledWith(
      "Where did I spend most?",
      "",
      expect.any(AbortSignal),
      undefined,
    );
    expect(screen.getByText("Verified SQL data")).toBeInTheDocument();
    await waitFor(() =>
      expect(listConversations.mock.calls.length).toBeGreaterThan(1),
    );
  });

  it("does not send on Shift+Enter", async () => {
    listConversations.mockResolvedValue([]);

    render(<FinanceChat />);
    await waitFor(() => expect(listConversations).toHaveBeenCalled());

    const input = typeQuestion("Draft line one");
    fireEvent.keyDown(input, { key: "Enter", shiftKey: true });

    expect(streamChat).not.toHaveBeenCalled();
  });

  it("surfaces a stream error event to the user", async () => {
    listConversations.mockResolvedValue([]);
    streamChat.mockReturnValue(
      eventStream([
        { type: "status", status: "planning" },
        {
          type: "error",
          message: "The AI service is temporarily unavailable.",
          code: "AI_UNAVAILABLE",
        },
      ]),
    );

    render(<FinanceChat />);
    await waitFor(() => expect(listConversations).toHaveBeenCalled());

    const input = typeQuestion("Any question");
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() =>
      expect(
        screen.getByText("The AI service is temporarily unavailable."),
      ).toBeInTheDocument(),
    );
  });

  it("loads an existing conversation when selected", async () => {
    const summary: ConversationSummary = {
      id: "c1",
      title: "Groceries spend",
      created_at: "2026-09-06T00:00:00Z",
      updated_at: "2026-09-06T00:00:00Z",
    };
    const detail: ConversationDetail = {
      ...summary,
      messages: [
        {
          id: "m1",
          role: "user",
          content: "How much on groceries?",
          metadata: {},
          created_at: "2026-09-06T00:00:00Z",
        },
      ],
    };
    listConversations.mockResolvedValue([summary]);
    getConversation.mockResolvedValue(detail);

    render(<FinanceChat />);
    await waitFor(() =>
      expect(screen.getByText("Groceries spend")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByText("Groceries spend"));

    await waitFor(() =>
      expect(screen.getByText("How much on groceries?")).toBeInTheDocument(),
    );
    expect(getConversation).toHaveBeenCalledWith("c1", "");
  });
});
