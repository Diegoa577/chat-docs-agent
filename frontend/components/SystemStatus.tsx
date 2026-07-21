"use client";

import { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Tooltip from "@mui/material/Tooltip";
import { API_URL } from "@/lib/constants";

interface StatusState {
  status: "loading" | "ok" | "degraded" | "error";
  message: string;
}

export function SystemStatus() {
  const [state, setState] = useState<StatusState>({
    status: "loading",
    message: "Checking status...",
  });

  useEffect(() => {
    let cancelled = false;

    async function checkStatus() {
      try {
        const readyRes = await fetch(`${API_URL}/ready`, { cache: "no-store" });
        if (!cancelled) {
          if (readyRes.ok) {
            setState({ status: "ok", message: "System ready" });
          } else {
            const body = await readyRes.json().catch(() => ({}));
            setState({
              status: "degraded",
              message: body.detail || "System not ready",
            });
          }
        }
      } catch {
        if (!cancelled) {
          setState({ status: "error", message: "Backend unreachable" });
        }
      }
    }

    checkStatus();
    const interval = setInterval(checkStatus, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const color =
    state.status === "ok"
      ? "success.main"
      : state.status === "degraded"
      ? "warning.main"
      : state.status === "error"
      ? "error.main"
      : "text.secondary";

  return (
    <Tooltip title={state.message} arrow>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1,
          px: 1.5,
          py: 0.5,
          borderRadius: 2,
          bgcolor: "rgba(0,0,0,0.04)",
          cursor: "default",
        }}
        aria-label={`System status: ${state.message}`}
      >
        <Box
          sx={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            bgcolor: color,
            animation: state.status === "loading" ? "pulse 1.5s infinite" : "none",
            "@keyframes pulse": {
              "0%": { opacity: 1 },
              "50%": { opacity: 0.4 },
              "100%": { opacity: 1 },
            },
          }}
        />
        <Box
          component="span"
          sx={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "text.secondary",
            textTransform: "capitalize",
          }}
        >
          {state.status}
        </Box>
      </Box>
    </Tooltip>
  );
}
