"use client";

import { useCallback, useEffect, useState } from "react";
import { deleteDocument, listDocuments, type Document } from "@/lib/api";
import { POLLING_INTERVAL_MS } from "@/lib/constants";

export interface UseDocumentsReturn {
  documents: Document[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load documents";
      setError(message);
      console.error(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const remove = useCallback(async (id: string) => {
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((doc) => doc.id !== id));
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete document";
      setError(message);
      console.error(message);
      throw err;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const hasActive = documents.some(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );
    if (!hasActive) return;

    const interval = setInterval(() => {
      refresh();
    }, POLLING_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [documents, refresh]);

  return { documents, isLoading, error, refresh, remove };
}
