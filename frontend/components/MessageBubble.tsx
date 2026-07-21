"use client";

import { useState } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Collapse from "@mui/material/Collapse";
import IconButton from "@mui/material/IconButton";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import PersonIcon from "@mui/icons-material/Person";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ArticleIcon from "@mui/icons-material/Article";
import type { Citation, Message } from "@/lib/api";
import { CitationCard } from "./CitationCard";
import { CitationModal } from "./CitationModal";
import { MarkdownContent } from "./MarkdownContent";

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const [openCitationIndex, setOpenCitationIndex] = useState<number | null>(null);
  const [sourcesExpanded, setSourcesExpanded] = useState(false);
  const isUser = message.role === "user";
  const metadata = message.metadata || {};
  const isStreaming = metadata.isStreaming === true;
  const citations = (metadata.citations as Citation[]) || [];
  const confidence = metadata.confidence as string | undefined;
  const model = metadata.model as string | undefined;
  const intent = metadata.intent as string | undefined;
  const strictModeApplied = metadata.strict_mode_applied === true;
  const hasError = metadata.error === true;

  const confidenceColor =
    confidence === "high"
      ? "success"
      : confidence === "medium"
      ? "warning"
      : confidence === "low"
      ? "error"
      : "default";

  const handleCitationClick = (sourceIndex: number) => {
    if (sourceIndex >= 1 && sourceIndex <= citations.length) {
      setOpenCitationIndex(sourceIndex - 1);
    }
  };

  const streamingCursor = (
    <Box
      component="span"
      sx={{
        display: "inline-block",
        width: "0.5em",
        height: "1em",
        ml: 0.5,
        bgcolor: "primary.main",
        animation: "blink 1s step-end infinite",
        "@keyframes blink": {
          "0%, 100%": { opacity: 1 },
          "50%": { opacity: 0 },
        },
      }}
    />
  );

  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        mb: 2,
      }}
    >
      <Paper
        elevation={0}
        sx={{
          maxWidth: { xs: "92%", md: "80%" },
          p: 2,
          borderRadius: 3,
          bgcolor: isUser ? "primary.main" : "background.paper",
          color: isUser ? "primary.contrastText" : "text.primary",
          border: isUser ? "none" : "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="row" spacing={1} alignItems="center" mb={1}>
          {isUser ? (
            <PersonIcon fontSize="small" />
          ) : (
            <SmartToyIcon fontSize="small" />
          )}
          <Typography variant="caption" fontWeight={600}>
            {isUser ? "You" : "Assistant"}
          </Typography>
        </Stack>

        {isUser || hasError ? (
          <Typography
            variant="body1"
            sx={{
              whiteSpace: "pre-wrap",
              lineHeight: 1.6,
              color: hasError ? "error.main" : "inherit",
            }}
          >
            {message.content}
            {isStreaming && streamingCursor}
          </Typography>
        ) : (
          <Box>
            <MarkdownContent
              content={message.content}
              citations={citations}
              onCitationClick={handleCitationClick}
            />
            {isStreaming && streamingCursor}
          </Box>
        )}

        <CitationModal
          citation={openCitationIndex !== null ? citations[openCitationIndex] : null}
          index={openCitationIndex ?? 0}
          open={openCitationIndex !== null}
          onClose={() => setOpenCitationIndex(null)}
        />

        {!isUser && citations.length > 0 && (
          <Box
            sx={{
              mt: 2,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2,
            }}
          >
            <Box
              role="button"
              tabIndex={0}
              aria-expanded={sourcesExpanded}
              aria-label={sourcesExpanded ? "Collapse all sources" : "Expand all sources"}
              onClick={() => setSourcesExpanded((prev) => !prev)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSourcesExpanded((prev) => !prev);
                }
              }}
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                px: 1.5,
                py: 0.5,
                cursor: "pointer",
                borderBottom: sourcesExpanded ? "1px solid" : "none",
                borderColor: "divider",
                "&:focus-visible": {
                  outline: "2px solid",
                  outlineColor: "primary.main",
                  outlineOffset: -2,
                },
              }}
            >
              <ArticleIcon fontSize="small" color="primary" />
              <Typography variant="caption" fontWeight={600} color="text.secondary">
                Sources ({citations.length})
              </Typography>
              <IconButton
                size="small"
                aria-hidden
                tabIndex={-1}
                sx={{ ml: "auto", pointerEvents: "none" }}
              >
                {sourcesExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
              </IconButton>
            </Box>
            <Collapse in={sourcesExpanded}>
              <Stack spacing={1} sx={{ p: 1.5 }}>
                {citations.map((citation, idx) => (
                  <CitationCard key={citation.chunk_id} citation={citation} index={idx} />
                ))}
              </Stack>
            </Collapse>
          </Box>
        )}

        {!isUser && (confidence || model || intent) && !isStreaming && (
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mt: 2 }}>
            {confidence && (
              <Chip
                label={`Confidence: ${confidence}`}
                size="small"
                color={confidenceColor as "success" | "warning" | "error" | "default"}
                variant="outlined"
              />
            )}
            {intent && (
              <Chip label={`Intent: ${intent}`} size="small" variant="outlined" />
            )}
            {model && (
              <Chip label={`Model: ${model}`} size="small" variant="outlined" />
            )}
            {strictModeApplied && (
              <Chip
                label="Strict mode applied"
                size="small"
                color="warning"
                variant="outlined"
              />
            )}
          </Stack>
        )}
      </Paper>
    </Box>
  );
}
