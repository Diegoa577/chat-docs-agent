"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Fab from "@mui/material/Fab";
import Typography from "@mui/material/Typography";
import Paper from "@mui/material/Paper";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import type { Message } from "@/lib/api";

/** Distance from the bottom (px) within which the view is considered "at the bottom". */
const NEAR_BOTTOM_THRESHOLD_PX = 100;

interface ChatWindowProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  error?: string | null;
  onSend: (
    question: string,
    strictMode: boolean,
    provider?: string,
    model?: string
  ) => void;
  onStop?: () => void;
}

export function ChatWindow({
  messages,
  isLoading,
  isStreaming,
  error,
  onSend,
  onStop,
}: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  /** Whether the view should keep following new content (sticky bottom). */
  const autoScrollRef = useRef(true);
  const prevMessageCountRef = useRef(0);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  // While streaming, tokens arrive constantly; only follow them when the user
  // is already near the bottom. Scrolling up pauses auto-scroll so the user
  // can read without being yanked back down.
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceToBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    autoScrollRef.current = distanceToBottom < NEAR_BOTTOM_THRESHOLD_PX;
    setShowJumpToBottom(!autoScrollRef.current);
  }, []);

  useEffect(() => {
    // A new turn (e.g. the user just sent a message) always pulls the view
    // back to the bottom, even if the user had scrolled up.
    if (messages.length !== prevMessageCountRef.current) {
      autoScrollRef.current = true;
    }
    prevMessageCountRef.current = messages.length;

    if (autoScrollRef.current) {
      scrollToBottom();
      setShowJumpToBottom(false);
    } else {
      setShowJumpToBottom(true);
    }
  }, [messages, scrollToBottom]);

  const jumpToBottom = useCallback(() => {
    autoScrollRef.current = true;
    scrollToBottom();
    setShowJumpToBottom(false);
  }, [scrollToBottom]);

  return (
    <Box sx={{ display: "flex", flexDirection: "column", height: "100%", gap: 2 }}>
      <Box
        sx={{
          position: "relative",
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <Paper
          ref={scrollRef}
          onScroll={handleScroll}
          data-testid="chat-scroll-container"
          elevation={0}
          sx={{
            flex: 1,
            overflow: "auto",
            p: 2,
            borderRadius: 3,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          {messages.length === 0 && !isLoading && (
            <Box sx={{ textAlign: "center", mt: 8, px: 2 }}>
              <Typography variant="h5" fontWeight={700} color="text.primary" gutterBottom>
                How can I help with your documents?
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                Upload clinical or regulatory documents and ask questions about protocols, SOPs, or submissions.
              </Typography>
            </Box>
          )}

          {messages.map((message, index) => (
            <MessageBubble
              key={(message.metadata?.id as string | undefined) ?? `fallback-${index}`}
              message={message}
            />
          ))}

          {isLoading && messages.length === 0 && (
            <Typography color="text.secondary" textAlign="center" mt={4}>
              Loading conversation...
            </Typography>
          )}
        </Paper>

        {isStreaming && showJumpToBottom && (
          <Fab
            size="small"
            color="primary"
            aria-label="Scroll to bottom"
            onClick={jumpToBottom}
            sx={{ position: "absolute", bottom: 16, right: 24, zIndex: 1 }}
          >
            <KeyboardArrowDownIcon />
          </Fab>
        )}
      </Box>

      {error && (
        <Alert severity="error" role="alert">
          {error}
        </Alert>
      )}

      <ChatInput
        onSend={onSend}
        onStop={onStop}
        isStreaming={isStreaming}
        disabled={isLoading}
        showSuggestions={messages.length === 0 && !isLoading}
      />
    </Box>
  );
}
