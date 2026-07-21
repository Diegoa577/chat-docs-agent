"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  getLLMProviders,
  type Conversation,
  type LLMProviderInfo,
  type Message,
} from "@/lib/api";
import { useConversations } from "@/lib/hooks/useConversations";

interface ChatContextValue {
  conversations: Conversation[];
  isLoadingConversations: boolean;
  refreshConversations: () => Promise<void>;
  deleteConversation: (conversationId: string) => Promise<void>;
  providers: LLMProviderInfo[];
  isLoadingProviders: boolean;
  providersError: string | null;
  selectedProvider: string;
  selectedModel: string;
  selectProvider: (providerId: string) => void;
  selectModel: (modelId: string) => void;
  getCachedMessages: (conversationId: string) => Message[] | undefined;
  cacheMessages: (conversationId: string, messages: Message[]) => void;
}

const ChatContext = createContext<ChatContextValue | undefined>(undefined);

export function ChatProvider({ children }: { children: ReactNode }) {
  const {
    conversations,
    isLoading: isLoadingConversations,
    refresh: refreshConversations,
    remove,
  } = useConversations();

  const messagesCacheRef = useRef<Map<string, Message[]>>(new Map());

  // Seed the per-conversation messages cache from the list endpoint, which
  // already returns full conversations including messages.
  useEffect(() => {
    for (const conversation of conversations) {
      messagesCacheRef.current.set(conversation.id, conversation.messages);
    }
  }, [conversations]);

  const getCachedMessages = useCallback((conversationId: string) => {
    return messagesCacheRef.current.get(conversationId);
  }, []);

  const cacheMessages = useCallback((conversationId: string, messages: Message[]) => {
    messagesCacheRef.current.set(conversationId, messages);
  }, []);

  const deleteConversation = useCallback(
    async (conversationId: string) => {
      await remove(conversationId);
      messagesCacheRef.current.delete(conversationId);
    },
    [remove]
  );

  const [providers, setProviders] = useState<LLMProviderInfo[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);
  const [providersError, setProvidersError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [selectedModel, setSelectedModel] = useState("");

  useEffect(() => {
    let cancelled = false;

    getLLMProviders()
      .then((data) => {
        if (cancelled) return;
        setProviders(data);
        if (data.length > 0) {
          setSelectedProvider(data[0].id);
          if (data[0].models.length > 0) {
            setSelectedModel(data[0].models[0].id);
          }
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setProvidersError(
          err instanceof Error ? err.message : "Failed to load providers"
        );
      })
      .finally(() => {
        if (!cancelled) setIsLoadingProviders(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectProvider = useCallback(
    (providerId: string) => {
      setSelectedProvider(providerId);
      const provider = providers.find((p) => p.id === providerId);
      setSelectedModel(provider?.models[0]?.id ?? "");
    },
    [providers]
  );

  const selectModel = useCallback((modelId: string) => {
    setSelectedModel(modelId);
  }, []);

  return (
    <ChatContext.Provider
      value={{
        conversations,
        isLoadingConversations,
        refreshConversations,
        deleteConversation,
        providers,
        isLoadingProviders,
        providersError,
        selectedProvider,
        selectedModel,
        selectProvider,
        selectModel,
        getCachedMessages,
        cacheMessages,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChatContext must be used within ChatProvider");
  }
  return context;
}
