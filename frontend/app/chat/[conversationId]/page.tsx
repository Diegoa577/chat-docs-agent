"use client";

import { notFound, useParams } from "next/navigation";
import Box from "@mui/material/Box";
import { ChatWindow } from "@/components/ChatWindow";
import { useChatContext } from "@/context/ChatContext";
import { useConversation } from "@/lib/hooks/useConversation";

export default function ConversationPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;

  const { messages, isLoading, isStreaming, error, errorStatus, sendMessage, stopStreaming } =
    useConversation(conversationId);
  const { refreshConversations } = useChatContext();

  // A conversation that does not exist renders the nearest not-found boundary.
  // notFound() must be called during render, not in an effect or callback.
  if (errorStatus === 404) {
    notFound();
  }

  const handleSend = async (
    question: string,
    strictMode: boolean,
    provider?: string,
    model?: string
  ) => {
    await sendMessage(question, strictMode, provider, model);
    await refreshConversations();
  };

  return (
    <Box sx={{ height: "calc(100vh - 140px)", minHeight: 500 }}>
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        isStreaming={isStreaming}
        error={error}
        onSend={handleSend}
        onStop={stopStreaming}
      />
    </Box>
  );
}
