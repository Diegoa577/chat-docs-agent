"use client";

import Snackbar from "@mui/material/Snackbar";
import Alert from "@mui/material/Alert";
import { useAppContext } from "@/context/AppContext";

export function SnackbarContainer() {
  const { snackbars, closeSnackbar } = useAppContext();

  return (
    <>
      {snackbars.map((snackbar) => (
        <Snackbar
          key={snackbar.id}
          open
          autoHideDuration={6000}
          onClose={() => closeSnackbar(snackbar.id)}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        >
          <Alert
            severity={snackbar.severity}
            variant="filled"
            onClose={() => closeSnackbar(snackbar.id)}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
}
