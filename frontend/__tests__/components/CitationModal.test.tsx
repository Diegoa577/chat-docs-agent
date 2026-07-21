import { act } from "@testing-library/react";
import { CitationModal } from "@/components/CitationModal";
import {
  makeCitation,
  render,
  screen,
  setupUser,
  within,
} from "../test-utils";

describe("CitationModal", () => {
  it("renders nothing when the citation is null", () => {
    const { container } = render(
      <CitationModal citation={null} index={0} open onClose={jest.fn()} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows page/section chips and the full excerpt when open", () => {
    render(
      <CitationModal citation={makeCitation()} index={0} open onClose={jest.fn()} />
    );
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(/Source 1 — protocol\.pdf/)
    ).toBeInTheDocument();
    expect(within(dialog).getByText("Page 3")).toBeInTheDocument();
    expect(
      within(dialog).getByText("Section: Inclusion Criteria")
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Patients aged 18 years or older/)
    ).toBeInTheDocument();
  });

  it("omits the page and section chips when those fields are missing", () => {
    render(
      <CitationModal
        citation={makeCitation({ page_number: null, section_title: null })}
        index={2}
        open
        onClose={jest.fn()}
      />
    );
    const dialog = screen.getByRole("dialog");
    expect(
      within(dialog).getByText(/Source 3 — protocol\.pdf/)
    ).toBeInTheDocument();
    expect(within(dialog).queryByText(/^Page /)).not.toBeInTheDocument();
    expect(within(dialog).queryByText(/^Section:/)).not.toBeInTheDocument();
  });

  it("calls onClose when the close button is clicked", async () => {
    const user = setupUser();
    const onClose = jest.fn();
    render(
      <CitationModal citation={makeCitation()} index={0} open onClose={onClose} />
    );
    const dialog = screen.getByRole("dialog");
    await act(async () => {
      await user.click(
        within(dialog).getByRole("button", { name: "Close citation detail" })
      );
    });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
