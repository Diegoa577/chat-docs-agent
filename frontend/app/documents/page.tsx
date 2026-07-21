"use client";

import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Grid from "@mui/material/Grid2";
import { DocumentUploader } from "@/components/DocumentUploader";
import { DocumentList } from "@/components/DocumentList";
import { useDocuments } from "@/lib/hooks/useDocuments";
import { useAppContext } from "@/context/AppContext";

export default function DocumentsPage() {
  const { documents, isLoading, refresh, remove } = useDocuments();
  const { showSnackbar } = useAppContext();

  const handleUploaded = () => {
    showSnackbar("Document uploaded successfully", "success");
    refresh();
  };

  const handleError = (message: string) => {
    showSnackbar(message, "error");
  };

  const handleDelete = async (id: string) => {
    try {
      await remove(id);
      showSnackbar("Document deleted", "success");
    } catch {
      showSnackbar("Failed to delete document", "error");
    }
  };

  return (
    <Box sx={{ maxWidth: 900 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Documents
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Upload and manage your clinical and regulatory documents. Documents are parsed, chunked,
          and indexed automatically.
        </Typography>

        <Grid container spacing={3}>
          <Grid size={{ xs: 12, md: 5 }}>
            <DocumentUploader onUploaded={handleUploaded} onError={handleError} />
          </Grid>
          <Grid size={{ xs: 12, md: 7 }}>
            <DocumentList
              documents={documents}
              isLoading={isLoading}
              onDelete={handleDelete}
              onDownloadError={handleError}
              onReprocessed={() => {
                showSnackbar("Reprocessing started", "info");
                refresh();
              }}
              onReprocessError={handleError}
            />
          </Grid>
        </Grid>
    </Box>
  );
}
