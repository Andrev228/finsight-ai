import { afterEach, describe, expect, it, vi } from "vitest";

import { streamChat } from "@/api/chat/chatApi";
import type { ChatStreamEvent } from "@/api/chat/types";

describe("streamChat", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses NDJSON events split across network chunks", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('{"type":"status","status":"plan'));
        controller.enqueue(
          encoder.encode(
            'ning"}\n{"type":"result","conversation_id":"conversation-1","data":{"answer":"ok","tools_used":[],"sources":[]}}\n',
          ),
        );
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(body, { status: 200 })),
    );

    const events: ChatStreamEvent[] = [];
    for await (const event of streamChat(
      "question",
      "",
      new AbortController().signal,
    )) {
      events.push(event);
    }

    expect(events).toEqual([
      { type: "status", status: "planning" },
      {
        type: "result",
        conversation_id: "conversation-1",
        data: { answer: "ok", tools_used: [], sources: [] },
      },
    ]);
  });

  it("rejects a response without a readable success body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
    );

    const consume = async () => {
      for await (const event of streamChat(
        "question",
        "",
        new AbortController().signal,
      )) {
        void event;
      }
    };

    await expect(consume()).rejects.toThrow(
      "Chat request failed with status 503",
    );
  });
});
