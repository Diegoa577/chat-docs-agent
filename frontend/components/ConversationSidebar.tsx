"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import Tooltip from "@mui/material/Tooltip";
import AddIcon from "@mui/icons-material/Add";
import ChatBubbleIcon from "@mui/icons-material/ChatBubble";
import DeleteIcon from "@mui/icons-material/Delete";
import { DeleteConversationDialog } from "@/components/DeleteConversationDialog";
import type { Conversation } from "@/lib/api";

interface ConversationSidebarProps {
  conversations: Conversation[];
  isLoading?: boolean;
  onDelete?: (conversationId: string) => void | Promise<void>;
}

export function ConversationSidebar({ conversations, isLoading, onDelete }: ConversationSidebarProps) {
  const pathname = usePathname();
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const sorted = useMemo(() => {
    return [...conversations].sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    );
  }, [conversations]);

  const getTitle = (conversation: Conversation) => {
    const firstUser = conversation.messages.find((m) => m.role === "user");
    if (firstUser) {
      return firstUser.content.length > 40
        ? `${firstUser.content.slice(0, 40)}...`
        : firstUser.content;
    }
    return `Conversation ${conversation.id.slice(0, 8)}`;
  };

  return (
    <Box sx={{ p: 2 }}>
      <Button
        component={Link}
        href="/chat"
        fullWidth
        variant="contained"
        startIcon={<AddIcon />}
        sx={{ mb: 2 }}
      >
        New conversation
      </Button>

      <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ px: 1, mb: 1, display: "block" }}>
        Recent conversations
      </Typography>

      {isLoading ? (
        <Typography variant="body2" color="text.secondary" sx={{ px: 1 }}>
          Loading...
        </Typography>
      ) : sorted.length === 0 ? (
        <Typography variant="body2" color="text.secondary" sx={{ px: 1 }}>
          No conversations yet.
        </Typography>
      ) : (
        <List dense disablePadding>
          {sorted.map((conversation) => {
            const href = `/chat/${conversation.id}`;
            const active = pathname === href;
            return (
              <ListItem
                key={conversation.id}
                disablePadding
                sx={{
                  "& .delete-button": {
                    opacity: 0,
                    transition: "opacity 150ms",
                  },
                  "&:hover .delete-button, & .delete-button:focus-visible": {
                    opacity: 1,
                  },
                }}
              >
                <ListItemButton
                  component={Link}
                  href={href}
                  selected={active}
                  sx={{
                    borderRadius: 2,
                    mb: 0.5,
                    pr: 6,
                    "&.Mui-selected": {
                      bgcolor: "action.selected",
                    },
                  }}
                >
                  <ChatBubbleIcon
                    fontSize="small"
                    sx={{ mr: 1, color: "text.secondary", flexShrink: 0 }}
                  />
                  <ListItemText
                    primary={getTitle(conversation)}
                    secondary={new Date(conversation.updated_at).toLocaleString()}
                    primaryTypographyProps={{
                      noWrap: true,
                      fontSize: "0.875rem",
                    }}
                    secondaryTypographyProps={{
                      noWrap: true,
                      fontSize: "0.7rem",
                    }}
                  />
                </ListItemButton>
                {onDelete && (
                  <Tooltip title="Delete conversation">
                    <IconButton
                      className="delete-button"
                      size="small"
                      color="error"
                      aria-label="Delete conversation"
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        setPendingDelete(conversation);
                      }}
                      sx={{
                        position: "absolute",
                        right: 8,
                        top: "50%",
                        transform: "translateY(-50%)",
                      }}
                    >
                      <DeleteIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                )}
              </ListItem>
            );
          })}
        </List>
      )}

      <DeleteConversationDialog
        open={pendingDelete !== null}
        conversationTitle={pendingDelete ? getTitle(pendingDelete) : ""}
        isDeleting={isDeleting}
        onCancel={() => setPendingDelete(null)}
        onConfirm={() => {
          if (!pendingDelete || !onDelete) return;
          setIsDeleting(true);
          Promise.resolve(onDelete(pendingDelete.id)).finally(() => {
            setIsDeleting(false);
            setPendingDelete(null);
          });
        }}
      />
    </Box>
  );
}
