"use client";

import { useState, useRef, useEffect } from "react";
import Box from "@mui/material/Box";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import TextField from "@mui/material/TextField";
import Button from "@mui/material/Button";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import Select from "@mui/material/Select";
import MenuItem from "@mui/material/MenuItem";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import Switch from "@mui/material/Switch";
import SendIcon from "@mui/icons-material/Send";
import StopIcon from "@mui/icons-material/Stop";
import { useChatContext } from "@/context/ChatContext";

interface ChatInputProps {
  onSend: (
    question: string,
    strictMode: boolean,
    provider?: string,
    model?: string
  ) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  showSuggestions?: boolean;
}

const SUGGESTIONS = [
  "What are the inclusion criteria?",
  "Summarize the primary endpoints.",
  "Compare the adverse event profiles.",
  "Who is the sponsor and what is the indication?",
];

export function ChatInput({
  onSend,
  onStop,
  isStreaming,
  disabled,
  showSuggestions,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [strictMode, setStrictMode] = useState(false);
  const {
    providers,
    isLoadingProviders,
    providersError,
    selectedProvider,
    selectedModel,
    selectProvider,
    selectModel,
  } = useChatContext();
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  const selectedProviderData = providers.find(
    (provider) => provider.id === selectedProvider
  );
  const availableModels = selectedProviderData?.models ?? [];

  const submitQuestion = () => {
    const trimmed = input.trim();
    if (
      !trimmed ||
      isStreaming ||
      disabled ||
      !selectedProvider ||
      !selectedModel
    )
      return;
    onSend(trimmed, strictMode, selectedProvider, selectedModel);
    setInput("");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitQuestion();
  };

  const handleSuggestionClick = (suggestion: string) => {
    if (
      isStreaming ||
      disabled ||
      !selectedProvider ||
      !selectedModel
    )
      return;
    onSend(suggestion, strictMode, selectedProvider, selectedModel);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuestion();
    }
  };

  const controlsDisabled = isStreaming || disabled || isLoadingProviders;
  const canSend =
    input.trim().length > 0 &&
    !isStreaming &&
    !disabled &&
    !isLoadingProviders &&
    !!selectedProvider &&
    !!selectedModel;

  return (
    <Paper
      component="form"
      onSubmit={handleSubmit}
      elevation={2}
      sx={{
        p: 2,
        borderRadius: 3,
        border: "1px solid",
        borderColor: "divider",
        position: "sticky",
        bottom: 0,
        bgcolor: "background.paper",
      }}
    >
      {showSuggestions && providers.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ mb: 1, fontWeight: 500 }}
          >
            Try asking:
          </Typography>
          <Box
            sx={{
              display: "flex",
              flexDirection: { xs: "column", sm: "row" },
              flexWrap: "wrap",
              gap: 1,
              alignItems: { xs: "stretch", sm: "center" },
            }}
          >
            {SUGGESTIONS.map((suggestion) => (
              <Typography
                key={suggestion}
                component="button"
                type="button"
                onClick={() => handleSuggestionClick(suggestion)}
                disabled={controlsDisabled || !selectedProvider || !selectedModel}
                sx={{
                  color: "primary.main",
                  bgcolor: "transparent",
                  border: "1px solid",
                  borderColor: "primary.light",
                  borderRadius: 2,
                  px: 2,
                  py: 1,
                  cursor: "pointer",
                  fontSize: "0.95rem",
                  textAlign: "center",
                  width: { xs: "100%", sm: "fit-content" },
                  maxWidth: "100%",
                  transition: "all 0.2s",
                  "&:hover:not(:disabled)": {
                    bgcolor: "primary.light",
                    color: "primary.contrastText",
                  },
                  "&:disabled": {
                    opacity: 0.5,
                    cursor: "not-allowed",
                  },
                }}
              >
                {suggestion}
              </Typography>
            ))}
          </Box>
        </Box>
      )}

      {providersError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {providersError}
        </Alert>
      )}

      {!isLoadingProviders && providers.length === 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No LLM providers are configured. Add an API key to your .env file and restart the backend.
        </Alert>
      )}

      {isLoadingProviders ? (
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 1.5,
            mb: 2,
          }}
        >
          <CircularProgress size={20} />
          <Typography variant="body2" color="text.secondary">
            Loading providers...
          </Typography>
        </Box>
      ) : (
        <Box
          sx={{
            display: "flex",
            gap: 2,
            mb: 2,
            flexDirection: { xs: "column", sm: "row" },
          }}
        >
          <FormControl
            fullWidth
            size="small"
            sx={{ minWidth: { sm: 160 }, flex: 1 }}
          >
            <InputLabel id="provider-select-label">Provider</InputLabel>
            <Select
              labelId="provider-select-label"
              id="provider-select"
              value={selectedProvider}
              label="Provider"
              onChange={(e) => selectProvider(e.target.value)}
              disabled={controlsDisabled}
            >
              {providers.map((provider) => (
                <MenuItem key={provider.id} value={provider.id}>
                  {provider.display_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl
            fullWidth
            size="small"
            sx={{ minWidth: { sm: 180 }, flex: 1 }}
          >
            <InputLabel id="model-select-label">Model</InputLabel>
            <Select
              labelId="model-select-label"
              id="model-select"
              value={selectedModel}
              label="Model"
              onChange={(e) => selectModel(e.target.value)}
              disabled={controlsDisabled || availableModels.length === 0}
            >
              {availableModels.map((model) => (
                <MenuItem key={model.id} value={model.id}>
                  {model.display_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      )}

      <TextField
        inputRef={textareaRef}
        fullWidth
        multiline
        maxRows={6}
        placeholder="Ask a question about your documents..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled || isStreaming || isLoadingProviders}
        aria-label="Question input"
        sx={{
          "& .MuiOutlinedInput-root": {
            borderRadius: 2,
            bgcolor: "background.default",
          },
        }}
      />
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          mt: 1.5,
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <FormControlLabel
          control={
            <Switch
              checked={strictMode}
              onChange={(e) => setStrictMode(e.target.checked)}
              disabled={isStreaming || disabled || isLoadingProviders}
              size="small"
            />
          }
          label={
            <Box component="span" sx={{ fontSize: "0.875rem", color: "text.secondary" }}>
              Strict mode
            </Box>
          }
        />
        <Box sx={{ display: "flex", gap: 1 }}>
          {isStreaming && onStop && (
            <Button
              variant="outlined"
              color="error"
              onClick={onStop}
              startIcon={<StopIcon />}
              aria-label="Stop generating"
            >
              Stop
            </Button>
          )}
          <Button
            type="submit"
            variant="contained"
            disabled={!canSend}
            endIcon={<SendIcon />}
            aria-label="Send message"
          >
            Send
          </Button>
        </Box>
      </Box>
    </Paper>
  );
}
