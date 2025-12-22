import React, { useEffect, useState } from "react";
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { useCompetitorData } from "@hooks/useCompetitorData";
import { useScanStatus } from "@hooks/useScanStatus";
import { CompetitorTable } from "@components/CompetitorTable";
import { CompetitorTableServer } from "@components/CompetitorTableServer";
import { ScanProgress } from "@components/ScanProgress";
import client from "@api/client";

const App: React.FC = () => {
  const { data: competitors = [] } = useCompetitorData();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const status = useScanStatus(jobId ?? undefined);
  const [error, setError] = useState<string | null>(null);
  const [hasBoundaryError, setHasBoundaryError] = useState(false);

  const triggerScan = async () => {
    if (!selectedId) return;
    try {
      const { data } = await client.post<{ job_id: string }>(`/scan/${selectedId}`);
      setJobId(data.job_id);
      setError(null);
    } catch (err: any) {
      setError(err?.message || "Failed to trigger scan");
    }
  };

  useEffect(() => {
    const handler = (event: ErrorEvent) => {
      setHasBoundaryError(true);
      setError(event.message);
    };
    window.addEventListener("error", handler);
    return () => window.removeEventListener("error", handler);
  }, []);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", color: "text.primary" }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Competitive Intelligence Dashboard (FastAPI/React)
          </Typography>
        </Toolbar>
      </AppBar>
      <Container sx={{ py: 3 }}>
        <Stack spacing={2}>
          {error && (
            <Box sx={{ p: 2, border: "1px solid", borderColor: "error.main", borderRadius: 1, color: "error.main" }}>
              <Typography variant="body2">Error: {error}</Typography>
            </Box>
          )}
          <CompetitorTableServer onSelect={(c) => setSelectedId(c.id)} />
          {hasBoundaryError && (
            <Box sx={{ p: 2, border: "1px solid", borderColor: "error.main", borderRadius: 1, color: "error.main" }}>
              <Typography variant="body2">Unexpected error: {error}</Typography>
            </Box>
          )}
          <Stack direction="row" spacing={2}>
            <Button variant="contained" onClick={triggerScan} disabled={!selectedId}>
              Trigger Scan
            </Button>
            {jobId && (
              <Typography variant="body2">Job: {jobId}</Typography>
            )}
          </Stack>
          <ScanProgress status={status} />
        </Stack>
      </Container>
    </Box>
  );
};

export default App;
