import NotFound from "@/app/not-found";
import { render, screen } from "../test-utils";

describe("NotFound (app/not-found.tsx)", () => {
  it("renders the 404 message and a link back to the dashboard", () => {
    render(<NotFound />);

    expect(screen.getByText("404")).toBeInTheDocument();
    expect(screen.getByText("Page not found")).toBeInTheDocument();
    const homeLink = screen.getByRole("link", { name: "Go to dashboard" });
    expect(homeLink).toHaveAttribute("href", "/");
  });
});
