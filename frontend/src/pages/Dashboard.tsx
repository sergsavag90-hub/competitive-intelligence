import React, { useEffect, useState } from "react";
import { Box, Button, Card, CardContent, Grid, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";
import { useCompetitorData } from "@hooks/useCompetitorData";
import { useScanStatus } from "@hooks/useScanStatus";
import { CompetitorTableServer } from "@components/CompetitorTableServer";
import { ScanProgress } from "@components/ScanProgress";
import client from "@api/client";

export const Dashboard: React.FC = () => {
  const { data: competitors = [] } = useCompetitorData();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const status = useScanStatus(jobId ?? undefined);
  const [error, setError] = useState<string | null>(null);
  const [hasBoundaryError, setHasBoundaryError] = useState(false);

  const triggerScan = async () => {
    if (!selectedId) return;
    try {
      const { data } = await client.post<{ job_id: string }>(`/api/v1/scan/${selectedId}`);
      setJobId(data.job_id);
      setError(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Failed to trigger scan");
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
    <Stack spacing={3}>
      <Typography variant="h5">Dashboard</Typography>

      <Grid container spacing={2}>
        {[
          { title: "SEO Analysis", description: "Meta tags, headings, structured data", path: "/seo" },
          { title: "Company Data", description: "Contacts, socials, key facts", path: "/company" },
          { title: "Products", description: "Catalog, price tracking, availability", path: "/products" },
          { title: "Promotions", description: "Current promos, discounts, campaigns", path: "/promotions" },
        ].map((tool) => (
          <Grid item xs={12} sm={6} md={3} key={tool.title}>
            <Card>
              <CardContent>
                <Typography variant="subtitle1">{tool.title}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {tool.description}
                </Typography>
                <Button component={RouterLink} to={tool.path} size="small">
                  Open
                </Button>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {error && (
        <Box sx={{ p: 2, border: "1px solid", borderColor: "error.main", borderRadius: 1, color: "error.main" }}>
          <Typography variant="body2">Error: {error}</Typography>
        </Box>
      )}

      <Stack spacing={2}>
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
          {jobId && <Typography variant="body2">Job: {jobId}</Typography>}
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {competitors.length} competitors
          </Typography>
        </Stack>
        <ScanProgress status={status} />
      </Stack>
    </Stack>
  );
};
