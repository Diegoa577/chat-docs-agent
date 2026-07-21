"use client";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import IconButton from "@mui/material/IconButton";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Box from "@mui/material/Box";
import CloseIcon from "@mui/icons-material/Close";
import ArticleIcon from "@mui/icons-material/Article";
import type { Citation } from "@/lib/api";

interface CitationModalProps {
  citation: Citation | null;
  index: number;
  open: boolean;
  onClose: () => void;
}

export function CitationModal({ citation, index, open, onClose }: CitationModalProps) {
  if (!citation) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="citation-dialog-title"
    >
      <DialogTitle
        id="citation-dialog-title"
        sx={{ display: "flex", alignItems: "center", gap: 1, pr: 6 }}
      >
        <ArticleIcon color="primary" />
        <Box component="span" sx={{ flexGrow: 1, fontWeight: 600 }}>
          Source {index + 1} — {citation.document_name}
        </Box>
        <IconButton
          onClick={onClose}
          aria-label="Close citation detail"
          sx={{
            position: "absolute",
            right: 8,
            top: 8,
            cursor: "pointer",
            color: "text.secondary",
          }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers>
        <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
          {citation.page_number && (
            <Chip label={`Page ${citation.page_number}`} size="small" color="primary" variant="outlined" />
          )}
          {citation.section_title && (
            <Chip label={`Section: ${citation.section_title}`} size="small" variant="outlined" />
          )}
        </Stack>
        <Box
          sx={{
            maxHeight: "60vh",
            overflowY: "auto",
            borderLeft: "3px solid",
            borderColor: "primary.light",
            bgcolor: "action.hover",
            borderRadius: 1,
            p: 2,
          }}
        >
          <Typography
            variant="body2"
            color="text.primary"
            sx={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}
          >
            {citation.excerpt}
          </Typography>
        </Box>
      </DialogContent>
    </Dialog>
  );
}
