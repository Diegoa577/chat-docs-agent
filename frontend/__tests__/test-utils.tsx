/**
 * Shared test utilities: render wrappers, fixture factories and fetch/stream
 * helpers. Import from every test file instead of @testing-library/react:
 *
 *   import { render, screen, makeDocument } from "../test-utils";
 */
import React, { type ReactElement, type ReactNode } from "react";
import {
  render as rtlRender,
  type RenderOptions,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider } from "@mui/material/styles";
import { createTheme } from "@mui/material/styles";
import appTheme from "@/lib/theme";
import { AppProvider } from "@/context/AppContext";
import { ChatProvider } from "@/context/ChatContext";
import type {
  Citation,
  ChatStreamEvent,
  Conversation,
  Document,
  LLMProviderInfo,
  Message,
} from "@/lib/api";

// ---------------------------------------------------------------------------
// Fixture factories
// ---------------------------------------------------------------------------

export function makeDocument(overrides: Partial<Document> = {}): Document {
  return {
    id: "doc-1",
    filename: "protocol.pdf",
    content_type: "application/pdf",
    status: "completed",
    metadata: {},
    error_message: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    role: "user",
    content: "Hello",
    ...overrides,
  };
}

export function makeConversation(
  overrides: Partial<Conversation> = {}
): Conversation {
  return {
    id: "conv-1",
    messages: [makeMessage()],
    metadata: {},
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeCitation(overrides: Partial<Citation> = {}): Citation {
  return {
    chunk_id: "chunk-1",
    document_id: "doc-1",
    document_name: "protocol.pdf",
    page_number: 3,
    section_title: "Inclusion Criteria",
    excerpt: "Patients aged 18 years or older...",
    ...overrides,
  };
}

export function makeProvider(
  overrides: Partial<LLMProviderInfo> = {}
): LLMProviderInfo {
  return {
    id: "openai",
    display_name: "OpenAI",
    models: [
      {
        id: "gpt-5.4-mini",
        display_name: "GPT-5.4 mini",
        default_temperature: 0.2,
        supports_json_mode: false,
      },
      {
        id: "gpt-5.4",
        display_name: "GPT-5.4",
        default_temperature: 0.2,
        supports_json_mode: false,
      },
    ],
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Render wrappers
// ---------------------------------------------------------------------------

interface WrapperOptions {
  withAppProvider?: boolean;
  withChatProvider?: boolean;
}

function buildWrapper({ withAppProvider, withChatProvider }: WrapperOptions) {
  return function Wrapper({ children }: { children: ReactNode }) {
    let node = children;
    // ChatProvider is independent from AppProvider; order does not matter,
    // but keep nesting stable so tests can rely on it.
    if (withChatProvider) node = <ChatProvider>{node}</ChatProvider>;
    if (withAppProvider) node = <AppProvider>{node}</AppProvider>;
    return <>{node}</>;
  };
}

/**
 * render() with the requested context providers.
 * Defaults to NO providers — opt in per test:
 *   renderWithProviders(<ChatInput ... />, { withChatProvider: true })
 */
const testTheme = createTheme({
  ...appTheme,
  components: {
    ...appTheme.components,
    MuiButtonBase: {
      defaultProps: {
        disableRipple: true,
      },
    },
    MuiCollapse: {
      defaultProps: {
        timeout: 0,
      },
    },
  },
});

function ThemeWrapper({ children }: { children: ReactNode }) {
  return <ThemeProvider theme={testTheme}>{children}</ThemeProvider>;
}

export function render(
  ui: ReactElement,
  options: Omit<RenderOptions, "wrapper"> = {}
) {
  return rtlRender(ui, {
    wrapper: ThemeWrapper,
    ...options,
  });
}

export function renderWithProviders(
  ui: ReactElement,
  options: WrapperOptions & Omit<RenderOptions, "wrapper"> = {}
) {
  const { withAppProvider, withChatProvider, ...renderOptions } = options;
  // Call rtlRender directly: the local render() above omits "wrapper" from its
  // options type, so passing one here would not type-check.
  return rtlRender(ui, {
    wrapper: buildWrapper({ withAppProvider, withChatProvider }),
    ...renderOptions,
  });
}

// ---------------------------------------------------------------------------
// fetch / streaming helpers
// ---------------------------------------------------------------------------

/** Builds a minimal Response-like object for mocked fetch calls. */
export function mockFetchResponse(
  body: unknown,
  init: { ok?: boolean; status?: number; statusText?: string } = {}
): Response {
  const { ok = true, status = 200, statusText = "OK" } = init;
  return {
    ok,
    status,
    statusText,
    json: () => Promise.resolve(body),
    blob: () => Promise.resolve(new Blob()),
  } as unknown as Response;
}

/**
 * Builds a fetch Response whose body is an NDJSON ReadableStream containing
 * the given events. If `chunkedAt` is provided, the encoded payload is split
 * into byte chunks at those offsets to exercise partial-line buffering.
 */
export function ndjsonStreamResponse(
  events: (ChatStreamEvent | string)[],
  chunkedAt?: number[]
): Response {
  const payload =
    events
      .map((e) => (typeof e === "string" ? e : JSON.stringify(e)))
      .join("\n") + "\n";
  const bytes = new TextEncoder().encode(payload);

  const chunks: Uint8Array[] = [];
  if (chunkedAt && chunkedAt.length > 0) {
    let prev = 0;
    for (const at of [...chunkedAt, bytes.length]) {
      chunks.push(bytes.slice(prev, at));
      prev = at;
    }
  } else {
    chunks.push(bytes);
  }

  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(chunk);
      controller.close();
    },
  });

  return {
    ok: true,
    status: 200,
    statusText: "OK",
    body: stream,
    json: () => Promise.reject(new Error("no json on stream")),
  } as unknown as Response;
}

/** Convenience: userEvent.setup for tests that use real timers (default). */
export function setupUser() {
  return userEvent.setup();
}

/** Convenience: userEvent.setup for tests that enable jest fake timers. */
export function setupUserWithFakeTimers() {
  return userEvent.setup({
    advanceTimers: (delay: number) => jest.advanceTimersByTime(delay),
  });
}

// Re-export RTL so test files only need this module.
export {
  act,
  cleanup,
  fireEvent,
  renderHook,
  screen,
  waitFor,
  within,
  type RenderOptions,
} from "@testing-library/react";
export { userEvent };
