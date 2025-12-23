import React, { useEffect, useState } from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { useCompetitorData } from "@hooks/useCompetitorData";
import { useScanStatus } from "@hooks/useScanStatus";
import { CompetitorTable } from "@components/CompetitorTable";
import { CompetitorTableServer } from "@components/CompetitorTableServer";
import { ScanProgress } from "@components/ScanProgress";
import client from "@api/client";
import { useAuth } from "../contexts/AuthContext";

const App: React.FC = () => {
  const { data: competitors = [] } = useCompetitorData();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const status = useScanStatus(jobId ?? undefined);
  const [error, setError] = useState<string | null>(null);
  const [hasBoundaryError, setHasBoundaryError] = useState(false);
  const { user, token, login, logout } = useAuth();

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
          {user ? (
            <Button color="inherit" onClick={logout}>
              Logout
            </Button>
          ) : null}
        </Toolbar>
      </AppBar>
      <Router>
        <Container sx={{ py: 3 }}>
          <Stack spacing={2}>
            {error && (
              <Box sx={{ p: 2, border: "1px solid", borderColor: "error.main", borderRadius: 1, color: "error.main" }}>
                <Typography variant="body2">Error: {error}</Typography>
              </Box>
            )}
            <Routes>
              <Route path="/login" element={<LoginPage onLogin={login} />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute user={user}>
                    <>
                      <CompetitorTableServer onSelect={(c) => setSelectedId(c.id)} />
                      {hasBoundaryError && (
                        <Box
                          sx={{ p: 2, border: "1px solid", borderColor: "error.main", borderRadius: 1, color: "error.main" }}
                        >
                          <Typography variant="body2">Unexpected error: {error}</Typography>
                        </Box>
                      )}
                      <Stack direction="row" spacing={2}>
                        <Button variant="contained" onClick={triggerScan} disabled={!selectedId}>
                          Trigger Scan
                        </Button>
                        {jobId && <Typography variant="body2">Job: {jobId}</Typography>}
                      </Stack>
                      <ScanProgress status={status} />
                    </>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </Stack>
        </Container>
      </Router>
    </Box>
  );
};

function ProtectedRoute({ user, children }: { user: any; children: React.ReactNode }) {
  const location = useLocation();
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

const LoginPage: React.FC<{ onLogin: (token: string, user?: { role?: string }) => void }> = ({ onLogin }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as any)?.from || "/";

  const submit = async () => {
    try {
      const { data } = await client.post<{ access_token: string; role?: string }>("/auth/login", { email, password });
      if (data.access_token) {
        onLogin(data.access_token, { role: data.role });
        navigate(from, { replace: true });
      }
      setError(null);
    } catch (exc: any) {
      setError(exc?.message || "Login failed");
    }
  };

  return (
    <Box sx={{ maxWidth: 360 }}>
      <Typography variant="h6">Login</Typography>
      <Stack spacing={2} sx={{ mt: 2 }}>
        <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" />
        <Button variant="contained" onClick={submit}>
          Login
        </Button>
        {error && <Typography color="error">{error}</Typography>}
      </Stack>
    </Box>
  );
};

export default App;
