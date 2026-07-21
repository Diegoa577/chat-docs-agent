import { act, makeDocument, renderHook, waitFor } from "../test-utils";
import { useDocuments } from "@/lib/hooks/useDocuments";
import { deleteDocument, listDocuments } from "@/lib/api";
import { POLLING_INTERVAL_MS } from "@/lib/constants";

// NOTE: the "@/" path alias is only rewritten by SWC in import statements,
// so jest.mock must use a relative path (it resolves to the same module).
jest.mock("../../lib/api");

const listDocumentsMock = listDocuments as jest.Mock;
const deleteDocumentMock = deleteDocument as jest.Mock;

beforeEach(() => {
  jest.clearAllMocks();
  jest.spyOn(console, "error").mockImplementation(() => undefined);
});

afterEach(() => {
  (console.error as jest.Mock).mockRestore();
  jest.useRealTimers();
});

describe("useDocuments", () => {
  it("fetches documents on mount and toggles isLoading true -> false", async () => {
    const docs = [makeDocument({ id: "doc-1" }), makeDocument({ id: "doc-2" })];
    listDocumentsMock.mockResolvedValue(docs);

    const { result } = renderHook(() => useDocuments());

    // The mount effect runs synchronously inside act(), so the fetch is in flight.
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.documents).toHaveLength(2));
    expect(result.current.documents.map((d) => d.id)).toEqual(["doc-1", "doc-2"]);
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(listDocumentsMock).toHaveBeenCalledTimes(1);
  });

  it("sets the error state when the initial fetch rejects", async () => {
    listDocumentsMock.mockRejectedValue(new Error("network down"));

    const { result } = renderHook(() => useDocuments());

    await waitFor(() => expect(result.current.error).toBe("network down"));
    expect(result.current.documents).toEqual([]);
    expect(result.current.isLoading).toBe(false);
  });

  it("polls every POLLING_INTERVAL_MS while a document is pending/processing", async () => {
    jest.useFakeTimers();
    listDocumentsMock.mockResolvedValue([makeDocument({ status: "processing" })]);

    const { result } = renderHook(() => useDocuments());
    await act(async () => undefined); // flush the initial refresh
    expect(listDocumentsMock).toHaveBeenCalledTimes(1);
    expect(result.current.documents[0].status).toBe("processing");

    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVAL_MS);
    });
    expect(listDocumentsMock).toHaveBeenCalledTimes(2);

    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVAL_MS);
    });
    expect(listDocumentsMock).toHaveBeenCalledTimes(3);
  });

  it("stops polling once every document is completed/failed", async () => {
    jest.useFakeTimers();
    listDocumentsMock.mockResolvedValue([makeDocument({ status: "pending" })]);

    const { result } = renderHook(() => useDocuments());
    await act(async () => undefined);
    expect(listDocumentsMock).toHaveBeenCalledTimes(1);

    // The next poll reports the document as completed.
    listDocumentsMock.mockResolvedValue([makeDocument({ status: "completed" })]);
    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVAL_MS);
    });
    expect(listDocumentsMock).toHaveBeenCalledTimes(2);
    expect(result.current.documents[0].status).toBe("completed");

    // No further polls are scheduled now that nothing is active.
    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVAL_MS * 5);
    });
    expect(listDocumentsMock).toHaveBeenCalledTimes(2);
  });

  it("never polls when the initial documents are all completed/failed", async () => {
    jest.useFakeTimers();
    listDocumentsMock.mockResolvedValue([
      makeDocument({ id: "doc-1", status: "completed" }),
      makeDocument({ id: "doc-2", status: "failed" }),
    ]);

    renderHook(() => useDocuments());
    await act(async () => undefined);
    expect(listDocumentsMock).toHaveBeenCalledTimes(1);

    await act(async () => {
      jest.advanceTimersByTime(POLLING_INTERVAL_MS * 5);
    });
    expect(listDocumentsMock).toHaveBeenCalledTimes(1);
  });

  it("remove filters the document out locally on success", async () => {
    listDocumentsMock.mockResolvedValue([
      makeDocument({ id: "doc-1" }),
      makeDocument({ id: "doc-2" }),
    ]);
    deleteDocumentMock.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.documents).toHaveLength(2));

    await act(async () => {
      await result.current.remove("doc-1");
    });

    expect(deleteDocumentMock).toHaveBeenCalledWith("doc-1");
    expect(result.current.documents.map((d) => d.id)).toEqual(["doc-2"]);
    expect(result.current.error).toBeNull();
  });

  it("remove rethrows and keeps the list unchanged on failure", async () => {
    listDocumentsMock.mockResolvedValue([makeDocument({ id: "doc-1" })]);
    deleteDocumentMock.mockRejectedValue(new Error("delete failed"));

    const { result } = renderHook(() => useDocuments());
    await waitFor(() => expect(result.current.documents).toHaveLength(1));

    let caught: unknown;
    await act(async () => {
      await result.current.remove("doc-1").catch((err) => {
        caught = err;
      });
    });

    expect(caught).toBeInstanceOf(Error);
    expect((caught as Error).message).toBe("delete failed");
    expect(result.current.documents).toHaveLength(1);
    expect(result.current.error).toBe("delete failed");
  });
});
