"use client";

import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import DialogActions from "@mui/material/DialogActions";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import CircularProgress from "@mui/material/CircularProgress";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DeleteIcon from "@mui/icons-material/Delete";

interface ConfirmDeleteDialogProps {
  open: boolean;
  /** Dialog heading, e.g. "Delete conversation?" */
  title: string;
  /** Name of the item being deleted, rendered quoted and bold. */
  itemName: string;
  /** Consequence text shown below the item name. */
  description: string;
  isDeleting: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDeleteDialog({
  open,
  title,
  itemName,
  description,
  isDeleting,
  onCancel,
  onConfirm,
}: ConfirmDeleteDialogProps) {
  return (
    <Dialog
      open={open}
      onClose={(_event, reason) => {
        if (isDeleting && (reason === "backdropClick" || reason === "escapeKeyDown")) return;
        onCancel();
      }}
      fullWidth
      maxWidth="xs"
      aria-labelledby="confirm-delete-dialog-title"
      aria-describedby="confirm-delete-dialog-description"
      PaperProps={{
        sx: {
          borderRadius: 3,
          boxShadow: "0 8px 30px rgba(15, 23, 42, 0.12), 0 2px 8px rgba(15, 23, 42, 0.08)",
        },
      }}
    >
      <DialogTitle
        id="confirm-delete-dialog-title"
        sx={{ display: "flex", alignItems: "center", gap: 1.5, pb: 1 }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            width: 40,
            height: 40,
            borderRadius: "50%",
            bgcolor: "error.light",
            color: "error.main",
            flexShrink: 0,
          }}
        >
          <DeleteOutlineIcon />
        </Box>
        <Typography variant="h6" component="span" fontWeight={600}>
          {title}
        </Typography>
      </DialogTitle>
      <DialogContent>
        <Typography
          id="confirm-delete-dialog-description"
          variant="body2"
          color="text.primary"
          sx={{ mb: 1 }}
        >
          You are about to delete{" "}
          <Box component="span" fontWeight={600}>
            &ldquo;{itemName}&rdquo;
          </Box>
          .
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2.5, gap: 1 }}>
        <Button
          variant="outlined"
          color="inherit"
          onClick={onCancel}
          disabled={isDeleting}
          autoFocus
          sx={{ cursor: "pointer", color: "text.secondary", borderColor: "divider" }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={onConfirm}
          disabled={isDeleting}
          startIcon={
            isDeleting ? <CircularProgress size={18} color="inherit" /> : <DeleteIcon />
          }
          sx={{ cursor: "pointer", minWidth: 110 }}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
