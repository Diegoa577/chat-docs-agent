"use client";

import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import { DocumentCard } from "./DocumentCard";
import type { Document } from "@/lib/api";

interface DocumentListProps {
  documents: Document[];
  isLoading?: boolean;
  onDelete: (id: string) => void;
  onDownloadError?: (message: string) => void;
  onReprocessed?: () => void;
  onReprocessError?: (message: string) => void;
}

export function DocumentList({
  documents,
  isLoading,
  onDelete,
  onDownloadError,
  onReprocessed,
  onReprocessError,
}: DocumentListProps) {
  if (isLoading && documents.length === 0) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (documents.length === 0) {
    return (
      <Box
        sx={{
          textAlign: "center",
          py: 4,
          border: "1px dashed",
          borderColor: "divider",
          borderRadius: 2,
        }}
      >
        <Typography variant="body1" color="text.secondary">
          No documents uploaded yet.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a document to start asking questions.
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={1.5}>
      {documents.map((doc) => (
        <DocumentCard
          key={doc.id}
          document={doc}
          onDelete={onDelete}
          onDownloadError={onDownloadError}
          onReprocessed={onReprocessed}
          onReprocessError={onReprocessError}
        />
      ))}
    </Stack>
  );
}
