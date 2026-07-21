// mockReplace lives in the manual mock (__mocks__/next/navigation.ts); its
// exports are made visible to TypeScript via __tests__/next-navigation.d.ts.
import { mockReplace } from "next/navigation";
import NewChatPage from "@/app/chat/page";
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

function hookState(overrides: Record<string, unknown> = {}) {
  return {
    messages: [],
    isLoading: false,
    isStreaming: false,
    error: null,
    conversationId: undefined as string | undefined,
    sendMessage: mockSendMessage,
    stopStreaming: jest.fn(),
    ...overrides,
  };
}

describe("NewChatPage (app/chat/page.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockChatWindowProps = null;
    mockUseConversation.mockReturnValue(hookState());
  });

  it("renders the ChatWindow", () => {
    render(<NewChatPage />);

    expect(screen.getByTestId("chat-window")).toBeInTheDocument();
  });

  it("does not navigate away before a conversation exists", () => {
    render(<NewChatPage />);

    expect(mockReplace).not.toHaveBeenCalled();
  });

  it("defers router.replace until streaming completes", () => {
    // While streaming, the conversation id may already be known, but the
    // page must NOT replace the route (that would unmount and abort the
    // in-flight stream).
    mockUseConversation.mockReturnValue(
      hookState({ conversationId: "conv-1", isStreaming: true })
    );
    const { rerender } = render(<NewChatPage />);

    expect(mockReplace).not.toHaveBeenCalled();

    // Once the stream is done, the page navigates to the conversation URL.
    mockUseConversation.mockReturnValue(
      hookState({ conversationId: "conv-1", isStreaming: false })
    );
    rerender(<NewChatPage />);

    expect(mockReplace).toHaveBeenCalledTimes(1);
    expect(mockReplace).toHaveBeenCalledWith("/chat/conv-1");
  });

  it("sends the message and refreshes the conversation list", async () => {
    render(<NewChatPage />);

    await act(async () => {
      await mockChatWindowProps!.onSend("What is the primary endpoint?", false);
    });

    expect(mockSendMessage).toHaveBeenCalledWith(
      "What is the primary endpoint?",
      false,
      undefined,
      undefined
    );
    await waitFor(() => expect(mockRefreshConversations).toHaveBeenCalledTimes(1));
  });
});
