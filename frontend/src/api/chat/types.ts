export type ChatResult = {
  answer: string;
  tools_used: string[];
  sources: Array<{
    source: string;
    title: string;
    heading: string | null;
  }>;
};

export type ConversationSummary = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ConversationMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata: {
    tools_used?: string[];
    sources?: ChatResult["sources"];
    unsupported?: boolean;
  };
  created_at: string;
};

export type ConversationDetail = ConversationSummary & {
  messages: ConversationMessage[];
};

export type ChatStreamEvent =
  | { type: "status"; status: string }
  | { type: "result"; conversation_id: string; data: ChatResult }
  | { type: "error"; message: string; code: string };
