import { CitationCard } from "@/components/CitationCard";
import {
  act,
  makeCitation,
  render,
  screen,
  setupUser,
  waitFor,
} from "../test-utils";

describe("CitationCard", () => {
  it("renders the numbered document name, page and section caption", () => {
    render(<CitationCard citation={makeCitation()} index={0} />);
    expect(screen.getByText(/1\. protocol\.pdf \(page 3\)/)).toBeInTheDocument();
    expect(screen.getByText("Section: Inclusion Criteria")).toBeInTheDocument();
  });

  it("omits the page suffix when no page number is present", () => {
    render(
      <CitationCard citation={makeCitation({ page_number: null })} index={1} />
    );
    expect(screen.getByText(/2\. protocol\.pdf/)).toBeInTheDocument();
    expect(screen.queryByText(/\(page /)).not.toBeInTheDocument();
  });

  it("renders the page suffix for page 0", () => {
    render(
      <CitationCard citation={makeCitation({ page_number: 0 })} index={0} />
    );
    expect(screen.getByText(/1\. protocol\.pdf \(page 0\)/)).toBeInTheDocument();
  });

  it("keeps the excerpt collapsed by default and expands it on toggle", async () => {
    const user = setupUser();
    render(<CitationCard citation={makeCitation()} index={0} />);

    const excerpt = screen.getByText(/Patients aged 18 years or older/);
    const collapse = excerpt.closest(".MuiCollapse-root");
    expect(collapse).toHaveClass("MuiCollapse-hidden");

    const toggle = screen.getByRole("button", { name: "Show citation excerpt" });
    await act(async () => {
      await user.click(toggle);
    });

    // aria-label flips once expanded
    expect(
      screen.getByRole("button", { name: "Hide citation excerpt" })
    ).toBeInTheDocument();
    await waitFor(() =>
      expect(excerpt.closest(".MuiCollapse-root")).not.toHaveClass(
        "MuiCollapse-hidden"
      )
    );
  });

  it("collapses the excerpt again when toggled twice", async () => {
    const user = setupUser();
    render(<CitationCard citation={makeCitation()} index={0} />);

    await act(async () => {
      await user.click(
        screen.getByRole("button", { name: "Show citation excerpt" })
      );
    });
    await act(async () => {
      await user.click(
        screen.getByRole("button", { name: "Hide citation excerpt" })
      );
    });

    await waitFor(() =>
      expect(
        screen
          .getByText(/Patients aged 18 years or older/)
          .closest(".MuiCollapse-root")
      ).toHaveClass("MuiCollapse-hidden")
    );
  });
});
