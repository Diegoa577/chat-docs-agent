"use client";

import { ConfirmDeleteDialog } from "./ConfirmDeleteDialog";

interface DeleteConversationDialogProps {
  open: boolean;
  conversationTitle: string;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function DeleteConversationDialog({
  open,
  conversationTitle,
  isDeleting,
  onCancel,
  onConfirm,
}: DeleteConversationDialogProps) {
  return (
    <ConfirmDeleteDialog
      open={open}
      title="Delete conversation?"
      itemName={conversationTitle}
      description="This action cannot be undone. All messages in this conversation will be permanently removed."
      isDeleting={isDeleting}
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
}
