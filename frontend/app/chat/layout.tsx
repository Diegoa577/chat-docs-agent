"use client";

import { useCallback, useEffect, useMemo, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ConversationSidebar } from "@/components/ConversationSidebar";
import { useAppContext } from "@/context/AppContext";
import { ChatProvider, useChatContext } from "@/context/ChatContext";

function ChatShell({ children }: { children: ReactNode }) {
  const { conversations, isLoadingConversations, deleteConversation } = useChatContext();
  const { setSidebar, showSnackbar } = useAppContext();
  const pathname = usePathname();
  const router = useRouter();

  const handleDelete = useCallback(
    async (conversationId: string) => {
      try {
        await deleteConversation(conversationId);
        showSnackbar("Conversation deleted", "success");
        if (pathname === `/chat/${conversationId}`) {
          router.push("/chat");
        }
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to delete conversation";
        showSnackbar(message, "error");
      }
    },
    [deleteConversation, showSnackbar, pathname, router]
  );

  // Memoize the sidebar element so the AppContext slot is only re-registered
  // when its actual inputs change (not on every render of this shell).
  const sidebarNode = useMemo(
    () => (
      <ConversationSidebar
        conversations={conversations}
        isLoading={isLoadingConversations}
        onDelete={handleDelete}
      />
    ),
    [conversations, isLoadingConversations, handleDelete]
  );

  useEffect(() => {
    setSidebar(sidebarNode);
    return () => setSidebar(null);
  }, [sidebarNode, setSidebar]);

  return <>{children}</>;
}

export default function ChatLayout({ children }: { children: ReactNode }) {
  return (
    <ChatProvider>
      <ChatShell>{children}</ChatShell>
    </ChatProvider>
  );
}
