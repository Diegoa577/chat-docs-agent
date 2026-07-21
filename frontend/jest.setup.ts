import "@testing-library/jest-dom";

// jsdom does not provide TextEncoder/TextDecoder; streamChat and its tests
// rely on them (Node's `util` implementations are spec-compatible).
import { TextDecoder, TextEncoder } from "util";
import { ReadableStream, TransformStream, WritableStream } from "stream/web";

if (typeof global.TextEncoder === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).TextEncoder = TextEncoder;
}
if (typeof global.TextDecoder === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).TextDecoder = TextDecoder;
}

// Web streams are not implemented by jsdom; streamChat and the NDJSON test
// helpers rely on them (Node's stream/web implementations are spec-compliant).
if (typeof global.ReadableStream === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).ReadableStream = ReadableStream;
}
if (typeof global.WritableStream === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).WritableStream = WritableStream;
}
if (typeof global.TransformStream === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (global as any).TransformStream = TransformStream;
}

// Apply the manual mock in __mocks__/next/navigation.ts to every test file.
// Tests override behaviour via e.g.
//   (usePathname as jest.Mock).mockReturnValue("/documents");
jest.mock("next/navigation");

// MUI responsive components may rely on matchMedia in some code paths.
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => undefined,
      removeListener: () => undefined,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
      dispatchEvent: () => false,
    }) as MediaQueryList;
}

// MUI components frequently schedule state updates (ripple, transitions, form
// control state) that outlive the synchronous React event batch. These are
// benign in tests but noisy. Swallow the well-known act() warning so the suite
// output stays readable; real failures still surface through assertions.
const originalError = console.error;
console.error = (...args: unknown[]) => {
  const first = typeof args[0] === "string" ? args[0] : "";
  if (
    /^Warning: An update to .* inside a test was not wrapped in act/.test(first)
  ) {
    return;
  }
  originalError(...args);
};
