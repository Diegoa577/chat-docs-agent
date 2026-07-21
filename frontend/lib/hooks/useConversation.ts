"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ApiError,
  getConversation,
  streamChat,
  type ChatStreamEvent,
  type Message,
} from "@/lib/api";
import { useChatContext } from "@/context/ChatContext";

export interface UseConversationReturn {
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  error: string | null;
  /** HTTP status of the last load failure (e.g. 404), or null. */
  errorStatus: number | null;
  conversationId: string | undefined;
  sendMessage: (
    question: string,
    strictMode: boolean,
    provider?: string,
    model?: string
  ) => Promise<void>;
  stopStreaming: () => void;
}

/**
 * Pure reducer for chat stream events: applies `event` to the message list
 * (always targeting the trailing assistant message) and returns the next
 * list. Kept pure so it can run outside React state updaters — updaters must
 * not contain side effects because StrictMode invokes them twice.
 */
export function applyStreamEvent(
  messages: Message[],
  event: ChatStreamEvent
): Message[] {
  const lastIndex = messages.length - 1;
  if (lastIndex < 0) return messages;
  const last = messages[lastIndex];
  if (last.role !== "assistant") return messages;

  if (event.type === "metadata") {
    const next = [...messages];
    next[lastIndex] = {
      ...last,
      metadata: {
        ...last.metadata,
        intent: event.intent,
        confidence: event.confidence,
        model: event.model,
        citations: event.citations,
        strict_mode_applied: event.strict_mode_applied,
        isStreaming: true,
      },
    };
    return next;
  }

  if (event.type === "chunk") {
    const next = [...messages];
    next[lastIndex] = {
      ...last,
      content: last.content + event.content,
    };
    return next;
  }

  if (event.type === "done") {
    const next = [...messages];
    next[lastIndex] = {
      ...last,
      metadata: { ...last.metadata, isStreaming: false },
    };
    return next;
  }

  if (event.type === "error") {
    const next = [...messages];
    next[lastIndex] = {
      ...last,
      content: `Error: ${event.detail}`,
      metadata: { ...last.metadata, isStreaming: false, error: true },
    };
    return next;
  }

  return messages;
}

/**
 * Module-level counter for client-generated message ids. Ids give the message
 * list stable React keys (append-only today, but safe against future
 * insertions/removals). Stamping happens at the useConversation boundary, so
 * ids survive streaming updates and the ChatContext cache round-trip.
 */
let messageIdCounter = 0;

/** Stamps `metadata.id` on messages that lack one; leaves the rest untouched. */
export function ensureMessageIds(messages: Message[]): Message[] {
  return messages.map((message) => {
    if (message.metadata?.id) return message;
    messageIdCounter += 1;
    return {
      ...message,
      metadata: { ...message.metadata, id: `msg-${messageIdCounter}` },
    };
  });
}

export function useConversation(conversationId?: string): UseConversationReturn {
  const { getCachedMessages, cacheMessages } = useChatContext();
  const [messages, setMessages] = useState<Message[]>(() =>
    conversationId ? ensureMessageIds(getCachedMessages(conversationId) ?? []) : []
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | undefined>(
    conversationId
  );
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }

    // Instant render from the cache seeded by the conversations list;
    // only fetch when the conversation is not cached yet.
    const cached = getCachedMessages(conversationId);
    if (cached) {
      setMessages(ensureMessageIds(cached));
      setError(null);
      setErrorStatus(null);
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    setError(null);
    setErrorStatus(null);

    getConversation(conversationId)
      .then((conversation) => {
        if (!cancelled) {
          const loaded = ensureMessageIds(conversation.messages);
          setMessages(loaded);
          cacheMessages(conversationId, loaded);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Failed to load conversation";
          setError(message);
          setErrorStatus(err instanceof ApiError ? err.status ?? null : null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId, getCachedMessages, cacheMessages]);

  /** Marks the trailing assistant message as no longer streaming, keeping
   *  whatever partial content it has. Pure functional update — no-op when
   *  there is nothing to finalize. */
  const finalizeStream = useCallback(() => {
    setMessages((prev) => {
      const lastIndex = prev.length - 1;
      if (lastIndex < 0) return prev;
      const last = prev[lastIndex];
      if (last.role !== "assistant" || last.metadata?.isStreaming !== true) {
        return prev;
      }
      const next = [...prev];
      next[lastIndex] = {
        ...last,
        metadata: { ...last.metadata, isStreaming: false },
      };
      return next;
    });
  }, []);

  const sendMessage = useCallback(
    async (question: string, strictMode: boolean, provider?: string, model?: string) => {
      setError(null);
      const userMessage: Message = { role: "user", content: question, metadata: {} };
      const assistantMessage: Message = {
        role: "assistant",
        content: "",
        metadata: { isStreaming: true },
      };

      // Local mirror of the message list for this stream. While a stream is
      // active this closure is the only writer of `messages`, so computing
      // the next state outside the setState updater is safe — and it keeps
      // side effects (the cacheMessages write-through) out of updaters,
      // which React StrictMode would otherwise invoke twice.
      let streamed: Message[] = [];
      setMessages((prev) => {
        streamed = ensureMessageIds([...prev, userMessage, assistantMessage]);
        return streamed;
      });
      setIsStreaming(true);

      abortControllerRef.current = new AbortController();

      try {
        await streamChat(
          { question, conversationId, strictMode, provider, model },
          (event) => {
            if (
              (event.type === "metadata" ||
                event.type === "chunk" ||
                event.type === "done") &&
              event.conversation_id
            ) {
              setActiveConversationId((prev) => prev ?? event.conversation_id);
            }

            streamed = applyStreamEvent(streamed, event);
            setMessages(streamed);

            if (event.type === "done") {
              setIsStreaming(false);
              abortControllerRef.current = null;
              // Idempotent write-through so the conversation page renders
              // instantly (no refetch) when the URL switches to /chat/[id].
              if (event.conversation_id) {
                cacheMessages(event.conversation_id, streamed);
              }
            }

            if (event.type === "error") {
              setIsStreaming(false);
              abortControllerRef.current = null;
            }
          },
          abortControllerRef.current.signal
        );
      } catch (err) {
        const wasAborted =
          abortControllerRef.current === null ||
          (err instanceof Error && err.name === "AbortError");

        if (wasAborted) {
          // User-initiated stop: a stop is not an error — keep the partial
          // content and leave the error state untouched. finalizeStream is
          // idempotent: stopStreaming() may have already run it.
          finalizeStream();
          setIsStreaming(false);
          return;
        }

        const message = err instanceof Error ? err.message : "Failed to send message";
        setError(message);
        setMessages((prev) => {
          const lastIndex = prev.length - 1;
          if (lastIndex < 0) return prev;
          const last = prev[lastIndex];
          if (last.role !== "assistant") return prev;
          const next = [...prev];
          next[lastIndex] = {
            ...last,
            content: last.content || `Error: ${message}`,
            metadata: { ...last.metadata, isStreaming: false, error: true },
          };
          return next;
        });
        setIsStreaming(false);
      }
    },
    [conversationId, cacheMessages, finalizeStream]
  );

  const stopStreaming = useCallback(() => {
    if (!abortControllerRef.current) return;
    abortControllerRef.current.abort();
    abortControllerRef.current = null;
    // Deterministic cleanup: do not rely on the fetch promise rejecting to
    // reset the state. The partial answer is preserved, no error is shown.
    finalizeStream();
    setIsStreaming(false);
  }, [finalizeStream]);

  useEffect(() => {
    return () => {
      stopStreaming();
    };
  }, [stopStreaming]);

  return {
    messages,
    isLoading,
    isStreaming,
    error,
    errorStatus,
    conversationId: activeConversationId,
    sendMessage,
    stopStreaming,
  };
}
