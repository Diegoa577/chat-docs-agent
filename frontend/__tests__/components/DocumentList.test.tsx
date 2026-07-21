import { DocumentList } from "@/components/DocumentList";
import { makeDocument, render, screen, userEvent, waitFor } from "../test-utils";

// See DocumentCard.test.tsx: jest.mock specifiers must be relative paths.
jest.mock("../../lib/api", () => ({
  downloadDocument: jest.fn(),
}));

describe("DocumentList", () => {
  it("shows a spinner while loading with an empty list", () => {
    render(<DocumentList documents={[]} isLoading onDelete={jest.fn()} />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(screen.queryByText("No documents uploaded yet.")).not.toBeInTheDocument();
  });

  it("shows the empty-state message when there are no documents", () => {
    render(<DocumentList documents={[]} onDelete={jest.fn()} />);

    expect(screen.getByText("No documents uploaded yet.")).toBeInTheDocument();
    expect(
      screen.getByText("Upload a document to start asking questions.")
    ).toBeInTheDocument();
  });

  it("renders one DocumentCard per document", () => {
    const documents = [
      makeDocument({ id: "doc-1", filename: "protocol.pdf" }),
      makeDocument({ id: "doc-2", filename: "sop.docx", status: "processing" }),
      makeDocument({ id: "doc-3", filename: "notes.txt", status: "pending" }),
    ];

    render(<DocumentList documents={documents} onDelete={jest.fn()} />);

    expect(screen.getByText("protocol.pdf")).toBeInTheDocument();
    expect(screen.getByText("sop.docx")).toBeInTheDocument();
    expect(screen.getByText("notes.txt")).toBeInTheDocument();
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("wires the delete action through to onDelete", async () => {
    const onDelete = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <DocumentList
        documents={[makeDocument({ id: "doc-9", filename: "protocol.pdf" })]}
        onDelete={onDelete}
      />
    );

    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledWith("doc-9"));
  });
});
