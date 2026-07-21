// useParams/notFound live in the manual mock (__mocks__/next/navigation.ts).
import { notFound, useParams } from "next/navigation";
import ConversationPage from "@/app/chat/[conversationId]/page";
import { useConversation } from "@/lib/hooks/useConversation";
import { act, render, screen, waitFor } from "../test-utils";

const mockRefreshConversations = jest.fn().mockResolvedValue(undefined);
const mockSendMessage = jest.fn().mockResolvedValue(undefined);

// Capture the props the page passes to ChatWindow so tests can drive onSend.
let mockChatWindowProps: {
  onSend: (q: string, strict: boolean, provider?: string, model?: string) => void;
  isStreaming?: boolean;
} | null = null;

// NOTE: jest.mock specifiers must be relative paths — `@/…` aliases are only
// rewritten by the SWC transform for import statements, not for jest.mock.
jest.mock("../../lib/hooks/useConversation", () => ({
  useConversation: jest.fn(),
}));

jest.mock("../../context/ChatContext", () => ({
  useChatContext: () => ({
    refreshConversations: mockRefreshConversations,
  }),
}));

jest.mock("../../components/ChatWindow", () => ({
  ChatWindow: (props: typeof mockChatWindowProps) => {
    mockChatWindowProps = props;
    return <div data-testid="chat-window" />;
  },
}));

const mockUseConversation = useConversation as jest.Mock;
const mockUseParams = useParams as jest.Mock;
const mockNotFound = notFound as unknown as jest.Mock;

function hookState(overrides: Record<string, unknown> = {}) {
  return {
    messages: [],
    isLoading: false,
    isStreaming: false,
    error: null,
    errorStatus: null,
    conversationId: "conv-1" as string | undefined,
    sendMessage: mockSendMessage,
    stopStreaming: jest.fn(),
    ...overrides,
  };
}

describe("ConversationPage (app/chat/[conversationId]/page.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockChatWindowProps = null;
    mockUseParams.mockReturnValue({ conversationId: "conv-1" });
    mockUseConversation.mockReturnValue(hookState());
  });

  it("renders the ChatWindow", () => {
    render(<ConversationPage />);

    expect(screen.getByTestId("chat-window")).toBeInTheDocument();
    expect(mockNotFound).not.toHaveBeenCalled();
  });

  it("sends the message and refreshes the conversation list", async () => {
    render(<ConversationPage />);

    await act(async () => {
      await mockChatWindowProps!.onSend("What is the dosage?", true, "openai", "gpt-5.4-mini");
    });

    expect(mockSendMessage).toHaveBeenCalledWith(
      "What is the dosage?",
      true,
      "openai",
      "gpt-5.4-mini"
    );
    await waitFor(() => expect(mockRefreshConversations).toHaveBeenCalledTimes(1));
  });

  it("calls notFound() when the conversation does not exist (404)", () => {
    mockUseConversation.mockReturnValue(
      hookState({ error: "Conversation not found", errorStatus: 404 })
    );

    render(<ConversationPage />);

    expect(mockNotFound).toHaveBeenCalledTimes(1);
  });

  it("does not call notFound() for non-404 errors", () => {
    mockUseConversation.mockReturnValue(
      hookState({ error: "Server exploded", errorStatus: 500 })
    );

    render(<ConversationPage />);

    expect(mockNotFound).not.toHaveBeenCalled();
    expect(screen.getByTestId("chat-window")).toBeInTheDocument();
  });
});
