// useParams/notFound live in the manual mock (__mocks__/next/navigation.ts).
import { notFound, useParams } from "next/navigation";
import DocumentDetailPage from "@/app/documents/[documentId]/page";
import { ApiError, downloadDocument, getDocument } from "@/lib/api";
import {
  act,
  makeDocument,
  render,
  screen,
  setupUser,
  waitFor,
} from "../test-utils";

// Keep the real ApiError class (the page relies on instanceof), mock only the
// endpoint functions the page calls. NOTE: jest.mock specifiers must be
// relative paths — `@/…` aliases are only rewritten for import statements.
jest.mock("../../lib/api", () => {
  const actual = jest.requireActual("../../lib/api");
  return {
    ...actual,
    getDocument: jest.fn(),
    downloadDocument: jest.fn(),
  };
});

const mockGetDocument = getDocument as jest.Mock;
const mockDownloadDocument = downloadDocument as jest.Mock;
const mockUseParams = useParams as jest.Mock;
const mockNotFound = notFound as unknown as jest.Mock;

describe("DocumentDetailPage (app/documents/[documentId]/page.tsx)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseParams.mockReturnValue({ documentId: "doc-1" });
  });

  it("shows a loading indicator while the document is fetched", () => {
    mockGetDocument.mockReturnValue(new Promise(() => {}));

    render(<DocumentDetailPage />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders the document details once loaded", async () => {
    const doc = makeDocument({
      id: "doc-1",
      filename: "protocol.pdf",
      status: "completed",
      metadata: { pages: 12 },
    });
    mockGetDocument.mockResolvedValue(doc);

    render(<DocumentDetailPage />);

    expect(await screen.findByText("protocol.pdf")).toBeInTheDocument();
    expect(screen.getByText("completed")).toBeInTheDocument();
    expect(screen.getByText("application/pdf")).toBeInTheDocument();
    expect(screen.getByText(/doc-1/)).toBeInTheDocument();
    expect(screen.getByText(/"pages": 12/)).toBeInTheDocument();
    expect(mockNotFound).not.toHaveBeenCalled();
  });

  it("shows an inline error when the fetch fails", async () => {
    mockGetDocument.mockRejectedValue(new Error("Failed to load document"));

    render(<DocumentDetailPage />);

    expect(await screen.findByText("Failed to load document")).toBeInTheDocument();
    expect(mockNotFound).not.toHaveBeenCalled();
  });

  it("calls notFound() when the document does not exist (404)", async () => {
    mockGetDocument.mockRejectedValue(new ApiError("Document not found", 404));

    render(<DocumentDetailPage />);

    await waitFor(() => expect(mockNotFound).toHaveBeenCalledTimes(1));
  });

  it("shows the backend error message for failed documents", async () => {
    mockGetDocument.mockResolvedValue(
      makeDocument({ status: "failed", error_message: "Parsing exploded" })
    );

    render(<DocumentDetailPage />);

    expect(await screen.findByText(/Parsing exploded/)).toBeInTheDocument();
  });

  it("downloads the document when the download button is clicked", async () => {
    const user = setupUser();
    const doc = makeDocument({ id: "doc-1" });
    mockGetDocument.mockResolvedValue(doc);
    mockDownloadDocument.mockResolvedValue(undefined);

    render(<DocumentDetailPage />);
    await screen.findByText("protocol.pdf");

    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Download/ }));
    });

    expect(mockDownloadDocument).toHaveBeenCalledWith(doc);
  });

  it("shows an inline error when the download fails", async () => {
    const user = setupUser();
    mockGetDocument.mockResolvedValue(makeDocument());
    mockDownloadDocument.mockRejectedValue(new Error("Failed to download document"));

    render(<DocumentDetailPage />);
    await screen.findByText("protocol.pdf");

    await act(async () => {
      await user.click(screen.getByRole("button", { name: /Download/ }));
    });

    expect(await screen.findByText("Failed to download document")).toBeInTheDocument();
  });
});
