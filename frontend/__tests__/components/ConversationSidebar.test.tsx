import { usePathname } from "next/navigation";
import { ConversationSidebar } from "@/components/ConversationSidebar";
import {
  makeConversation,
  makeMessage,
  render,
  screen,
  userEvent,
  waitFor,
  within,
} from "../test-utils";

function deferred<T = void>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((res) => {
    resolve = res;
  });
  return { promise, resolve };
}

describe("ConversationSidebar", () => {
  beforeEach(() => {
    (usePathname as jest.Mock).mockReturnValue("/chat");
  });

  it("links the New conversation button to /chat", () => {
    render(<ConversationSidebar conversations={[]} />);

    const button = screen.getByRole("link", { name: "New conversation" });
    expect(button).toHaveAttribute("href", "/chat");
  });

  it("shows the empty state when there are no conversations", () => {
    render(<ConversationSidebar conversations={[]} />);

    expect(screen.getByText("No conversations yet.")).toBeInTheDocument();
  });

  it("shows a loading indicator while loading", () => {
    render(<ConversationSidebar conversations={[]} isLoading />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByText("No conversations yet.")).not.toBeInTheDocument();
  });

  it("sorts conversations by updated_at descending", () => {
    const conversations = [
      makeConversation({
        id: "conv-old",
        messages: [makeMessage({ content: "Oldest chat" })],
        updated_at: "2024-01-01T00:00:00Z",
      }),
      makeConversation({
        id: "conv-new",
        messages: [makeMessage({ content: "Newest chat" })],
        updated_at: "2024-03-01T00:00:00Z",
      }),
      makeConversation({
        id: "conv-mid",
        messages: [makeMessage({ content: "Middle chat" })],
        updated_at: "2024-02-01T00:00:00Z",
      }),
    ];

    render(<ConversationSidebar conversations={conversations} />);

    const links = screen.getAllByRole("link", { name: /chat/i });
    const titles = links.map((link) => link.textContent);
    expect(titles[0]).toContain("Newest chat");
    expect(titles[1]).toContain("Middle chat");
    expect(titles[2]).toContain("Oldest chat");
  });

  it("uses the first user message as the title, truncated at 40 characters", () => {
    const longContent =
      "What are the inclusion criteria for patients in the phase III trial?";
    const conversations = [
      makeConversation({
        id: "conv-1",
        messages: [
          makeMessage({ role: "assistant", content: "I am an assistant" }),
          makeMessage({ role: "user", content: longContent }),
        ],
      }),
    ];

    render(<ConversationSidebar conversations={conversations} />);

    expect(screen.getByText(`${longContent.slice(0, 40)}...`)).toBeInTheDocument();
  });

  it("falls back to a sliced conversation id when there are no user messages", () => {
    const conversations = [
      makeConversation({ id: "abcdef12-3456-7890", messages: [] }),
    ];

    render(<ConversationSidebar conversations={conversations} />);

    expect(screen.getByText("Conversation abcdef12")).toBeInTheDocument();
  });

  it("marks the conversation matching the pathname as active", () => {
    (usePathname as jest.Mock).mockReturnValue("/chat/conv-2");
    const conversations = [
      makeConversation({ id: "conv-1", messages: [makeMessage({ content: "First" })] }),
      makeConversation({ id: "conv-2", messages: [makeMessage({ content: "Second" })] }),
    ];

    render(<ConversationSidebar conversations={conversations} />);

    const activeLink = screen.getByRole("link", { name: /Second/ });
    const inactiveLink = screen.getByRole("link", { name: /First/ });
    expect(activeLink).toHaveClass("Mui-selected");
    expect(inactiveLink).not.toHaveClass("Mui-selected");
  });

  it("does not render delete buttons when onDelete is not provided", () => {
    render(
      <ConversationSidebar
        conversations={[makeConversation()]}
      />
    );

    expect(
      screen.queryByRole("button", { name: "Delete conversation" })
    ).not.toBeInTheDocument();
  });

  it("opens the dialog, confirms deletion and calls onDelete with the id", async () => {
    const pending = deferred();
    const onDelete = jest.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();
    const conversation = makeConversation({
      id: "conv-7",
      messages: [makeMessage({ content: "Delete me" })],
    });

    render(<ConversationSidebar conversations={[conversation]} onDelete={onDelete} />);

    const item = screen.getByRole("link", { name: /Delete me/ }).closest("li")!;
    await user.click(
      within(item).getByRole("button", { name: "Delete conversation" })
    );

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Delete conversation?")).toBeInTheDocument();
    expect(within(dialog).getByText(/Delete me/)).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Delete" }));

    expect(onDelete).toHaveBeenCalledWith("conv-7");
    // Dialog enters the deleting state while onDelete is pending.
    expect(
      await within(dialog).findByRole("button", { name: "Deleting..." })
    ).toBeDisabled();

    pending.resolve();
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
  });

  it("cancelling the dialog closes it without calling onDelete", async () => {
    const onDelete = jest.fn();
    const user = userEvent.setup();

    render(
      <ConversationSidebar conversations={[makeConversation()]} onDelete={onDelete} />
    );

    await user.click(screen.getByRole("button", { name: "Delete conversation" }));
    const dialog = await screen.findByRole("dialog");

    await user.click(within(dialog).getByRole("button", { name: "Cancel" }));

    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
    expect(onDelete).not.toHaveBeenCalled();
  });
});
