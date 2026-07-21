"use client";

import { useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import DeleteIcon from "@mui/icons-material/Delete";
import DownloadIcon from "@mui/icons-material/Download";
import RefreshIcon from "@mui/icons-material/Refresh";
import ArticleIcon from "@mui/icons-material/Article";
import CircularProgress from "@mui/material/CircularProgress";
import { downloadDocument, reprocessDocument, type Document } from "@/lib/api";
import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog";

interface DocumentCardProps {
  document: Document;
  onDelete: (id: string) => void;
  onDownloadError?: (message: string) => void;
  onReprocessed?: () => void;
  onReprocessError?: (message: string) => void;
}

export function DocumentCard({
  document,
  onDelete,
  onDownloadError,
  onReprocessed,
  onReprocessError,
}: DocumentCardProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await downloadDocument(document);
    } catch {
      onDownloadError?.("Failed to download document");
    } finally {
      setIsDownloading(false);
    }
  };

  const handleReprocess = async () => {
    setIsRetrying(true);
    try {
      await reprocessDocument(document.id);
      // Let the parent refresh the list (restarts status polling).
      onReprocessed?.();
    } catch {
      onReprocessError?.("Failed to reprocess document");
    } finally {
      setIsRetrying(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onDelete(document.id);
    } finally {
      setIsDeleting(false);
      setConfirmOpen(false);
    }
  };

  const statusConfig = {
    pending: { color: "default" as const, label: "Pending", showProgress: true },
    processing: { color: "warning" as const, label: "Processing", showProgress: true },
    completed: { color: "success" as const, label: "Ready", showProgress: false },
    failed: { color: "error" as const, label: "Failed", showProgress: false },
  };

  const config = statusConfig[document.status];

  return (
    <Card variant="outlined" sx={{ borderRadius: 2 }}>
      <CardContent sx={{ display: "flex", alignItems: "center", gap: 2, py: 1.5, px: 2 }}>
        <ArticleIcon color="primary" />
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" noWrap title={document.filename}>
            {document.filename}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {new Date(document.created_at).toLocaleString()}
          </Typography>
          {document.error_message && (
            <Typography variant="caption" color="error.main" display="block">
              {document.error_message}
            </Typography>
          )}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexShrink: 0 }}>
          {config.showProgress && <CircularProgress size={18} thickness={5} />}
          <Chip label={config.label} size="small" color={config.color} />
          {document.status === "failed" && (
            <Tooltip title="Retry processing">
              <IconButton
                size="small"
                onClick={handleReprocess}
                disabled={isRetrying}
                aria-label={`Retry processing ${document.filename}`}
              >
                {isRetrying ? (
                  <CircularProgress size={18} thickness={5} />
                ) : (
                  <RefreshIcon fontSize="small" />
                )}
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title="Download document">
            <IconButton
              size="small"
              onClick={handleDownload}
              disabled={isDownloading}
              aria-label={`Download ${document.filename}`}
            >
              <DownloadIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Delete document">
            <IconButton
              size="small"
              onClick={() => setConfirmOpen(true)}
              disabled={isDeleting}
              aria-label={`Delete ${document.filename}`}
              color="error"
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </CardContent>
      <ConfirmDeleteDialog
        open={confirmOpen}
        title="Delete document?"
        itemName={document.filename}
        description="This action cannot be undone. The document and its indexed chunks will be permanently removed."
        isDeleting={isDeleting}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={handleDelete}
      />
    </Card>
  );
}
