import { act } from "@testing-library/react";
import DashboardPage from "@/app/page";
import { listConversations, listDocuments } from "@/lib/api";
import { makeConversation, makeDocument, render, screen } from "../test-utils";

// NOTE: jest.mock specifiers must be relative paths (see chat-page.test.tsx).
jest.mock("../../lib/api", () => ({
  listDocuments: jest.fn(),
  listConversations: jest.fn(),
}));

const mockListDocuments = listDocuments as jest.Mock;
const mockListConversations = listConversations as jest.Mock;

describe("DashboardPage (app/page.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows placeholders while the stats are loading", async () => {
    mockListDocuments.mockReturnValue(new Promise(() => {}));
    mockListConversations.mockReturnValue(new Promise(() => {}));

    await act(async () => {
      render(<DashboardPage />);
    });

    expect(screen.getAllByText("—")).toHaveLength(2);
  });

  it("shows document and conversation counts after loading", async () => {
    mockListDocuments.mockResolvedValue([
      makeDocument({ id: "doc-1", status: "completed" }),
      makeDocument({ id: "doc-2", status: "completed" }),
      makeDocument({ id: "doc-3", status: "failed" }),
    ]);
    mockListConversations.mockResolvedValue([
      makeConversation({ id: "conv-1" }),
      makeConversation({ id: "conv-2" }),
    ]);

    await act(async () => {
      render(<DashboardPage />);
    });

    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByText("2 ready")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("All time")).toBeInTheDocument();
    expect(screen.queryByText("—")).not.toBeInTheDocument();
  });

  it("links the stat cards to /documents and /chat", async () => {
    mockListDocuments.mockResolvedValue([]);
    mockListConversations.mockResolvedValue([]);

    await act(async () => {
      render(<DashboardPage />);
    });

    const docsLink = screen.getByRole("link", { name: "Go to Documents" });
    const chatLink = screen.getByRole("link", { name: "Go to Conversations" });
    expect(docsLink).toHaveAttribute("href", "/documents");
    expect(chatLink).toHaveAttribute("href", "/chat");
  });
});
