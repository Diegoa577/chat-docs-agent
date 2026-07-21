"use client";

import { useMemo } from "react";
import ReactMarkdown, { defaultUrlTransform, type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import Typography from "@mui/material/Typography";
import Box from "@mui/material/Box";
import Link from "@mui/material/Link";
import type { Citation } from "@/lib/api";

interface MarkdownContentProps {
  content: string;
  citations?: Citation[];
  onCitationClick?: (sourceIndex: number) => void;
}

/**
 * Converts inline source markers written by the LLM into markdown links so
 * they can be rendered as clickable citation chips.
 * Handles "[Source 2]", "[Sources 1, 2]", "[Source 2, Source 3]", "[2]", "[1, 2]".
 */
export function linkifyCitations(text: string): string {
  return text.replace(
    /\[((?:Sources?\s*)?\d+(?:\s*,\s*(?:Sources?\s*)?\d+)*)\]/gi,
    (match) =>
      (match.match(/\d+/g) ?? [])
        .map((n) => `[Source ${n}](citation:${n})`)
        .join(" ")
  );
}

/**
 * Keeps the custom `citation:N` scheme produced by `linkifyCitations` intact.
 * Without this, react-markdown's default URL transform strips the unknown
 * protocol, the citation link degrades into an empty external link, and
 * clicking it opens the current page in a new tab instead of the modal.
 */
export function allowCitationUrls(url: string): string {
  if (url.startsWith("citation:")) return url;
  return defaultUrlTransform(url);
}

/** Builds "doc name · section · p. N", omitting the parts that are missing. */
export function citationLabel(citation: Citation): string {
  const parts = [citation.document_name];
  if (citation.section_title) parts.push(citation.section_title);
  if (citation.page_number != null) parts.push(`p. ${citation.page_number}`);
  return parts.join(" · ");
}

function buildComponents(
  onCitationClick?: (sourceIndex: number) => void,
  citations?: Citation[]
): Components {
  return {
    p: ({ children }) => (
      <Typography
        variant="body1"
        sx={{ lineHeight: 1.6, mb: 1.5, "&:last-child": { mb: 0 } }}
      >
        {children}
      </Typography>
    ),
    ul: ({ children }) => (
      <Box component="ul" sx={{ pl: 2.5, my: 1 }}>
        {children}
      </Box>
    ),
    ol: ({ children }) => (
      <Box component="ol" sx={{ pl: 2.5, my: 1 }}>
        {children}
      </Box>
    ),
    li: ({ children }) => (
      <Typography component="li" variant="body1" sx={{ lineHeight: 1.6, mb: 0.5 }}>
        {children}
      </Typography>
    ),
    strong: ({ children }) => (
      <Box component="strong" sx={{ fontWeight: 700 }}>
        {children}
      </Box>
    ),
    h1: ({ children }) => (
      <Typography variant="h6" sx={{ mt: 2, mb: 1, fontWeight: 700 }}>
        {children}
      </Typography>
    ),
    h2: ({ children }) => (
      <Typography variant="h6" sx={{ mt: 2, mb: 1, fontWeight: 700 }}>
        {children}
      </Typography>
    ),
    h3: ({ children }) => (
      <Typography variant="subtitle1" sx={{ mt: 1.5, mb: 1, fontWeight: 700 }}>
        {children}
      </Typography>
    ),
    h4: ({ children }) => (
      <Typography variant="subtitle1" sx={{ mt: 1.5, mb: 1, fontWeight: 700 }}>
        {children}
      </Typography>
    ),
    blockquote: ({ children }) => (
      <Box
        component="blockquote"
        sx={{
          m: 0,
          my: 1,
          pl: 1.5,
          borderLeft: "3px solid",
          borderColor: "primary.light",
          color: "text.secondary",
        }}
      >
        {children}
      </Box>
    ),
    code: ({ children, className }) => {
      const isBlock = /language-/.test(className || "");
      if (isBlock) return <code className={className}>{children}</code>;
      // Plain <code> element: valid inline HTML inside <p> (no MUI wrapper).
      return <code className="md-inline-code">{children}</code>;
    },
    pre: ({ children }) => (
      <Box
        component="pre"
        sx={{
          bgcolor: "action.hover",
          borderRadius: 1,
          p: 1.5,
          my: 1,
          overflowX: "auto",
          fontSize: "0.875rem",
          fontFamily: "monospace",
        }}
      >
        {children}
      </Box>
    ),
    a: ({ href, children }) => {
      if (href?.startsWith("citation:")) {
        const n = Number.parseInt(href.slice("citation:".length), 10);
        const citation = citations?.[n - 1];
        const label = citation ? citationLabel(citation) : null;
        return (
          <Box
            component="span"
            role="button"
            tabIndex={0}
            title={label ?? undefined}
            onClick={() => onCitationClick?.(n)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onCitationClick?.(n);
              }
            }}
            sx={{
              display: "inline-block",
              maxWidth: 220,
              overflow: "hidden",
              textOverflow: "ellipsis",
              verticalAlign: "bottom",
              cursor: "pointer",
              color: "primary.main",
              fontWeight: 600,
              fontSize: "0.85em",
              whiteSpace: "nowrap",
              borderBottom: "1px dashed",
              borderColor: "primary.main",
              transition: "color 200ms, border-color 200ms",
              "&:hover": { color: "primary.dark", borderColor: "primary.dark" },
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
                outlineOffset: 1,
                borderRadius: 0.5,
              },
            }}
          >
            {label ?? children}
          </Box>
        );
      }
      return (
        <Link href={href} target="_blank" rel="noopener noreferrer" underline="hover">
          {children}
        </Link>
      );
    },
  };
}

export function MarkdownContent({ content, citations, onCitationClick }: MarkdownContentProps) {
  const components = useMemo(
    () => buildComponents(onCitationClick, citations),
    [onCitationClick, citations]
  );
  const linked = useMemo(() => linkifyCitations(content), [content]);

  return (
    <Box sx={{ overflowWrap: "break-word" }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
        urlTransform={allowCitationUrls}
      >
        {linked}
      </ReactMarkdown>
    </Box>
  );
}
