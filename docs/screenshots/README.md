# Screenshots

Demo screenshots referenced by the root [README.md](../../README.md) in the **Screenshots & Demo** section,
captured against the running stack at 1440x900 with the 6 seeded documents in `completed` status.

| File | What it shows |
|---|---|
| `01-dashboard.png` | Dashboard with document/conversation stats and the backend status pill |
| `02-documents.png` | Documents page: drag & drop uploader + status transitions |
| `03-chat-streaming.png` | Chat answer streaming with confidence / intent / model chips |
| `04-citations.png` | Inline citation chips + citation modal with the source excerpt |
| `05-compare.png` | Multi-document comparison answer |
| `06-strict-mode.png` | Strict mode refusing a low-confidence answer |
| `07-provider-model.png` | LLM provider / model selectors in the chat input |
| `08-metrics.png` | `/ready` JSON and/or Prometheus output at `/metrics` |

Tips: run the full stack with `docker-compose up --build -d` and wait for the 6 seeded
documents to reach `completed` before capturing. A working LLM provider is needed for the
chat shots.
