"use client";

import { useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import IconButton from "@mui/material/IconButton";
import Collapse from "@mui/material/Collapse";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ArticleIcon from "@mui/icons-material/Article";
import type { Citation } from "@/lib/api";

interface CitationCardProps {
  citation: Citation;
  index: number;
}

export function CitationCard({ citation, index }: CitationCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card
      variant="outlined"
      sx={{
        borderRadius: 2,
        bgcolor: "background.paper",
        borderColor: "divider",
      }}
    >
      <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography
          variant="subtitle2"
          component="div"
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1,
            color: "text.primary",
            fontWeight: 600,
          }}
        >
          <ArticleIcon fontSize="small" color="primary" />
          {index + 1}. {citation.document_name}
          {citation.page_number != null && ` (page ${citation.page_number})`}
          <IconButton
            size="small"
            onClick={() => setExpanded((prev) => !prev)}
            aria-label={expanded ? "Hide citation excerpt" : "Show citation excerpt"}
            sx={{ ml: "auto" }}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Typography>
        {citation.section_title && (
          <Typography variant="caption" color="text.secondary" sx={{ ml: 4 }}>
            Section: {citation.section_title}
          </Typography>
        )}
        <Collapse in={expanded}>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{
              mt: 1,
              ml: 4,
              fontStyle: "italic",
              borderLeft: "3px solid",
              borderColor: "primary.light",
              pl: 1.5,
            }}
          >
            &ldquo;{citation.excerpt}&rdquo;
          </Typography>
        </Collapse>
      </CardContent>
    </Card>
  );
}
