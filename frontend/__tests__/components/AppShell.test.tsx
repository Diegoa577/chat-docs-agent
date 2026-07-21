import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { AppShell } from "@/components/AppShell";
import { useAppContext } from "@/context/AppContext";
import {
  mockFetchResponse,
  renderWithProviders,
  screen,
  waitFor,
} from "../test-utils";

const fetchMock = jest.fn();

function SidebarProbe() {
  const { setSidebar } = useAppContext();
  useEffect(() => {
    setSidebar(<div>sidebar-content</div>);
    return () => setSidebar(null);
  }, [setSidebar]);
  return null;
}

describe("AppShell", () => {
  beforeEach(() => {
    fetchMock.mockReset();
    fetchMock.mockResolvedValue(mockFetchResponse({ status: "ready" }));
    global.fetch = fetchMock;
    (usePathname as jest.Mock).mockReturnValue("/");
  });

  it("renders the navigation items with their hrefs", () => {
    renderWithProviders(<AppShell>{null}</AppShell>, { withAppProvider: true });

    // The shell renders both a temporary and a permanent drawer, so each
    // nav item appears twice.
    for (const [name, href] of [
      ["Dashboard", "/"],
      ["Chat", "/chat"],
      ["Documents", "/documents"],
    ] as const) {
      const links = screen.getAllByRole("link", { name });
      expect(links.length).toBeGreaterThan(0);
      for (const link of links) {
        expect(link).toHaveAttribute("href", href);
      }
    }
  });

  it("marks the nav item matching the pathname as active", () => {
    (usePathname as jest.Mock).mockReturnValue("/documents");

    renderWithProviders(<AppShell>{null}</AppShell>, { withAppProvider: true });

    for (const link of screen.getAllByRole("link", { name: "Documents" })) {
      expect(link).toHaveClass("Mui-selected");
    }
    for (const link of screen.getAllByRole("link", { name: "Chat" })) {
      expect(link).not.toHaveClass("Mui-selected");
    }
    for (const link of screen.getAllByRole("link", { name: "Dashboard" })) {
      expect(link).not.toHaveClass("Mui-selected");
    }
  });

  it("renders children in the main content area", () => {
    renderWithProviders(
      <AppShell>
        <div>page-content</div>
      </AppShell>,
      { withAppProvider: true }
    );

    expect(screen.getByText("page-content")).toBeInTheDocument();
  });

  it("renders the sidebar node injected through the AppContext slot", async () => {
    renderWithProviders(
      <>
        <SidebarProbe />
        <AppShell>{null}</AppShell>
      </>,
      { withAppProvider: true }
    );

    await waitFor(() =>
      expect(screen.getAllByText("sidebar-content").length).toBeGreaterThan(0)
    );
  });
});
