"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Box from "@mui/material/Box";
import { ChatWindow } from "@/components/ChatWindow";
import { useChatContext } from "@/context/ChatContext";
import { useConversation } from "@/lib/hooks/useConversation";

export default function NewChatPage() {
  const router = useRouter();
  const { messages, isStreaming, error, sendMessage, stopStreaming, conversationId } =
    useConversation();
  const { refreshConversations } = useChatContext();

  useEffect(() => {
    // Wait until the stream finishes before navigating: replacing the route
    // unmounts this page, which aborts the in-flight stream, and the new page
    // refetches the conversation from the API.
    if (conversationId && !isStreaming) {
      router.replace(`/chat/${conversationId}`);
    }
  }, [conversationId, isStreaming, router]);

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
        isStreaming={isStreaming}
        error={error}
        onSend={handleSend}
        onStop={stopStreaming}
      />
    </Box>
  );
}
