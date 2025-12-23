import React from "react";
import { LinearProgress, Typography, Box } from "@mui/material";
import { ScanStatus } from "../types/api";

type Props = {
  status: ScanStatus | null;
};

export const ScanProgress: React.FC<Props> = ({ status }) => {
  if (!status) return null;
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle2">Scan status: {status.status}</Typography>
      <LinearProgress variant="determinate" value={status.progress} />
      {status.error && (
        <Typography color="error" variant="body2">
          {status.error}
        </Typography>
      )}
    </Box>
  );
};
