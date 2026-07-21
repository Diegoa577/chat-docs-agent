"use client";

import Link from "next/link";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";

export default function NotFound() {
  return (
    <Box sx={{ textAlign: "center", mt: 8 }}>
        <Typography variant="h1" fontWeight={700} color="primary.main">
          404
        </Typography>
        <Typography variant="h5" fontWeight={600} gutterBottom>
          Page not found
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          The page you are looking for does not exist.
        </Typography>
        <Button component={Link} href="/" variant="contained">
          Go to dashboard
        </Button>
    </Box>
  );
}
