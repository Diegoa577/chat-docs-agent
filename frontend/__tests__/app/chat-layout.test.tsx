import ChatLayout from "@/app/chat/layout";
import { AppProvider, useAppContext } from "@/context/AppContext";
import { getLLMProviders, listConversations } from "@/lib/api";
import {
  makeConversation,
  makeMessage,
  makeProvider,
  render,
  screen,
  waitFor,
  within,
} from "../test-utils";

// ChatLayout mounts the real ChatProvider, which loads conversations and
// providers through the API client. NOTE: jest.mock specifiers must be
// relative paths — `@/…` aliases are only rewritten for import statements.
jest.mock("../../lib/api", () => ({
  listConversations: jest.fn(),
  deleteConversation: jest.fn(),
  getLLMProviders: jest.fn(),
}));

const mockListConversations = listConversations as jest.Mock;
const mockGetLLMProviders = getLLMProviders as jest.Mock;

/** Mimics AppShell: renders whatever is registered in the sidebar slot. */
function SidebarSlot() {
  const { sidebar } = useAppContext();
  return <div data-testid="sidebar-slot">{sidebar}</div>;
}

function renderShell({ withLayout }: { withLayout: boolean }) {
  return (
    <AppProvider>
      <SidebarSlot />
      {withLayout ? (
        <ChatLayout>
          <div data-testid="page-content" />
        </ChatLayout>
      ) : null}
    </AppProvider>
  );
}

describe("ChatLayout (app/chat/layout.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetLLMProviders.mockResolvedValue([makeProvider()]);
    mockListConversations.mockResolvedValue([
      makeConversation({
        id: "conv-1",
        messages: [makeMessage({ role: "user", content: "Dosage question" })],
      }),
    ]);
  });

  it("registers the conversation sidebar into the AppContext sidebar slot", async () => {
    render(renderShell({ withLayout: true }));

    const slot = screen.getByTestId("sidebar-slot");
    await waitFor(() =>
      expect(within(slot).getByText("Recent conversations")).toBeInTheDocument()
    );
    expect(within(slot).getByText("Dosage question")).toBeInTheDocument();
    expect(screen.getByTestId("page-content")).toBeInTheDocument();
  });

  it("clears the sidebar slot when the layout unmounts", async () => {
    const { rerender } = render(renderShell({ withLayout: true }));

    const slot = screen.getByTestId("sidebar-slot");
    await waitFor(() =>
      expect(within(slot).getByText("Recent conversations")).toBeInTheDocument()
    );

    rerender(renderShell({ withLayout: false }));

    await waitFor(() => expect(slot).toBeEmptyDOMElement());
  });
});
