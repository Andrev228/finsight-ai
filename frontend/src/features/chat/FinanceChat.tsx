"use client";

import AddOutlined from "@mui/icons-material/AddOutlined";
import ChatBubbleOutline from "@mui/icons-material/ChatBubbleOutline";
import SendRounded from "@mui/icons-material/SendRounded";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import type { FormEvent, KeyboardEvent } from "react";
import { useEffect, useRef, useState } from "react";

import {
  getConversation,
  listConversations,
  streamChat,
} from "@/api/chat/chatApi";
import type {
  ChatResult,
  ConversationMessage,
  ConversationSummary,
} from "@/api/chat/types";
import { useAuth } from "@/features/auth/AuthProvider";
import { CHAT_STATUS_LABELS } from "@/features/chat/constants";

function renderAnswer(answer: string) {
  const withoutCitations = answer.replace(/\[(?:analytics|\d+)\]/g, "").trim();
  return withoutCitations.split(/(\*\*.*?\*\*)/g).map((part, index) =>
    part.startsWith("**") && part.endsWith("**") ? (
      <Box component="strong" key={index}>
        {part.slice(2, -2)}
      </Box>
    ) : (
      part
    ),
  );
}

function optimisticMessage(
  role: "user" | "assistant",
  content: string,
  metadata: ConversationMessage["metadata"] = {},
): ConversationMessage {
  return {
    id: crypto.randomUUID(),
    role,
    content,
    metadata,
    created_at: new Date().toISOString(),
  };
}

/**
 * Renders a persistent ChatGPT-style conversation interface.
 */
export default function FinanceChat() {
  const { accessToken } = useAuth();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [conversationId, setConversationId] = useState<string>();
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<string>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(false);
  const activeRequest = useRef<AbortController | undefined>(undefined);
  const messagesEnd = useRef<HTMLDivElement>(null);

  const refreshConversations = async () => {
    const items = await listConversations(accessToken);
    setConversations(items);
  };

  useEffect(() => {
    refreshConversations().catch(() => {
      setError("Could not load conversation history.");
    });
    return () => activeRequest.current?.abort();
  }, [accessToken]);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const openConversation = async (id: string) => {
    if (loading) return;
    setError(undefined);
    try {
      const conversation = await getConversation(id, accessToken);
      setConversationId(conversation.id);
      setMessages(conversation.messages);
    } catch {
      setError("Could not load this conversation.");
    }
  };

  const newConversation = () => {
    if (loading) return;
    setConversationId(undefined);
    setMessages([]);
    setQuestion("");
    setError(undefined);
  };

  const sendMessage = async () => {
    const content = question.trim();
    if (!content || loading) return;

    setQuestion("");
    setLoading(true);
    setError(undefined);
    setStatus("planning");
    setMessages((current) => [
      ...current,
      optimisticMessage("user", content),
    ]);
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    let receivedTerminalEvent = false;

    try {
      for await (const event of streamChat(
        content,
        accessToken,
        controller.signal,
        conversationId,
      )) {
        if (event.type === "status") setStatus(event.status);
        if (event.type === "result") {
          const result: ChatResult = event.data;
          setConversationId(event.conversation_id);
          setMessages((current) => [
            ...current,
            optimisticMessage("assistant", result.answer, {
              tools_used: result.tools_used,
              sources: result.sources,
            }),
          ]);
          receivedTerminalEvent = true;
          await refreshConversations();
        }
        if (event.type === "error") {
          receivedTerminalEvent = true;
          throw new Error(event.message);
        }
      }
      if (!receivedTerminalEvent) {
        throw new Error("Chat stream ended unexpectedly");
      }
    } catch (chatError) {
      if (!controller.signal.aborted) {
        setError(
          chatError instanceof Error ? chatError.message : "Chat request failed",
        );
      }
    } finally {
      if (activeRequest.current === controller) activeRequest.current = undefined;
      await refreshConversations().catch(() => undefined);
      setLoading(false);
      setStatus(undefined);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void sendMessage();
  };

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void sendMessage();
    }
  };

  return (
    <Paper
      elevation={0}
      sx={{
        minHeight: { xs: "calc(100vh - 130px)", md: 680 },
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "280px minmax(0, 1fr)" },
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 3,
      }}
    >
      <Stack
        sx={{
          minWidth: 0,
          bgcolor: "background.default",
          borderRight: { md: "1px solid" },
          borderBottom: { xs: "1px solid", md: 0 },
          borderColor: "divider",
          maxHeight: { xs: 180, md: "none" },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Button
            fullWidth
            variant="outlined"
            startIcon={<AddOutlined />}
            onClick={newConversation}
          >
            New chat
          </Button>
        </Box>
        <Divider />
        <List dense sx={{ overflowY: "auto", p: 1 }}>
          {conversations.map((conversation) => (
            <ListItemButton
              key={conversation.id}
              selected={conversation.id === conversationId}
              onClick={() => openConversation(conversation.id)}
              sx={{ borderRadius: 2, mb: 0.5 }}
            >
              <ChatBubbleOutline sx={{ mr: 1.5, fontSize: 18 }} />
              <ListItemText
                primary={conversation.title}
                primaryTypographyProps={{
                  noWrap: true,
                  fontSize: 14,
                }}
              />
            </ListItemButton>
          ))}
          {!conversations.length && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ p: 2, textAlign: "center" }}
            >
              Your conversations will appear here.
            </Typography>
          )}
        </List>
      </Stack>

      <Stack sx={{ minWidth: 0, minHeight: 0 }}>
        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            px: { xs: 2, sm: 4, md: 7 },
            py: 3,
          }}
        >
          {!messages.length && (
            <Stack
              alignItems="center"
              justifyContent="center"
              textAlign="center"
              spacing={1.5}
              sx={{ minHeight: 380 }}
            >
              <ChatBubbleOutline color="primary" sx={{ fontSize: 38 }} />
              <Typography variant="h5" fontWeight={750}>
                Ask about your finances
              </Typography>
              <Typography color="text.secondary" maxWidth={480}>
                Try “What was my biggest expense category?” or “How much did I
                spend over the last three months?”
              </Typography>
            </Stack>
          )}

          <Stack spacing={3} maxWidth={760} mx="auto">
            {messages.map((message) => (
              <Stack
                key={message.id}
                alignItems={message.role === "user" ? "flex-end" : "flex-start"}
              >
                <Box
                  sx={{
                    maxWidth: message.role === "user" ? "80%" : "100%",
                    px: message.role === "user" ? 2 : 0,
                    py: message.role === "user" ? 1.25 : 0,
                    borderRadius: 3,
                    bgcolor:
                      message.role === "user"
                        ? "action.selected"
                        : "transparent",
                  }}
                >
                  <Typography sx={{ whiteSpace: "pre-wrap" }}>
                    {message.role === "assistant"
                      ? renderAnswer(message.content)
                      : message.content}
                  </Typography>
                  {message.role === "assistant" &&
                    message.content.includes("[analytics]") && (
                      <Chip
                        size="small"
                        color="success"
                        label="Verified SQL data"
                        sx={{ mt: 1.5 }}
                      />
                    )}
                </Box>
              </Stack>
            ))}
            {status && (
              <Stack direction="row" spacing={1.5} alignItems="center">
                <CircularProgress size={16} />
                <Typography
                  role="status"
                  aria-live="polite"
                  variant="body2"
                  color="text.secondary"
                >
                  {CHAT_STATUS_LABELS[status] ?? status}
                </Typography>
              </Stack>
            )}
            <div ref={messagesEnd} />
          </Stack>
        </Box>

        <Box
          component="form"
          onSubmit={submit}
          sx={{
            px: { xs: 2, sm: 4, md: 7 },
            pb: 3,
            pt: 1,
            bgcolor: "background.paper",
          }}
        >
          <Stack maxWidth={760} mx="auto" spacing={1}>
            {error && <Alert severity="error">{error}</Alert>}
            <Paper
              variant="outlined"
              sx={{
                display: "flex",
                alignItems: "flex-end",
                gap: 1,
                p: 1,
                borderRadius: 4,
              }}
            >
              <TextField
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={handleComposerKeyDown}
                placeholder="Message FinSight"
                multiline
                maxRows={6}
                inputProps={{ maxLength: 2000 }}
                disabled={loading}
                fullWidth
                variant="standard"
                InputProps={{ disableUnderline: true }}
                sx={{ px: 1, py: 0.5 }}
              />
              <Tooltip title="Send message">
                <span>
                  <IconButton
                    type="submit"
                    color="primary"
                    disabled={loading || !question.trim()}
                    aria-label="Send message"
                    sx={{
                      bgcolor: "primary.main",
                      color: "primary.contrastText",
                      "&:hover": { bgcolor: "primary.dark" },
                      "&.Mui-disabled": {
                        bgcolor: "action.disabledBackground",
                      },
                    }}
                  >
                    <SendRounded />
                  </IconButton>
                </span>
              </Tooltip>
            </Paper>
            <Typography
              variant="caption"
              color="text.secondary"
              textAlign="center"
            >
              Enter to send · Shift+Enter for a new line
            </Typography>
          </Stack>
        </Box>
      </Stack>
    </Paper>
  );
}
