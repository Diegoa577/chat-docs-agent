import { DocumentUploader } from "@/components/DocumentUploader";
import { uploadDocument } from "@/lib/api";
import {
  act,
  fireEvent,
  makeDocument,
  render,
  screen,
  setupUser,
  waitFor,
} from "../test-utils";

// NOTE: the "@/" path alias is only rewritten by SWC in import statements,
// so jest.mock must use a relative path (it resolves to the same module).
jest.mock("../../lib/api");

const mockUploadDocument = uploadDocument as jest.Mock;

function getFileInput(container: HTMLElement): HTMLInputElement {
  const input = container.querySelector('input[type="file"]');
  if (!input) throw new Error("file input not found");
  return input as HTMLInputElement;
}

function renderUploader() {
  const onUploaded = jest.fn();
  const onError = jest.fn();
  const utils = render(
    <DocumentUploader onUploaded={onUploaded} onError={onError} />
  );
  return { onUploaded, onError, ...utils };
}

describe("DocumentUploader", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUploadDocument.mockResolvedValue(makeDocument());
  });

  it("rejects unsupported file types without calling uploadDocument", () => {
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const png = new File(["pixels"], "image.png", { type: "image/png" });
    // fireEvent.change bypasses the accept-attribute filter that userEvent
    // applies, so the component's own validation is exercised.
    fireEvent.change(input, { target: { files: [png] } });

    expect(onError).toHaveBeenCalledWith(
      "Only PDF, TXT, and DOCX files are supported."
    );
    expect(mockUploadDocument).not.toHaveBeenCalled();
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("uploads a valid PDF through the hidden file input", async () => {
    const user = setupUser();
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const pdf = new File(["%PDF-1.4"], "protocol.pdf", {
      type: "application/pdf",
    });

    await act(async () => {
      await user.upload(input, pdf);
    });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
    expect(mockUploadDocument).toHaveBeenCalledWith(pdf);
    expect(onError).not.toHaveBeenCalled();
  });

  it("calls onError with the error message when the upload fails", async () => {
    const user = setupUser();
    mockUploadDocument.mockRejectedValue(new Error("Server exploded"));
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const pdf = new File(["%PDF-1.4"], "protocol.pdf", {
      type: "application/pdf",
    });

    await act(async () => {
      await user.upload(input, pdf);
    });

    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith("Server exploded")
    );
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("accepts a .docx file even when the MIME type is generic", async () => {
    const user = setupUser();
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const docx = new File(["doc-content"], "report.docx", {
      type: "application/octet-stream",
    });

    await act(async () => {
      await user.upload(input, docx);
    });

    await waitFor(() => expect(onUploaded).toHaveBeenCalledTimes(1));
    expect(mockUploadDocument).toHaveBeenCalledWith(docx);
    expect(onError).not.toHaveBeenCalled();
  });

  it("shows the default browse prompt", () => {
    renderUploader();
    expect(screen.getByText("Upload a document")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Browse files/i })
    ).toBeInTheDocument();
  });

  it("rejects files over the size limit without calling uploadDocument", () => {
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const big = new File(["%PDF-1.4"], "big.pdf", { type: "application/pdf" });
    Object.defineProperty(big, "size", { value: 51 * 1024 * 1024 });

    fireEvent.change(input, { target: { files: [big] } });

    expect(onError).toHaveBeenCalledWith("File exceeds the 50MB limit.");
    expect(mockUploadDocument).not.toHaveBeenCalled();
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("rejects multiple files at once without calling uploadDocument", () => {
    const { container, onUploaded, onError } = renderUploader();
    const input = getFileInput(container);
    const pdfA = new File(["a"], "a.pdf", { type: "application/pdf" });
    const pdfB = new File(["b"], "b.pdf", { type: "application/pdf" });

    fireEvent.change(input, { target: { files: [pdfA, pdfB] } });

    expect(onError).toHaveBeenCalledWith("Please upload one file at a time.");
    expect(mockUploadDocument).not.toHaveBeenCalled();
    expect(onUploaded).not.toHaveBeenCalled();
  });

  it("ignores additional files while an upload is in progress", async () => {
    let resolveUpload: (doc: unknown) => void = () => {};
    mockUploadDocument.mockReturnValue(
      new Promise((resolve) => {
        resolveUpload = resolve;
      })
    );
    const { container, onError } = renderUploader();
    const input = getFileInput(container);
    const pdfA = new File(["a"], "a.pdf", { type: "application/pdf" });
    const pdfB = new File(["b"], "b.pdf", { type: "application/pdf" });

    await act(async () => {
      fireEvent.change(input, { target: { files: [pdfA] } });
    });
    await act(async () => {
      fireEvent.change(input, { target: { files: [pdfB] } });
    });

    expect(mockUploadDocument).toHaveBeenCalledTimes(1);
    expect(mockUploadDocument).toHaveBeenCalledWith(pdfA);
    expect(onError).not.toHaveBeenCalled();

    resolveUpload(makeDocument());
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /Browse files/i })
      ).toBeEnabled()
    );
  });

  it("shows an inline error message with role=alert on validation failure", () => {
    const { container } = renderUploader();
    const input = getFileInput(container);
    const png = new File(["pixels"], "image.png", { type: "image/png" });

    fireEvent.change(input, { target: { files: [png] } });

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Only PDF, TXT, and DOCX files are supported."
    );
  });

  it("keeps the dragging state when the pointer moves over child elements", () => {
    renderUploader();
    const dropZone = screen.getByRole("button", { name: "Upload a document" });

    fireEvent.dragEnter(dropZone);
    const draggingClass = dropZone.className;

    // Moving over a child element fires a dragEnter/dragLeave pair; the
    // highlight must remain until the counter returns to zero.
    fireEvent.dragEnter(dropZone);
    fireEvent.dragLeave(dropZone);
    expect(dropZone.className).toBe(draggingClass);

    fireEvent.dragLeave(dropZone);
    expect(dropZone.className).not.toBe(draggingClass);
  });
});
