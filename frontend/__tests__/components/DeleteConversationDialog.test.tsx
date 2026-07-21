import { DeleteConversationDialog } from "@/components/DeleteConversationDialog";
import { fireEvent, render, screen, userEvent, within } from "../test-utils";

function renderDialog(overrides: Partial<Parameters<typeof DeleteConversationDialog>[0]> = {}) {
  const props = {
    open: true,
    conversationTitle: "My conversation",
    isDeleting: false,
    onCancel: jest.fn(),
    onConfirm: jest.fn(),
    ...overrides,
  };
  render(<DeleteConversationDialog {...props} />);
  return props;
}

describe("DeleteConversationDialog", () => {
  it("renders the title, body and actions", () => {
    renderDialog();

    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText("Delete conversation?")).toBeInTheDocument();
    expect(within(dialog).getByText(/My conversation/)).toBeInTheDocument();
    expect(
      within(dialog).getByText(/This action cannot be undone/)
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Cancel" })).toBeEnabled();
    expect(within(dialog).getByRole("button", { name: "Delete" })).toBeEnabled();
  });

  it("autofocuses the Cancel button", async () => {
    renderDialog();

    const cancel = await screen.findByRole("button", { name: "Cancel" });
    expect(cancel).toHaveFocus();
  });

  it("calls onCancel when Cancel is clicked and onConfirm when Delete is clicked", async () => {
    const props = renderDialog();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(props.onCancel).toHaveBeenCalledTimes(1);
    expect(props.onConfirm).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Delete" }));
    expect(props.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("disables actions and shows the deleting state while isDeleting", () => {
    renderDialog({ isDeleting: true });

    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    const deleteButton = screen.getByRole("button", { name: "Deleting..." });
    expect(deleteButton).toBeDisabled();
    expect(within(deleteButton).getByRole("progressbar")).toBeInTheDocument();
  });

  it("does not close on Escape while deleting", () => {
    const props = renderDialog({ isDeleting: true });

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" });

    expect(props.onCancel).not.toHaveBeenCalled();
  });

  it("does not close on backdrop click while deleting", async () => {
    const props = renderDialog({ isDeleting: true });
    const user = userEvent.setup();

    const backdrop = document.querySelector(".MuiBackdrop-root")!;
    await user.click(backdrop as Element);

    expect(props.onCancel).not.toHaveBeenCalled();
  });

  it("closes on Escape when not deleting", () => {
    const props = renderDialog();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape", code: "Escape" });

    expect(props.onCancel).toHaveBeenCalledTimes(1);
  });

  it("renders nothing when closed", () => {
    renderDialog({ open: false });

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
