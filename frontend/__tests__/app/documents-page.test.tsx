import DocumentsPage from "@/app/documents/page";
import { deleteDocument, listDocuments, uploadDocument } from "@/lib/api";
import {
  fireEvent,
  makeDocument,
  renderWithProviders,
  screen,
  userEvent,
  waitFor,
} from "../test-utils";

// NOTE: jest.mock specifiers must be relative paths (see chat-page.test.tsx).
jest.mock("../../lib/api", () => ({
  listDocuments: jest.fn(),
  deleteDocument: jest.fn(),
  uploadDocument: jest.fn(),
  downloadDocument: jest.fn(),
}));

const mockListDocuments = listDocuments as jest.Mock;
const mockDeleteDocument = deleteDocument as jest.Mock;
const mockUploadDocument = uploadDocument as jest.Mock;

describe("DocumentsPage (app/documents/page.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("loads and lists the documents", async () => {
    mockListDocuments.mockResolvedValue([
      makeDocument({ id: "doc-1", filename: "protocol.pdf" }),
      makeDocument({ id: "doc-2", filename: "sop.docx", status: "failed" }),
    ]);

    renderWithProviders(<DocumentsPage />, { withAppProvider: true });

    expect(await screen.findByText("protocol.pdf")).toBeInTheDocument();
    expect(screen.getByText("sop.docx")).toBeInTheDocument();
    expect(mockListDocuments).toHaveBeenCalledTimes(1);
  });

  it("shows the empty state when there are no documents", async () => {
    mockListDocuments.mockResolvedValue([]);

    renderWithProviders(<DocumentsPage />, { withAppProvider: true });

    expect(
      await screen.findByText("No documents uploaded yet.")
    ).toBeInTheDocument();
  });

  it("removes a document from the list after a confirmed delete", async () => {
    mockListDocuments.mockResolvedValue([
      makeDocument({ id: "doc-1", filename: "protocol.pdf" }),
      makeDocument({ id: "doc-2", filename: "sop.docx" }),
    ]);
    mockDeleteDocument.mockResolvedValue(undefined);
    const user = userEvent.setup();

    renderWithProviders(<DocumentsPage />, { withAppProvider: true });

    await screen.findByText("protocol.pdf");
    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(mockDeleteDocument).toHaveBeenCalledWith("doc-1"));
    await waitFor(() =>
      expect(screen.queryByText("protocol.pdf")).not.toBeInTheDocument()
    );
    expect(screen.getByText("sop.docx")).toBeInTheDocument();
  });

  it("does not delete when the confirm dialog is cancelled", async () => {
    mockListDocuments.mockResolvedValue([
      makeDocument({ id: "doc-1", filename: "protocol.pdf" }),
    ]);
    const user = userEvent.setup();

    renderWithProviders(<DocumentsPage />, { withAppProvider: true });

    await screen.findByText("protocol.pdf");
    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));
    await user.click(await screen.findByRole("button", { name: "Cancel" }));

    expect(mockDeleteDocument).not.toHaveBeenCalled();
    expect(screen.getByText("protocol.pdf")).toBeInTheDocument();
  });

  it("refreshes the list after a successful upload", async () => {
    const existing = makeDocument({ id: "doc-1", filename: "protocol.pdf" });
    const uploaded = makeDocument({ id: "doc-2", filename: "new-sop.pdf" });
    mockListDocuments
      .mockResolvedValueOnce([existing])
      .mockResolvedValue([existing, uploaded]);
    mockUploadDocument.mockResolvedValue(uploaded);

    const { container } = renderWithProviders(<DocumentsPage />, {
      withAppProvider: true,
    });

    await screen.findByText("protocol.pdf");
    expect(mockListDocuments).toHaveBeenCalledTimes(1);

    const input = container.querySelector('input[type="file"]')!;
    const file = new File(["pdf-bytes"], "new-sop.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(mockUploadDocument).toHaveBeenCalledWith(file));
    await waitFor(() => expect(mockListDocuments).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("new-sop.pdf")).toBeInTheDocument();
  });
});
