"use client";

import { notFound, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Button from "@mui/material/Button";
import Link from "next/link";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import DownloadIcon from "@mui/icons-material/Download";
import { ApiError, downloadDocument, getDocument, type Document } from "@/lib/api";

export default function DocumentDetailPage() {
  const params = useParams<{ documentId: string }>();
  const [document, setDocument] = useState<Document | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    if (!document) return;
    setIsDownloading(true);
    try {
      await downloadDocument(document);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to download document");
    } finally {
      setIsDownloading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    getDocument(params.documentId)
      .then((doc) => {
        if (!cancelled) setDocument(doc);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load document");
          setErrorStatus(err instanceof ApiError ? err.status ?? null : null);
        }
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [params.documentId]);

  // A document that does not exist renders the nearest not-found boundary.
  // notFound() must be called during render, not in an effect or callback.
  if (errorStatus === 404) {
    notFound();
  }

  return (
    <Box sx={{ maxWidth: 800 }}>
        <Button component={Link} href="/documents" startIcon={<ArrowBackIcon />} sx={{ mb: 2 }}>
          Back to documents
        </Button>
        {document && (
          <Button
            variant="contained"
            startIcon={<DownloadIcon />}
            onClick={handleDownload}
            disabled={isDownloading}
            sx={{ mb: 2, ml: 1 }}
          >
            {isDownloading ? "Downloading..." : "Download"}
          </Button>
        )}
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Document detail
        </Typography>

        {isLoading && <Typography color="text.secondary">Loading...</Typography>}
        {error && <Typography color="error.main">{error}</Typography>}

        {document && (
          <Card>
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>
                {document.filename}
              </Typography>
              <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
                <Chip
                  label={document.status}
                  color={
                    document.status === "completed"
                      ? "success"
                      : document.status === "failed"
                      ? "error"
                      : document.status === "processing"
                      ? "warning"
                      : "default"
                  }
                />
                <Chip label={document.content_type} variant="outlined" />
              </Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                <strong>ID:</strong> {document.id}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                <strong>Created:</strong> {new Date(document.created_at).toLocaleString()}
              </Typography>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                <strong>Updated:</strong> {new Date(document.updated_at).toLocaleString()}
              </Typography>
              {document.error_message && (
                <Typography variant="body2" color="error.main" sx={{ mt: 2 }}>
                  <strong>Error:</strong> {document.error_message}
                </Typography>
              )}
              {document.metadata && Object.keys(document.metadata).length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" fontWeight={600}>
                    Metadata
                  </Typography>
                  <pre style={{ whiteSpace: "pre-wrap", fontSize: "0.85rem" }}>
                    {JSON.stringify(document.metadata, null, 2)}
                  </pre>
                </Box>
              )}
            </CardContent>
          </Card>
        )}
    </Box>
  );
}
