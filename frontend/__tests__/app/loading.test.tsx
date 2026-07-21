import Loading from "@/app/loading";
import { render, screen } from "../test-utils";

describe("Loading (app/loading.tsx)", () => {
  it("renders a centered progress indicator", () => {
    render(<Loading />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
  });
});
