import { ChatWindow } from "@/components/ChatWindow";
import { useChatContext } from "@/context/ChatContext";
import type { Message } from "@/lib/api";
import { fireEvent, makeMessage, makeProvider, render, screen } from "../test-utils";

// Mock the chat context (used by ChatInput) so tests do not depend on
// ChatProvider's async data loading. jest.mock needs a relative path because
// the "@/" alias is only rewritten by SWC in import statements.
jest.mock("../../context/ChatContext", () => ({
  useChatContext: jest.fn(),
}));

const mockUseChatContext = useChatContext as jest.Mock;

function buildContext(overrides: Record<string, unknown> = {}) {
  return {
    providers: [makeProvider()],
    isLoadingProviders: false,
    providersError: null,
    selectedProvider: "openai",
    selectedModel: "gpt-5.4-mini",
    selectProvider: jest.fn(),
    selectModel: jest.fn(),
    ...overrides,
  };
}

function getScrollContainer(): HTMLElement {
  return screen.getByTestId("chat-scroll-container");
}

/** jsdom does not compute layout, so scroll metrics are defined explicitly. */
function setScrollMetrics(
  el: HTMLElement,
  metrics: { scrollTop: number; scrollHeight: number; clientHeight: number }
) {
  Object.defineProperty(el, "scrollTop", {
    value: metrics.scrollTop,
    writable: true,
    configurable: true,
  });
  Object.defineProperty(el, "scrollHeight", {
    value: metrics.scrollHeight,
    configurable: true,
  });
  Object.defineProperty(el, "clientHeight", {
    value: metrics.clientHeight,
    configurable: true,
  });
}

function renderChatWindow(
  messages: Message[],
  props: Partial<Parameters<typeof ChatWindow>[0]> = {}
) {
  return <ChatWindow messages={messages} onSend={jest.fn()} {...props} />;
}

describe("ChatWindow auto-scroll", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseChatContext.mockReturnValue(buildContext());
  });

  it("sticks to the bottom while streaming when the user is at the bottom", () => {
    const messages = [
      makeMessage({ role: "user", content: "Hi" }),
      makeMessage({ role: "assistant", content: "Hel" }),
    ];
    const { rerender } = render(renderChatWindow(messages, { isStreaming: true }));
    const el = getScrollContainer();
    setScrollMetrics(el, { scrollTop: 1500, scrollHeight: 2000, clientHeight: 500 });

    // A new token arrives (same message count, longer content).
    rerender(
      renderChatWindow(
        [messages[0], makeMessage({ role: "assistant", content: "Hello, world" })],
        { isStreaming: true }
      )
    );

    expect(el.scrollTop).toBe(2000);
  });

  it("does not force-scroll new tokens when the user scrolled up", () => {
    const messages = [
      makeMessage({ role: "user", content: "Hi" }),
      makeMessage({ role: "assistant", content: "Hel" }),
    ];
    const { rerender } = render(renderChatWindow(messages, { isStreaming: true }));
    const el = getScrollContainer();
    setScrollMetrics(el, { scrollTop: 100, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);

    rerender(
      renderChatWindow(
        [messages[0], makeMessage({ role: "assistant", content: "Hello, world" })],
        { isStreaming: true }
      )
    );

    expect(el.scrollTop).toBe(100);
  });

  it("resumes auto-scroll when the user scrolls back near the bottom", () => {
    const messages = [
      makeMessage({ role: "user", content: "Hi" }),
      makeMessage({ role: "assistant", content: "Hel" }),
    ];
    const { rerender } = render(renderChatWindow(messages, { isStreaming: true }));
    const el = getScrollContainer();
    setScrollMetrics(el, { scrollTop: 100, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);

    // User scrolls back down to within the near-bottom threshold.
    setScrollMetrics(el, { scrollTop: 1950, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);

    rerender(
      renderChatWindow(
        [messages[0], makeMessage({ role: "assistant", content: "Hello, world" })],
        { isStreaming: true }
      )
    );

    expect(el.scrollTop).toBe(2000);
  });

  it("scrolls to the bottom when a new message arrives even if scrolled up", () => {
    const messages = [makeMessage({ role: "assistant", content: "Previous answer" })];
    const { rerender } = render(renderChatWindow(messages, { isStreaming: true }));
    const el = getScrollContainer();
    setScrollMetrics(el, { scrollTop: 100, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);

    // A new turn starts: the user sends another question.
    rerender(
      renderChatWindow(
        [...messages, makeMessage({ role: "user", content: "Another question" })],
        { isStreaming: true }
      )
    );

    expect(el.scrollTop).toBe(2000);
  });

  it("shows a jump-to-bottom button while streaming when scrolled up and hides it on click", () => {
    const messages = [
      makeMessage({ role: "user", content: "Hi" }),
      makeMessage({ role: "assistant", content: "Hel" }),
    ];
    render(renderChatWindow(messages, { isStreaming: true }));
    const el = getScrollContainer();

    // At the bottom: no button.
    expect(screen.queryByRole("button", { name: "Scroll to bottom" })).toBeNull();

    // Scrolled up while streaming: button appears.
    setScrollMetrics(el, { scrollTop: 100, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);
    const button = screen.getByRole("button", { name: "Scroll to bottom" });

    fireEvent.click(button);

    expect(el.scrollTop).toBe(2000);
    expect(screen.queryByRole("button", { name: "Scroll to bottom" })).toBeNull();
  });

  it("does not show the jump-to-bottom button when not streaming", () => {
    const messages = [makeMessage({ role: "assistant", content: "Done" })];
    render(renderChatWindow(messages, { isStreaming: false }));
    const el = getScrollContainer();
    setScrollMetrics(el, { scrollTop: 100, scrollHeight: 2000, clientHeight: 500 });
    fireEvent.scroll(el);

    expect(screen.queryByRole("button", { name: "Scroll to bottom" })).toBeNull();
  });
});
