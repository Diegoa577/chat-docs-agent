import type { ReactNode } from "react";
import {
  act,
  makeCitation,
  makeConversation,
  makeMessage,
  makeProvider,
  renderHook,
  waitFor,
} from "../test-utils";
import { ChatProvider, useChatContext } from "@/context/ChatContext";
import {
  applyStreamEvent,
  useConversation,
} from "@/lib/hooks/useConversation";
import {
  getConversation,
  getLLMProviders,
  listConversations,
  streamChat,
  type ChatStreamEvent,
} from "@/lib/api";

// NOTE: the "@/" path alias is only rewritten by SWC in import statements,
// so jest.mock must use a relative path (it resolves to the same module).
jest.mock("../../lib/api");

const getConversationMock = getConversation as jest.Mock;
const getLLMProvidersMock = getLLMProviders as jest.Mock;
const listConversationsMock = listConversations as jest.Mock;
const streamChatMock = streamChat as jest.Mock;

function wrapper({ children }: { children: ReactNode }) {
  return <ChatProvider>{children}</ChatProvider>;
}

interface CapturedStream {
  onEvent: (event: ChatStreamEvent) => void;
  signal?: AbortSignal;
  resolve: () => void;
  reject: (err: unknown) => void;
}

/**
 * Mocks streamChat with a manually-controlled pending promise. Returns a
 * getter for the captured (onEvent, signal, resolve, reject) tuple, valid
 * after sendMessage has been called.
 */
function mockPendingStream(): () => CapturedStream {
  let captured!: CapturedStream;
  streamChatMock.mockImplementation(
    (
      _params: unknown,
      onEvent: (event: ChatStreamEvent) => void,
      signal?: AbortSignal
    ) =>
      new Promise<void>((resolve, reject) => {
        captured = { onEvent, signal, resolve, reject };
      })
  );
  return () => captured;
}

beforeEach(() => {
  jest.clearAllMocks();
  getLLMProvidersMock.mockResolvedValue([makeProvider()]);
  listConversationsMock.mockResolvedValue([]);
  getConversationMock.mockResolvedValue(makeConversation());
});

describe("useConversation cache behaviour", () => {
  function useCachedConversation(id?: string) {
    const ctx = useChatContext();
    const conversation = useConversation(id);
    return { ctx, conversation };
  }

  it("renders from the provider-seeded cache without fetching on a cache hit", async () => {
    const cachedMessages = [makeMessage({ role: "assistant", content: "from cache" })];
    listConversationsMock.mockResolvedValue([
      makeConversation({ id: "conv-1", messages: cachedMessages }),
    ]);

    const { result, rerender } = renderHook(
      ({ id }: { id?: string }) => useCachedConversation(id),
      { wrapper, initialProps: { id: undefined as string | undefined } }
    );

    // Wait until ChatProvider has seeded the cache from the conversations list.
    await waitFor(() =>
      expect(result.current.ctx.getCachedMessages("conv-1")).toEqual(cachedMessages)
    );

    // Mounting the hook on a cached conversation renders instantly, no fetch.
    rerender({ id: "conv-1" });

    // The hook stamps a client-generated id on each message (stable React
    // keys); the rest of the message is unchanged.
    expect(result.current.conversation.messages).toMatchObject(cachedMessages);
    expect(
      result.current.conversation.messages[0].metadata?.id
    ).toMatch(/^msg-/);
    expect(result.current.conversation.isLoading).toBe(false);
    expect(result.current.conversation.error).toBeNull();
    expect(getConversationMock).not.toHaveBeenCalled();
  });

  it("fetches the conversation on a cache miss and caches it", async () => {
    const conversation = makeConversation({
      id: "conv-9",
      messages: [makeMessage({ content: "fetched" })],
    });
    getConversationMock.mockResolvedValue(conversation);

    function useMissProbe(id?: string) {
      const ctx = useChatContext();
      const conv = useConversation(id);
      return { ctx, conv };
    }

    const { result } = renderHook(() => useMissProbe("conv-9"), { wrapper });

    await waitFor(() => expect(result.current.conv.messages).toHaveLength(1));
    expect(getConversationMock).toHaveBeenCalledTimes(1);
    expect(getConversationMock).toHaveBeenCalledWith("conv-9");
    expect(result.current.conv.messages[0].content).toBe("fetched");
    expect(result.current.conv.isLoading).toBe(false);
    expect(result.current.conv.error).toBeNull();

    // The fetched messages were written through to the provider cache
    // (with the client-generated ids stamped by the hook).
    expect(result.current.ctx.getCachedMessages("conv-9")).toMatchObject(
      conversation.messages
    );
    expect(
      result.current.ctx.getCachedMessages("conv-9")?.[0].metadata?.id
    ).toMatch(/^msg-/);
  });

  it("sets the error state when the cache-miss fetch rejects", async () => {
    getConversationMock.mockRejectedValue(new Error("not found"));

    const { result } = renderHook(() => useConversation("conv-x"), { wrapper });

    await waitFor(() => expect(result.current.error).toBe("not found"));
    expect(result.current.messages).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });
});

describe("useConversation sendMessage", () => {
  it("runs the full streaming cycle: optimistic messages, metadata, chunks, done", async () => {
    const getCaptured = mockPendingStream();
    const { result } = renderHook(() => useConversation(), { wrapper });

    let sendPromise!: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage(
        "What is the dosage?",
        true,
        "openai",
        "gpt-5.4-mini"
      );
    });

    // Optimistic user + assistant placeholder appended before the stream resolves.
    expect(result.current.isStreaming).toBe(true);
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({
      role: "user",
      content: "What is the dosage?",
    });
    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "",
      metadata: { isStreaming: true },
    });
    expect(streamChatMock).toHaveBeenCalledWith(
      {
        question: "What is the dosage?",
        conversationId: undefined,
        strictMode: true,
        provider: "openai",
        model: "gpt-5.4-mini",
      },
      expect.any(Function),
      expect.any(AbortSignal)
    );

    const stream = getCaptured();
    const citation = makeCitation();

    act(() => {
      stream.onEvent({
        type: "metadata",
        conversation_id: "conv-new",
        intent: "search",
        confidence: "high",
        model: "gpt-5.4-mini",
        citations: [citation],
        strict_mode_applied: true,
      });
    });
    expect(result.current.messages[1].metadata).toMatchObject({
      intent: "search",
      confidence: "high",
      model: "gpt-5.4-mini",
      strict_mode_applied: true,
      isStreaming: true,
    });
    expect(result.current.messages[1].metadata?.citations).toEqual([citation]);
    expect(result.current.conversationId).toBe("conv-new");

    act(() => {
      stream.onEvent({ type: "chunk", conversation_id: "conv-new", content: "Hello" });
    });
    act(() => {
      stream.onEvent({ type: "chunk", conversation_id: "conv-new", content: " world" });
    });
    expect(result.current.messages[1].content).toBe("Hello world");
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      stream.onEvent({ type: "done", conversation_id: "conv-new" });
    });
    await act(async () => {
      stream.resolve();
      await sendPromise;
    });

    expect(result.current.isStreaming).toBe(false);
    expect(result.current.conversationId).toBe("conv-new");
    expect(result.current.messages[1].content).toBe("Hello world");
    expect(result.current.messages[1].metadata).toMatchObject({ isStreaming: false });
    expect(result.current.error).toBeNull();
  });

  it("renders an error event into the assistant message", async () => {
    const getCaptured = mockPendingStream();
    const { result } = renderHook(() => useConversation(), { wrapper });

    let sendPromise!: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage("Hi", false);
    });

    const stream = getCaptured();
    act(() => {
      stream.onEvent({ type: "error", detail: "boom" });
    });
    await act(async () => {
      stream.resolve();
      await sendPromise;
    });

    const assistant = result.current.messages[1];
    expect(assistant.content).toBe("Error: boom");
    expect(assistant.metadata).toMatchObject({ isStreaming: false, error: true });
    expect(result.current.isStreaming).toBe(false);
  });

  it("appends an error message to the last assistant message when streamChat rejects", async () => {
    const getCaptured = mockPendingStream();
    const { result } = renderHook(() => useConversation(), { wrapper });

    let sendPromise!: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage("Hi", false);
    });

    const stream = getCaptured();
    await act(async () => {
      stream.reject(new Error("aborted"));
      await sendPromise;
    });

    expect(result.current.error).toBe("aborted");
    const assistant = result.current.messages[1];
    expect(assistant.content).toBe("Error: aborted");
    expect(assistant.metadata).toMatchObject({ isStreaming: false, error: true });
    expect(result.current.isStreaming).toBe(false);
  });

  it("stopStreaming aborts the signal and finalizes the partial answer cleanly", async () => {
    const getCaptured = mockPendingStream();
    const { result } = renderHook(() => useConversation(), { wrapper });

    let sendPromise!: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage("Hi", false);
    });

    const stream = getCaptured();
    expect(stream.signal).toBeInstanceOf(AbortSignal);
    expect(stream.signal?.aborted).toBe(false);

    act(() => {
      stream.onEvent({ type: "chunk", conversation_id: "conv-1", content: "Partial" });
    });
    expect(result.current.isStreaming).toBe(true);

    act(() => {
      result.current.stopStreaming();
    });

    // Deterministic cleanup: the state resets without waiting for the
    // stream promise to settle, and the partial answer is preserved.
    expect(stream.signal?.aborted).toBe(true);
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "Partial",
      metadata: { isStreaming: false },
    });
    expect(result.current.error).toBeNull();

    // The browser fetch rejects with AbortError after abort(); the hook
    // must not surface it as an error.
    await act(async () => {
      stream.reject(new DOMException("This operation was aborted", "AbortError"));
      await sendPromise;
    });

    expect(result.current.error).toBeNull();
    expect(result.current.messages[1].content).toBe("Partial");
    expect(result.current.messages[1].metadata).toMatchObject({
      isStreaming: false,
    });
  });

  it("treats an AbortError rejection as a clean stop (no error state)", async () => {
    const getCaptured = mockPendingStream();
    const { result } = renderHook(() => useConversation(), { wrapper });

    let sendPromise!: Promise<void>;
    act(() => {
      sendPromise = result.current.sendMessage("Hi", false);
    });

    const stream = getCaptured();
    await act(async () => {
      stream.reject(new DOMException("The operation was aborted", "AbortError"));
      await sendPromise;
    });

    expect(result.current.error).toBeNull();
    const assistant = result.current.messages[1];
    expect(assistant.content).toBe("");
    expect(assistant.metadata).toMatchObject({ isStreaming: false });
    expect(result.current.isStreaming).toBe(false);
  });
});

describe("applyStreamEvent", () => {
  it("returns the list unchanged when it is empty", () => {
    const result = applyStreamEvent([], {
      type: "chunk",
      conversation_id: "conv-1",
      content: "x",
    });
    expect(result).toEqual([]);
  });

  it("returns the list unchanged when the last message is not from the assistant", () => {
    const messages = [makeMessage({ role: "user", content: "Hi" })];
    const result = applyStreamEvent(messages, {
      type: "chunk",
      conversation_id: "conv-1",
      content: "x",
    });
    expect(result).toBe(messages);
  });

  it("does not mutate the input list when applying an event", () => {
    const messages = [
      makeMessage({ role: "user", content: "Hi" }),
      makeMessage({ role: "assistant", content: "", metadata: { isStreaming: true } }),
    ];
    const result = applyStreamEvent(messages, {
      type: "chunk",
      conversation_id: "conv-1",
      content: "Hello",
    });
    expect(result[1].content).toBe("Hello");
    expect(messages[1].content).toBe("");
  });
});
