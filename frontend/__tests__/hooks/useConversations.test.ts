import { act, makeConversation, renderHook, waitFor } from "../test-utils";
import { useConversations } from "@/lib/hooks/useConversations";
import { deleteConversation, listConversations } from "@/lib/api";

// NOTE: the "@/" path alias is only rewritten by SWC in import statements,
// so jest.mock must use a relative path (it resolves to the same module).
jest.mock("../../lib/api");

const listConversationsMock = listConversations as jest.Mock;
const deleteConversationMock = deleteConversation as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
});

describe("useConversations", () => {
  it("fetches conversations on mount and toggles isLoading true -> false", async () => {
    const conversations = [
      makeConversation({ id: "conv-1" }),
      makeConversation({ id: "conv-2" }),
    ];
    listConversationsMock.mockResolvedValue(conversations);

    const { result } = renderHook(() => useConversations());

    // The mount effect runs synchronously inside act(), so the fetch is in flight.
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.conversations).toHaveLength(2));
    expect(result.current.conversations.map((c) => c.id)).toEqual(["conv-1", "conv-2"]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(listConversationsMock).toHaveBeenCalledTimes(1);
  });

  it("sets the error state when the initial fetch rejects", async () => {
    listConversationsMock.mockRejectedValue(new Error("server exploded"));

    const { result } = renderHook(() => useConversations());

    await waitFor(() => expect(result.current.error).toBe("server exploded"));
    expect(result.current.conversations).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it("refresh refetches the conversation list", async () => {
    listConversationsMock.mockResolvedValue([makeConversation({ id: "conv-1" })]);

    const { result } = renderHook(() => useConversations());
    await waitFor(() => expect(result.current.conversations).toHaveLength(1));

    listConversationsMock.mockResolvedValue([
      makeConversation({ id: "conv-1" }),
      makeConversation({ id: "conv-2" }),
    ]);
    await act(async () => {
      await result.current.refresh();
    });

    expect(listConversationsMock).toHaveBeenCalledTimes(2);
    expect(result.current.conversations).toHaveLength(2);
  });

  it("remove filters the conversation out locally on success", async () => {
    listConversationsMock.mockResolvedValue([
      makeConversation({ id: "conv-1" }),
      makeConversation({ id: "conv-2" }),
    ]);
    deleteConversationMock.mockResolvedValue(undefined);

    const { result } = renderHook(() => useConversations());
    await waitFor(() => expect(result.current.conversations).toHaveLength(2));

    await act(async () => {
      await result.current.remove("conv-1");
    });

    expect(deleteConversationMock).toHaveBeenCalledWith("conv-1");
    expect(result.current.conversations.map((c) => c.id)).toEqual(["conv-2"]);
    expect(result.current.error).toBeNull();
  });

  it("remove rethrows and keeps the list unchanged on failure", async () => {
    listConversationsMock.mockResolvedValue([makeConversation({ id: "conv-1" })]);
    deleteConversationMock.mockRejectedValue(new Error("delete failed"));

    const { result } = renderHook(() => useConversations());
    await waitFor(() => expect(result.current.conversations).toHaveLength(1));

    let caught: unknown;
    await act(async () => {
      await result.current.remove("conv-1").catch((err) => {
        caught = err;
      });
    });

    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error).message).toBe("delete failed");
    expect(result.current.conversations).toHaveLength(1);
    expect(result.current.error).toBe("delete failed");
  });
});
