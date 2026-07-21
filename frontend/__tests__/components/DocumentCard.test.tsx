import { DocumentCard } from "@/components/DocumentCard";
import { makeDocument, render, screen, userEvent, waitFor } from "../test-utils";

// NOTE: next/jest's SWC transform rewrites `@/` imports at compile time, but
// jest.mock() specifiers are resolved at runtime where no `@/` alias exists.
// Use a relative path so the mock registers against the same resolved module.
jest.mock("../../lib/api", () => ({
  downloadDocument: jest.fn(),
  reprocessDocument: jest.fn(),
}));

import { reprocessDocument } from "../../lib/api";

const mockReprocessDocument = reprocessDocument as jest.Mock;

function deferred<T = void>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("DocumentCard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("shows a spinner and the Pending label for pending documents", () => {
    render(
      <DocumentCard document={makeDocument({ status: "pending" })} onDelete={jest.fn()} />
    );

    expect(screen.getByText("Pending")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows a spinner and the Processing label for processing documents", () => {
    render(
      <DocumentCard document={makeDocument({ status: "processing" })} onDelete={jest.fn()} />
    );

    expect(screen.getByText("Processing")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });

  it("shows the Ready label without a spinner for completed documents", () => {
    render(
      <DocumentCard document={makeDocument({ status: "completed" })} onDelete={jest.fn()} />
    );

    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows error styling and the error message for failed documents", () => {
    render(
      <DocumentCard
        document={makeDocument({ status: "failed", error_message: "Parsing exploded" })}
        onDelete={jest.fn()}
      />
    );

    const chip = screen.getByText("Failed");
    expect(chip).toBeInTheDocument();
    expect(chip.closest(".MuiChip-root")).toHaveClass("MuiChip-colorError");
    expect(screen.getByText("Parsing exploded")).toBeInTheDocument();
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows the retry button only for failed documents", () => {
    const { rerender } = render(
      <DocumentCard document={makeDocument({ status: "completed" })} onDelete={jest.fn()} />
    );
    expect(
      screen.queryByRole("button", { name: "Retry processing protocol.pdf" })
    ).not.toBeInTheDocument();

    rerender(
      <DocumentCard document={makeDocument({ status: "failed" })} onDelete={jest.fn()} />
    );
    expect(
      screen.getByRole("button", { name: "Retry processing protocol.pdf" })
    ).toBeInTheDocument();
  });

  it("reprocesses the document and notifies the parent on success", async () => {
    mockReprocessDocument.mockResolvedValue(makeDocument({ status: "pending" }));
    const onReprocessed = jest.fn();
    const user = userEvent.setup();

    render(
      <DocumentCard
        document={makeDocument({ id: "doc-7", status: "failed" })}
        onDelete={jest.fn()}
        onReprocessed={onReprocessed}
      />
    );
    await user.click(
      screen.getByRole("button", { name: "Retry processing protocol.pdf" })
    );

    await waitFor(() => expect(onReprocessed).toHaveBeenCalledTimes(1));
    expect(mockReprocessDocument).toHaveBeenCalledWith("doc-7");
  });

  it("reports reprocess failures via onReprocessError", async () => {
    mockReprocessDocument.mockRejectedValue(new Error("boom"));
    const onReprocessError = jest.fn();
    const user = userEvent.setup();

    render(
      <DocumentCard
        document={makeDocument({ status: "failed" })}
        onDelete={jest.fn()}
        onReprocessError={onReprocessError}
      />
    );
    await user.click(
      screen.getByRole("button", { name: "Retry processing protocol.pdf" })
    );

    await waitFor(() =>
      expect(onReprocessError).toHaveBeenCalledWith("Failed to reprocess document")
    );
  });

  it("disables the retry button while reprocessing is in flight", async () => {
    const pending = deferred<unknown>();
    mockReprocessDocument.mockReturnValue(pending.promise);
    const user = userEvent.setup();

    render(
      <DocumentCard document={makeDocument({ status: "failed" })} onDelete={jest.fn()} />
    );
    const retryButton = screen.getByRole("button", {
      name: "Retry processing protocol.pdf",
    });
    await user.click(retryButton);
    await waitFor(() => expect(retryButton).toBeDisabled());

    pending.resolve(makeDocument({ status: "pending" }));
    await waitFor(() => expect(retryButton).toBeEnabled());
  });

  it("opens the confirmation dialog and does not call onDelete when cancelled", async () => {
    const onDelete = jest.fn();
    const user = userEvent.setup();

    render(<DocumentCard document={makeDocument()} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));

    expect(await screen.findByText("Delete document?")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onDelete).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(screen.queryByText("Delete document?")).not.toBeInTheDocument()
    );
  });

  it("calls onDelete with the document id when confirmed", async () => {
    const onDelete = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(<DocumentCard document={makeDocument({ id: "doc-42" })} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));
    await user.click(await screen.findByRole("button", { name: "Delete" }));

    await waitFor(() => expect(onDelete).toHaveBeenCalledWith("doc-42"));
  });

  it("disables the confirm button while deletion is in flight", async () => {
    const pending = deferred();
    const onDelete = jest.fn().mockReturnValue(pending.promise);
    const user = userEvent.setup();

    render(<DocumentCard document={makeDocument()} onDelete={onDelete} />);
    await user.click(screen.getByRole("button", { name: "Delete protocol.pdf" }));
    const confirmButton = await screen.findByRole("button", { name: "Delete" });

    await user.click(confirmButton);
    await waitFor(() => expect(confirmButton).toBeDisabled());

    pending.resolve();
    await waitFor(() =>
      expect(screen.queryByText("Delete document?")).not.toBeInTheDocument()
    );
  });
});
