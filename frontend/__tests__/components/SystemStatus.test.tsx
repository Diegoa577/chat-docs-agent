import { SystemStatus } from "@/components/SystemStatus";
import { act, mockFetchResponse, render, screen } from "../test-utils";

const API_URL = "http://localhost:8000";

const fetchMock = jest.fn();

async function flushPromises() {
  await act(async () => {});
}

describe("SystemStatus", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    fetchMock.mockReset();
    global.fetch = fetchMock;
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("starts in the loading state and fetches /ready", () => {
    fetchMock.mockReturnValue(new Promise(() => {}));

    render(<SystemStatus />);

    expect(screen.getByLabelText("System status: Checking status...")).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(`${API_URL}/ready`, { cache: "no-store" });
  });

  it("shows the success state when the backend responds ok", async () => {
    fetchMock.mockResolvedValue(mockFetchResponse({ status: "ready" }));

    render(<SystemStatus />);
    await flushPromises();

    expect(screen.getByLabelText("System status: System ready")).toBeInTheDocument();
    expect(screen.getByText("ok")).toBeInTheDocument();
  });

  it("shows the degraded state with the server detail on a non-ok response", async () => {
    fetchMock.mockResolvedValue(
      mockFetchResponse({ detail: "Redis unavailable" }, { ok: false, status: 503 })
    );

    render(<SystemStatus />);
    await flushPromises();

    expect(
      screen.getByLabelText("System status: Redis unavailable")
    ).toBeInTheDocument();
    expect(screen.getByText("degraded")).toBeInTheDocument();
  });

  it("falls back to a generic degraded message when there is no detail", async () => {
    fetchMock.mockResolvedValue(
      mockFetchResponse({}, { ok: false, status: 500 })
    );

    render(<SystemStatus />);
    await flushPromises();

    expect(
      screen.getByLabelText("System status: System not ready")
    ).toBeInTheDocument();
  });

  it("shows Backend unreachable when the fetch rejects", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    render(<SystemStatus />);
    await flushPromises();

    expect(
      screen.getByLabelText("System status: Backend unreachable")
    ).toBeInTheDocument();
    expect(screen.getByText("error")).toBeInTheDocument();
  });

  it("polls again every 15 seconds", async () => {
    fetchMock.mockResolvedValue(mockFetchResponse({ status: "ready" }));

    render(<SystemStatus />);
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    act(() => {
      jest.advanceTimersByTime(15000);
    });
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    act(() => {
      jest.advanceTimersByTime(15000);
    });
    await flushPromises();
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
