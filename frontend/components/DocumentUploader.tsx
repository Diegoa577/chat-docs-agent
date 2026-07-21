"use client";

import { useRef, useState } from "react";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Typography from "@mui/material/Typography";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";
import { uploadDocument } from "@/lib/api";
import { MAX_UPLOAD_SIZE_MB } from "@/lib/constants";

interface DocumentUploaderProps {
  onUploaded: () => void;
  onError: (message: string) => void;
}

const ACCEPTED_EXTENSIONS = [".pdf", ".txt", ".docx"];

export function DocumentUploader({ onUploaded, onError }: DocumentUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);
  const uploadingRef = useRef(false);

  const fail = (message: string) => {
    setErrorMessage(message);
    onError(message);
  };

  const handleFile = async (file: File) => {
    if (uploadingRef.current) return;

    const lowerName = file.name.toLowerCase();
    if (!ACCEPTED_EXTENSIONS.some((ext) => lowerName.endsWith(ext))) {
      fail("Only PDF, TXT, and DOCX files are supported.");
      return;
    }
    if (file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024) {
      fail(`File exceeds the ${MAX_UPLOAD_SIZE_MB}MB limit.`);
      return;
    }

    uploadingRef.current = true;
    setIsUploading(true);
    setErrorMessage(null);
    try {
      await uploadDocument(file);
      onUploaded();
    } catch (err) {
      fail(err instanceof Error ? err.message : "Upload failed");
    } finally {
      uploadingRef.current = false;
      setIsUploading(false);
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    if (files.length > 1) {
      fail("Please upload one file at a time.");
      return;
    }
    handleFile(files[0]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current += 1;
    setIsDragging(true);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
    if (dragCounterRef.current === 0) setIsDragging(false);
  };

  const openFileDialog = () => {
    inputRef.current?.click();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      openFileDialog();
    }
  };

  return (
    <Paper
      variant="outlined"
      role="button"
      tabIndex={0}
      aria-label="Upload a document"
      onClick={openFileDialog}
      onKeyDown={handleKeyDown}
      onDrop={handleDrop}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      sx={{
        p: 4,
        borderRadius: 3,
        borderStyle: "dashed",
        borderWidth: 2,
        borderColor: isDragging ? "primary.main" : "divider",
        bgcolor: isDragging ? "primary.light" : "background.paper",
        transition: "all 0.2s",
        textAlign: "center",
        cursor: "pointer",
      }}
    >
      <CloudUploadIcon sx={{ fontSize: 48, color: "primary.main", mb: 1 }} />
      <Typography variant="h6" fontWeight={600} gutterBottom>
        {isUploading ? "Uploading..." : "Upload a document"}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Drag and drop a PDF, TXT, or DOCX file here (max {MAX_UPLOAD_SIZE_MB}MB), or click anywhere
        in this area to browse.
      </Typography>
      {errorMessage && (
        <Typography variant="body2" color="error" role="alert" sx={{ mb: 2 }}>
          {errorMessage}
        </Typography>
      )}
      <Button
        variant="contained"
        disabled={isUploading}
        startIcon={
          isUploading ? <CircularProgress size={16} color="inherit" /> : <CloudUploadIcon />
        }
        onClick={(e) => {
          e.stopPropagation();
          openFileDialog();
        }}
      >
        {isUploading ? "Uploading..." : "Browse files"}
      </Button>
      <input
        ref={inputRef}
        type="file"
        hidden
        accept=".pdf,.txt,.docx"
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </Paper>
  );
}
