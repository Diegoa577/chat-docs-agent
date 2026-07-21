import { MessageBubble } from "@/components/MessageBubble";
import {
  makeCitation,
  makeMessage,
  render,
  screen,
  setupUser,
  waitFor,
  within,
} from "../test-utils";

describe("MessageBubble", () => {
  it("renders a user message as plain text", () => {
    render(
      <MessageBubble
        message={makeMessage({ role: "user", content: "Hello **doc**" })}
      />
    );
    expect(screen.getByText("You")).toBeInTheDocument();
    // Markdown markers are shown literally for user messages
    expect(screen.getByText("Hello **doc**")).toBeInTheDocument();
  });

  it("renders assistant message content as markdown", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "This is **important**.",
        })}
      />
    );
    const strong = screen.getByText("important");
    expect(strong.tagName).toBe("STRONG");
  });

  it("renders inline code as a plain <code> element with the md-inline-code class", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "Use `dose_mg` for dosing.",
        })}
      />
    );
    const code = screen.getByText("dose_mg");
    expect(code.tagName).toBe("CODE");
    expect(code).toHaveClass("md-inline-code");
  });

  it("shows the streaming cursor but no metadata chips while streaming", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "user",
          content: "typing...",
          metadata: { isStreaming: true },
        })}
      />
    );
    const content = screen.getByText("typing...");
    // The blinking cursor is rendered as an inline <span> after the content
    expect(content.querySelector("span")).not.toBeNull();
  });

  it("does not show metadata chips while streaming", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "partial answer",
          metadata: {
            isStreaming: true,
            confidence: "high",
            intent: "search",
            model: "gpt-5.4-mini",
          },
        })}
      />
    );
    expect(screen.queryByText(/Confidence:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Intent:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Model:/)).not.toBeInTheDocument();
  });

  it("shows confidence, intent, model and strict-mode chips after streaming", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "Final answer.",
          metadata: {
            confidence: "high",
            intent: "search",
            model: "gpt-5.4-mini",
            strict_mode_applied: true,
          },
        })}
      />
    );
    const confidenceChip = screen.getByText("Confidence: high");
    // High confidence maps to the success color
    expect(confidenceChip.closest(".MuiChip-root")).toHaveClass(
      "MuiChip-colorSuccess"
    );
    expect(screen.getByText("Intent: search")).toBeInTheDocument();
    expect(screen.getByText("Model: gpt-5.4-mini")).toBeInTheDocument();
    expect(screen.getByText("Strict mode applied")).toBeInTheDocument();
  });

  it("maps low confidence to the error color", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "Final answer.",
          metadata: { confidence: "low" },
        })}
      />
    );
    expect(screen.getByText("Confidence: low").closest(".MuiChip-root")).toHaveClass(
      "MuiChip-colorError"
    );
  });

  it("keeps the Sources accordion collapsed by default and reveals the cards on expand", async () => {
    const user = setupUser();
    const citations = [
      makeCitation(),
      makeCitation({
        chunk_id: "chunk-2",
        document_name: "sop.docx",
        page_number: null,
      }),
    ];
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "Answer with sources.",
          metadata: { citations },
        })}
      />
    );
    expect(screen.getByText("Sources (2)")).toBeInTheDocument();

    // Collapsed by default: the cards stay hidden inside the Collapse.
    const toggle = screen.getByRole("button", { name: "Expand all sources" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    const firstCard = screen.getByText(/1\. protocol\.pdf \(page 3\)/);
    expect(firstCard.closest(".MuiCollapse-root")).toHaveClass("MuiCollapse-hidden");

    await user.click(toggle);

    expect(
      screen.getByRole("button", { name: "Collapse all sources" })
    ).toHaveAttribute("aria-expanded", "true");
    expect(firstCard.closest(".MuiCollapse-root")).not.toHaveClass(
      "MuiCollapse-hidden"
    );
    expect(screen.getByText(/2\. sop\.docx/)).toBeInTheDocument();
  });

  it("collapses and expands all sources via the global accordion toggle", async () => {
    const user = setupUser();
    const citations = [makeCitation()];
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "Answer with sources.",
          metadata: { citations },
        })}
      />
    );

    const expandToggle = screen.getByRole("button", { name: "Expand all sources" });
    expect(expandToggle).toHaveAttribute("aria-expanded", "false");

    await user.click(expandToggle);

    const collapseToggle = screen.getByRole("button", { name: "Collapse all sources" });
    expect(collapseToggle).toHaveAttribute("aria-expanded", "true");

    await user.click(collapseToggle);
    expect(
      screen.getByRole("button", { name: "Expand all sources" })
    ).toHaveAttribute("aria-expanded", "false");
  });

  it("opens the citation modal when a citation link is clicked and closes it", async () => {
    const user = setupUser();
    const citations = [makeCitation()];
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "See [Source 1] for details.",
          metadata: { citations },
        })}
      />
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

    const citationLink = screen.getByRole("button", {
      name: "protocol.pdf · Inclusion Criteria · p. 3",
    });
    await user.click(citationLink);

    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByText(/Source 1 — protocol\.pdf/)
    ).toBeInTheDocument();
    expect(
      within(dialog).getByText(/Patients aged 18 years or older/)
    ).toBeInTheDocument();

    await user.click(
      within(dialog).getByRole("button", { name: "Close citation detail" })
    );
    await waitFor(() =>
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    );
  });

  it("renders an error message plainly without markdown", () => {
    render(
      <MessageBubble
        message={makeMessage({
          role: "assistant",
          content: "**Something failed**",
          metadata: { error: true },
        })}
      />
    );
    expect(screen.getByText("**Something failed**")).toBeInTheDocument();
    expect(screen.queryByText("Something failed")).not.toBeInTheDocument();
  });
});
