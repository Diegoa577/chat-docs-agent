import { ChatInput } from "@/components/ChatInput";
import { useChatContext } from "@/context/ChatContext";
import { makeProvider, render, screen, setupUser } from "../test-utils";

// Mock the chat context so each test controls providers/selection directly
// instead of relying on ChatProvider's async data loading. NOTE: the "@/"
// path alias is only rewritten by SWC in import statements, so jest.mock
// must use a relative path (it resolves to the same module).
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

describe("ChatInput", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseChatContext.mockReturnValue(buildContext());
  });

  it("disables the send button when the input is empty", () => {
    render(<ChatInput onSend={jest.fn()} />);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("enables the send button when text is entered and a provider is selected", async () => {
    const user = setupUser();
    render(<ChatInput onSend={jest.fn()} />);
    await user.type(screen.getByPlaceholderText("Ask a question about your documents..."), "Hello");
    expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled();
  });

  it("disables the send button while streaming", async () => {
    const user = setupUser();
    const { rerender } = render(<ChatInput onSend={jest.fn()} />);
    await user.type(screen.getByPlaceholderText("Ask a question about your documents..."), "Hello");
    rerender(<ChatInput onSend={jest.fn()} isStreaming />);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it("submits on Enter with question, strictMode, provider and model", async () => {
    const user = setupUser();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);
    await user.type(screen.getByPlaceholderText("Ask a question about your documents..."), "What is the dosage?");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith(
      "What is the dosage?",
      false,
      "openai",
      "gpt-5.4-mini"
    );
    // Input is cleared after submit
    expect(screen.getByPlaceholderText("Ask a question about your documents...")).toHaveValue("");
  });

  it("does not submit on Shift+Enter", async () => {
    const user = setupUser();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);
    const input = screen.getByPlaceholderText("Ask a question about your documents...");
    await user.type(input, "Line one");
    await user.keyboard("{Shift>}{Enter}{/Shift}");
    expect(onSend).not.toHaveBeenCalled();
  });

  it("clicking a suggestion chip sends the suggestion with strict mode off", async () => {
    const user = setupUser();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} showSuggestions />);
    await user.click(
      screen.getByRole("button", { name: "What are the inclusion criteria?" })
    );
    expect(onSend).toHaveBeenCalledWith(
      "What are the inclusion criteria?",
      false,
      "openai",
      "gpt-5.4-mini"
    );
  });

  it("clicking a suggestion chip respects the strict mode toggle", async () => {
    const user = setupUser();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} showSuggestions />);
    await user.click(screen.getByRole("checkbox", { name: /Strict mode/i }));
    await user.click(
      screen.getByRole("button", { name: "What are the inclusion criteria?" })
    );
    expect(onSend).toHaveBeenCalledWith(
      "What are the inclusion criteria?",
      true,
      "openai",
      "gpt-5.4-mini"
    );
  });

  it("shows the stop button only while streaming and onStop is provided", async () => {
    const user = setupUser();
    const onStop = jest.fn();
    const { rerender } = render(<ChatInput onSend={jest.fn()} />);
    expect(
      screen.queryByRole("button", { name: "Stop generating" })
    ).not.toBeInTheDocument();

    rerender(<ChatInput onSend={jest.fn()} isStreaming />);
    expect(
      screen.queryByRole("button", { name: "Stop generating" })
    ).not.toBeInTheDocument();

    rerender(<ChatInput onSend={jest.fn()} isStreaming onStop={onStop} />);
    const stopButton = screen.getByRole("button", { name: "Stop generating" });
    await user.click(stopButton);
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it("passes strictMode=true after toggling the strict mode switch", async () => {
    const user = setupUser();
    const onSend = jest.fn();
    render(<ChatInput onSend={onSend} />);
    await user.click(screen.getByRole("checkbox", { name: /Strict mode/i }));
    await user.type(screen.getByPlaceholderText("Ask a question about your documents..."), "Hello");
    await user.keyboard("{Enter}");
    expect(onSend).toHaveBeenCalledWith(
      "Hello",
      true,
      "openai",
      "gpt-5.4-mini"
    );
  });

  it("shows the no-providers alert when the provider list is empty", () => {
    mockUseChatContext.mockReturnValue(
      buildContext({ providers: [], selectedProvider: "", selectedModel: "" })
    );
    render(<ChatInput onSend={jest.fn()} />);
    expect(
      screen.getByText(/No LLM providers are configured/)
    ).toBeInTheDocument();
  });

  it("does not show the no-providers alert while providers are loading", () => {
    mockUseChatContext.mockReturnValue(
      buildContext({ providers: [], isLoadingProviders: true })
    );
    render(<ChatInput onSend={jest.fn()} />);
    expect(
      screen.queryByText(/No LLM providers are configured/)
    ).not.toBeInTheDocument();
    expect(screen.getByText("Loading providers...")).toBeInTheDocument();
  });

  it("shows an error alert when providersError is set", () => {
    mockUseChatContext.mockReturnValue(
      buildContext({ providersError: "Failed to load providers" })
    );
    render(<ChatInput onSend={jest.fn()} />);
    expect(screen.getByText("Failed to load providers")).toBeInTheDocument();
  });
});
