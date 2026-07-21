export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const POLLING_INTERVAL_MS = 2000;

// Mirrors the backend `max_upload_size_mb` setting (the backend remains the
// authority and returns HTTP 413 above this limit).
export const MAX_UPLOAD_SIZE_MB = 50;
