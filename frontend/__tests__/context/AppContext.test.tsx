import { act, render } from "../test-utils";
import { AppProvider, useAppContext } from "@/context/AppContext";

let appContext!: ReturnType<typeof useAppContext>;

function Probe() {
  appContext = useAppContext();
  return null;
}

function renderProbe() {
  return render(
    <AppProvider>
      <Probe />
    </AppProvider>
  );
}

afterEach(() => {
  jest.useRealTimers();
});

describe("AppContext", () => {
  it("showSnackbar adds a snackbar with the default severity", () => {
    renderProbe();

    act(() => {
      appContext.showSnackbar("Document uploaded");
    });

    expect(appContext.snackbars).toHaveLength(1);
    expect(appContext.snackbars[0]).toMatchObject({
      message: "Document uploaded",
      severity: "info",
    });
  });

  it("auto-removes a snackbar after 6000ms", () => {
    jest.useFakeTimers();
    renderProbe();

    act(() => {
      appContext.showSnackbar("Saved", "success");
    });
    expect(appContext.snackbars).toHaveLength(1);

    act(() => {
      jest.advanceTimersByTime(5999);
    });
    expect(appContext.snackbars).toHaveLength(1);

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(appContext.snackbars).toHaveLength(0);
  });

  it("closeSnackbar removes the snackbar immediately", () => {
    jest.useFakeTimers();
    renderProbe();

    act(() => {
      appContext.showSnackbar("First");
      appContext.showSnackbar("Second", "warning");
    });
    expect(appContext.snackbars).toHaveLength(2);

    const firstId = appContext.snackbars[0].id;
    act(() => {
      appContext.closeSnackbar(firstId);
    });

    expect(appContext.snackbars).toHaveLength(1);
    expect(appContext.snackbars[0].message).toBe("Second");
  });

  it("closeSnackbar cancels the auto-dismiss timer", () => {
    jest.useFakeTimers();
    renderProbe();

    act(() => {
      appContext.showSnackbar("First");
      appContext.showSnackbar("Second", "warning");
    });
    const firstId = appContext.snackbars[0].id;
    act(() => {
      appContext.closeSnackbar(firstId);
    });

    // Advancing past 6s must not resurrect or disturb the remaining snackbar.
    act(() => {
      jest.advanceTimersByTime(6000);
    });
    expect(appContext.snackbars).toHaveLength(0);
  });

  it("clears pending auto-dismiss timers on unmount", () => {
    jest.useFakeTimers();
    const { unmount } = renderProbe();

    act(() => {
      appContext.showSnackbar("Ephemeral");
    });
    unmount();

    // The timer was cleared: advancing time must not fire any callback.
    expect(jest.getTimerCount()).toBe(0);
    act(() => {
      jest.advanceTimersByTime(10000);
    });
  });

  it("setSidebar stores the node", () => {
    renderProbe();
    expect(appContext.sidebar).toBeNull();

    const node = <div>Sidebar content</div>;
    act(() => {
      appContext.setSidebar(node);
    });

    expect(appContext.sidebar).toBe(node);

    act(() => {
      appContext.setSidebar(null);
    });
    expect(appContext.sidebar).toBeNull();
  });

  it("toggleMobileOpen flips the mobile drawer state", () => {
    renderProbe();
    expect(appContext.mobileOpen).toBe(false);

    act(() => {
      appContext.toggleMobileOpen();
    });
    expect(appContext.mobileOpen).toBe(true);

    act(() => {
      appContext.setMobileOpen(false);
    });
    expect(appContext.mobileOpen).toBe(false);
  });

  it("useAppContext throws when used outside AppProvider", () => {
    jest.spyOn(console, "error").mockImplementation(() => undefined);

    expect(() => render(<Probe />)).toThrow(
      "useAppContext must be used within AppProvider"
    );

    (console.error as jest.Mock).mockRestore();
  });
});
