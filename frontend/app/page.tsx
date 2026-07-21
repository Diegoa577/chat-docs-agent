"use client";

import Link from "next/link";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import { alpha } from "@mui/material/styles";
import FolderIcon from "@mui/icons-material/Folder";
import ChatIcon from "@mui/icons-material/Chat";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { useDocuments } from "@/lib/hooks/useDocuments";
import { useConversations } from "@/lib/hooks/useConversations";

export default function DashboardPage() {
  const { documents, isLoading: docsLoading } = useDocuments();
  const { conversations, isLoading: convLoading } = useConversations();

  const readyDocs = documents.filter((d) => d.status === "completed").length;

  const stats = [
    {
      title: "Documents",
      value: documents.length,
      subtitle: `${readyDocs} ready`,
      icon: FolderIcon,
      href: "/documents",
      color: "primary" as const,
    },
    {
      title: "Conversations",
      value: conversations.length,
      subtitle: "All time",
      icon: ChatIcon,
      href: "/chat",
      color: "secondary" as const,
    },
  ];

  return (
    <Box sx={{ maxWidth: 1100 }}>
        <Typography variant="h4" fontWeight={700} gutterBottom>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Welcome to your Clinical Document Intelligence workspace. Upload protocols, SOPs, or
          regulatory submissions and get verifiable answers with source attribution.
        </Typography>

        <Grid container spacing={3}>
          {stats.map((stat) => (
            <Grid size={{ xs: 12, md: 6 }} key={stat.title}>
              <Card sx={{ height: "100%" }}>
                <CardContent>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
                    <Box
                      sx={{
                        p: 1.2,
                        borderRadius: 2,
                        bgcolor: (theme) => alpha(theme.palette[stat.color].main, 0.08),
                        color: `${stat.color}.main`,
                      }}
                    >
                      <stat.icon />
                    </Box>
                    <Typography variant="h6" fontWeight={600}>
                      {stat.title}
                    </Typography>
                  </Box>
                  <Typography variant="h3" fontWeight={700} gutterBottom>
                    {docsLoading || convLoading ? "—" : stat.value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {stat.subtitle}
                  </Typography>
                  <Button component={Link} href={stat.href} endIcon={<ArrowForwardIcon />}>
                    Go to {stat.title}
                  </Button>
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>

        <Card sx={{ mt: 4 }}>
          <CardContent>
            <Typography variant="h6" fontWeight={600} gutterBottom>
              How it works
            </Typography>
            <Box component="ol" sx={{ pl: 2, color: "text.secondary", lineHeight: 1.8 }}>
              <li>Upload a clinical or regulatory document.</li>
              <li>Wait for processing to complete (usually a few seconds).</li>
              <li>Ask questions in natural language.</li>
              <li>Review answers with citations, confidence scores, and model attribution.</li>
            </Box>
          </CardContent>
        </Card>
    </Box>
  );
}
