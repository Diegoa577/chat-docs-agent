import { API_URL } from "./constants";

export interface Document {
  id: string;
  filename: string;
  content_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  metadata: Record<string, unknown>;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number: number | null;
  section_title: string | null;
  excerpt: string;
}

export type ChatStreamMetadataEvent = {
  type: "metadata";
  conversation_id: string;
  intent: string;
  confidence: string;
  model: string;
  citations: Citation[];
  strict_mode_applied: boolean;
};

export type ChatStreamChunkEvent = {
  type: "chunk";
  conversation_id: string;
  content: string;
};

type ChatStreamDoneEvent = {
  type: "done";
  conversation_id: string;
};

type ChatStreamErrorEvent = {
  type: "error";
  detail: string;
};

export type ChatStreamEvent =
  | ChatStreamMetadataEvent
  | ChatStreamChunkEvent
  | ChatStreamDoneEvent
  | ChatStreamErrorEvent;

export interface Message {
  role: "user" | "assistant";
  content: string;
  metadata?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  messages: Message[];
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface LLMModelInfo {
  id: string;
  display_name: string;
  default_temperature: number;
  supports_json_mode: boolean;
}

export interface LLMProviderInfo {
  id: string;
  display_name: string;
  models: LLMModelInfo[];
}

export interface LLMProvidersResponse {
  providers: LLMProviderInfo[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public detail?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = "Request failed";
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(detail, response.status, detail);
  }
  return response.json() as Promise<T>;
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_URL}/documents`, {
    method: "POST",
    body: formData,
  });

  return handleResponse<Document>(response);
}

export async function listDocuments(): Promise<Document[]> {
  const response = await fetch(`${API_URL}/documents`);
  const data = await handleResponse<{ documents: Document[] }>(response);
  return data.documents;
}

export async function getDocument(id: string): Promise<Document> {
  const response = await fetch(`${API_URL}/documents/${id}`);
  return handleResponse<Document>(response);
}

export async function deleteDocument(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/documents/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await handleResponse<never>(response);
  }
}

export async function reprocessDocument(id: string): Promise<Document> {
  const response = await fetch(`${API_URL}/documents/${id}/reprocess`, {
    method: "POST",
  });
  return handleResponse<Document>(response);
}

export async function downloadDocument(document: Document): Promise<void> {
  const response = await fetch(`${API_URL}/documents/${document.id}/download`);
  if (!response.ok) {
    await handleResponse<never>(response);
  }
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  const serverFilename = disposition?.match(/filename="?([^";]+)"?/)?.[1];
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = serverFilename ?? document.filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function listConversations(): Promise<Conversation[]> {
  const response = await fetch(`${API_URL}/conversations`);
  const data = await handleResponse<{ conversations: Conversation[] }>(response);
  return data.conversations;
}

export async function getConversation(id: string): Promise<Conversation> {
  const response = await fetch(`${API_URL}/conversations/${id}`);
  return handleResponse<Conversation>(response);
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await fetch(`${API_URL}/conversations/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    await handleResponse<never>(response);
  }
}

export async function getLLMProviders(): Promise<LLMProviderInfo[]> {
  const response = await fetch(`${API_URL}/providers/llm`);
  const data = await handleResponse<LLMProvidersResponse>(response);
  return data.providers;
}

interface StreamChatParams {
  question: string;
  conversationId?: string;
  strictMode?: boolean;
  provider?: string;
  model?: string;
}

export async function streamChat(
  params: StreamChatParams,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
    },
    body: JSON.stringify({
      question: params.question,
      conversation_id: params.conversationId,
      strict_mode: params.strictMode ?? false,
      provider: params.provider,
      model: params.model,
    }),
    signal,
  });

  if (!response.ok) {
    let detail = "Failed to start chat stream";
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = response.statusText;
    }
    throw new ApiError(detail, response.status, detail);
  }

  if (!response.body) {
    throw new ApiError("No response body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const event = JSON.parse(trimmed) as ChatStreamEvent;
          onEvent(event);
        } catch (parseErr) {
          console.error("Failed to parse stream line:", trimmed, parseErr);
        }
      }
    }

    if (buffer.trim()) {
      try {
        const event = JSON.parse(buffer.trim()) as ChatStreamEvent;
        onEvent(event);
      } catch (parseErr) {
        console.error("Failed to parse final stream buffer:", buffer, parseErr);
      }
    }
  } finally {
    reader.releaseLock();
  }
}
