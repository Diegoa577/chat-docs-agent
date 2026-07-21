import { act, makeConversation, makeMessage, makeProvider, render, waitFor } from "../test-utils";
import { ChatProvider, useChatContext } from "@/context/ChatContext";
import { deleteConversation, getLLMProviders, listConversations } from "@/lib/api";

// NOTE: the "@/" path alias is only rewritten by SWC in import statements,
// so jest.mock must use a relative path (it resolves to the same module).
jest.mock("../../lib/api");

const getLLMProvidersMock = getLLMProviders as jest.Mock;
const listConversationsMock = listConversations as jest.Mock;
const deleteConversationMock = deleteConversation as jest.Mock;

let chatContext!: ReturnType<typeof useChatContext>;

function Probe() {
  chatContext = useChatContext();
  return null;
}

function renderProbe() {
  return render(
    <ChatProvider>
      <Probe />
    </ChatProvider>
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  getLLMProvidersMock.mockResolvedValue([makeProvider()]);
  listConversationsMock.mockResolvedValue([]);
  deleteConversationMock.mockResolvedValue(undefined);
});

describe("ChatContext providers", () => {
  it("loads providers on mount and defaults to the first provider/model", async () => {
    renderProbe();

    expect(chatContext.isLoadingProviders).toBe(true);

    await waitFor(() => expect(chatContext.isLoadingProviders).toBe(false));
    expect(getLLMProvidersMock).toHaveBeenCalledTimes(1);
    expect(chatContext.providers).toHaveLength(1);
    expect(chatContext.selectedProvider).toBe("openai");
    expect(chatContext.selectedModel).toBe("gpt-5.4-mini");
    expect(chatContext.providersError).toBeNull();
  });

  it("sets providersError when getLLMProviders rejects", async () => {
    getLLMProvidersMock.mockRejectedValue(new Error("providers down"));

    renderProbe();

    await waitFor(() => expect(chatContext.providersError).toBe("providers down"));
    expect(chatContext.isLoadingProviders).toBe(false);
    expect(chatContext.providers).toEqual([]);
    expect(chatContext.selectedProvider).toBe("");
    expect(chatContext.selectedModel).toBe("");
  });

  it("selectProvider resets the model to that provider's first model; selectModel sets it directly", async () => {
    getLLMProvidersMock.mockResolvedValue([
      makeProvider(),
      makeProvider({
        id: "gemini",
        display_name: "Google Gemini",
        models: [
          {
            id: "gemini-3.5-flash",
            display_name: "Gemini 3.5 Flash",
            default_temperature: 0.2,
            supports_json_mode: false,
          },
          {
            id: "gemini-2.5-flash",
            display_name: "Gemini 2.5 Flash",
            default_temperature: 0.2,
            supports_json_mode: false,
          },
        ],
      }),
    ]);

    renderProbe();
    await waitFor(() => expect(chatContext.selectedModel).toBe("gpt-5.4-mini"));

    act(() => {
      chatContext.selectProvider("gemini");
    });
    expect(chatContext.selectedProvider).toBe("gemini");
    expect(chatContext.selectedModel).toBe("gemini-3.5-flash");

    act(() => {
      chatContext.selectModel("gemini-2.5-flash");
    });
    expect(chatContext.selectedModel).toBe("gemini-2.5-flash");
  });
});

describe("ChatContext messages cache", () => {
  it("seeds the cache from the conversations list, allows overrides and evicts on delete", async () => {
    const messages = [makeMessage({ content: "cached" })];
    listConversationsMock.mockResolvedValue([
      makeConversation({ id: "conv-1", messages }),
    ]);

    renderProbe();

    await waitFor(() =>
      expect(chatContext.getCachedMessages("conv-1")).toEqual(messages)
    );

    // cacheMessages overrides the seeded entry.
    const override = [makeMessage({ content: "override" })];
    act(() => {
      chatContext.cacheMessages("conv-1", override);
    });
    expect(chatContext.getCachedMessages("conv-1")).toEqual(override);

    // deleteConversation calls the API and evicts the cache entry.
    await act(async () => {
      await chatContext.deleteConversation("conv-1");
    });
    expect(deleteConversationMock).toHaveBeenCalledWith("conv-1");
    expect(chatContext.getCachedMessages("conv-1")).toBeUndefined();
    expect(chatContext.conversations).toHaveLength(0);
  });
});

describe("useChatContext", () => {
  it("throws when used outside ChatProvider", () => {
    jest.spyOn(console, "error").mockImplementation(() => undefined);

    expect(() => render(<Probe />)).toThrow(
      "useChatContext must be used within ChatProvider"
    );

    (console.error as jest.Mock).mockRestore();
  });
});
