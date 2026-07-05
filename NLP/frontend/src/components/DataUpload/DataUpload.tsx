import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  Button,
  TextField,
  LinearProgress,
  Alert,
  Snackbar,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import CloseIcon from '@mui/icons-material/Close';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { uploadDataset, pollDatasetStatus } from '../../services/api';
import type { Dataset } from '../../types';
import { formatFileSize } from '../../utils/format';

interface DataUploadProps {
  onSuccess?: (dataset: Dataset) => void;
  onClose?: () => void;
  compact?: boolean;
}

type UploadState = 'idle' | 'uploading' | 'processing' | 'done' | 'error';

const ACCEPTED_TYPES = {
  'text/csv': ['.csv'],
  'application/vnd.ms-excel': ['.xls'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
};

const DataUpload: React.FC<DataUploadProps> = ({ onSuccess, onClose, compact = false }) => {
  const [file, setFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState('');
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: { errors: { message: string }[] }[]) => {
    if (rejectedFiles.length > 0) {
      setSnackbar({
        open: true,
        message: `File rejected: ${rejectedFiles[0].errors[0].message}`,
        severity: 'error',
      });
      return;
    }
    if (acceptedFiles.length > 0) {
      const f = acceptedFiles[0];
      setFile(f);
      // Auto-generate name from filename
      const namePart = f.name.replace(/\.(csv|xls|xlsx)$/i, '').replace(/[_-]/g, ' ');
      setDatasetName(namePart.charAt(0).toUpperCase() + namePart.slice(1));
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: ACCEPTED_TYPES,
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100MB
    disabled: uploadState === 'uploading' || uploadState === 'processing' || uploadState === 'done',
  });

  const handleUpload = async () => {
    if (!file || !datasetName.trim()) return;

    setUploadState('uploading');
    setUploadProgress(0);

    try {
      const response = await uploadDataset(file, datasetName.trim(), (progress) => {
        setUploadProgress(progress);
      });

      setUploadState('processing');
      setProcessingStatus('Analyzing columns and computing statistics...');

      const dataset = await pollDatasetStatus(
        response.dataset_id,
        (status) => {
          if (status === 'processing') {
            setProcessingStatus('Processing data and building indexes...');
          }
        }
      );

      setUploadState('done');
      setSnackbar({ open: true, message: `Dataset "${datasetName}" uploaded successfully!`, severity: 'success' });
      onSuccess?.(dataset);
    } catch (err) {
      setUploadState('error');
      const message = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setSnackbar({ open: true, message, severity: 'error' });
    }
  };

  const handleReset = () => {
    setFile(null);
    setDatasetName('');
    setUploadState('idle');
    setUploadProgress(0);
    setProcessingStatus('');
  };

  const getDropzoneStyles = () => ({
    border: '2px dashed',
    borderColor: isDragReject
      ? 'error.main'
      : isDragActive
      ? 'primary.main'
      : uploadState === 'done'
      ? 'success.main'
      : 'divider',
    borderRadius: 2,
    backgroundColor: isDragActive
      ? 'primary.50'
      : uploadState === 'done'
      ? 'success.50'
      : 'background.default',
    transition: 'all 0.2s ease',
    cursor: uploadState === 'done' ? 'default' : 'pointer',
    outline: 'none',
    '&:focus-visible': {
      borderColor: 'primary.main',
    },
  });

  return (
    <Box>
      {/* Drop Zone */}
      <Paper
        {...getRootProps()}
        variant="outlined"
        sx={{
          ...getDropzoneStyles(),
          p: compact ? 3 : 5,
          textAlign: 'center',
          position: 'relative',
        }}
      >
        <input {...getInputProps()} />

        {uploadState === 'done' ? (
          <Box>
            <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
            <Typography variant="h6" color="success.main" fontWeight={600}>
              Upload Complete!
            </Typography>
            <Typography variant="body2" color="text.secondary" mt={0.5}>
              Dataset is ready to query
            </Typography>
          </Box>
        ) : file ? (
          <Box>
            <InsertDriveFileIcon sx={{ fontSize: 48, color: 'primary.main', mb: 1 }} />
            <Typography variant="subtitle1" fontWeight={600}>
              {file.name}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', mt: 1 }}>
              <Chip label={formatFileSize(file.size)} size="small" variant="outlined" />
              <Chip label={file.type || 'spreadsheet'} size="small" variant="outlined" color="primary" />
            </Box>
            {uploadState === 'idle' && (
              <Tooltip title="Remove file">
                <IconButton
                  size="small"
                  onClick={(e) => { e.stopPropagation(); handleReset(); }}
                  sx={{ position: 'absolute', top: 8, right: 8 }}
                >
                  <CloseIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        ) : (
          <Box>
            <CloudUploadIcon
              sx={{
                fontSize: compact ? 40 : 64,
                color: isDragActive ? 'primary.main' : 'text.disabled',
                mb: 1,
                transition: 'all 0.2s ease',
                transform: isDragActive ? 'scale(1.1) translateY(-4px)' : 'none',
              }}
            />
            <Typography variant={compact ? 'subtitle1' : 'h6'} fontWeight={600} color="text.primary">
              {isDragActive ? 'Drop your file here' : 'Drag & drop your data file'}
            </Typography>
            <Typography variant="body2" color="text.secondary" mt={0.5}>
              or <Box component="span" sx={{ color: 'primary.main', fontWeight: 600 }}>browse files</Box>
            </Typography>
            <Typography variant="caption" color="text.secondary" mt={1} display="block">
              Supports CSV, XLS, XLSX — max 100MB
            </Typography>
          </Box>
        )}
      </Paper>

      {/* Dataset Name Input */}
      {file && uploadState !== 'done' && (
        <TextField
          fullWidth
          label="Dataset Name"
          value={datasetName}
          onChange={(e) => setDatasetName(e.target.value)}
          placeholder="e.g., Sales Q4 2024"
          variant="outlined"
          size="medium"
          sx={{ mt: 2 }}
          disabled={uploadState === 'uploading' || uploadState === 'processing'}
          helperText="Give your dataset a descriptive name"
        />
      )}

      {/* Progress */}
      {(uploadState === 'uploading' || uploadState === 'processing') && (
        <Box sx={{ mt: 2 }}>
          {uploadState === 'uploading' ? (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Uploading...
                </Typography>
                <Typography variant="caption" fontWeight={600} color="primary.main">
                  {uploadProgress}%
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={uploadProgress} sx={{ height: 6 }} />
            </>
          ) : (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {processingStatus}
                </Typography>
              </Box>
              <LinearProgress sx={{ height: 6 }} />
            </>
          )}
        </Box>
      )}

      {uploadState === 'error' && (
        <Alert severity="error" sx={{ mt: 2 }} action={
          <Button size="small" color="inherit" onClick={handleReset}>Retry</Button>
        }>
          Upload failed. Please try again with a valid file.
        </Alert>
      )}

      {/* Actions */}
      <Box sx={{ mt: 2, display: 'flex', gap: 1.5, justifyContent: 'flex-end' }}>
        {onClose && (
          <Button variant="outlined" color="inherit" onClick={onClose} disabled={uploadState === 'uploading' || uploadState === 'processing'}>
            Cancel
          </Button>
        )}
        {uploadState === 'done' ? (
          <Button variant="outlined" color="success" onClick={handleReset}>
            Upload Another
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleUpload}
            disabled={!file || !datasetName.trim() || uploadState === 'uploading' || uploadState === 'processing'}
            startIcon={<CloudUploadIcon />}
            size="large"
          >
            {uploadState === 'uploading' ? 'Uploading...' : uploadState === 'processing' ? 'Processing...' : 'Upload Dataset'}
          </Button>
        )}
      </Box>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default DataUpload;
