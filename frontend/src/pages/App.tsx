import React from "react";
import { BrowserRouter as Router, Routes, Route, Navigate, Link as RouterLink } from "react-router-dom";
import { AppBar, Box, Button, Container, Stack, Toolbar, Typography } from "@mui/material";
import { ProtectedRoute } from "@components/ProtectedRoute";
import { LoginPage } from "./Login";
import { RegisterPage } from "./Register";
import { Dashboard } from "./Dashboard";
import { useAuth } from "../contexts/AuthContext";
import { ErrorBoundary } from "@components/ErrorBoundary";

const App: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "background.default", color: "text.primary" }}>
      <Router>
        <AppBar position="static">
          <Toolbar>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              Competitive Intelligence Dashboard (FastAPI/React)
            </Typography>
            <Stack direction="row" spacing={2}>
              {user ? (
                <>
                  <Button color="inherit" component={RouterLink} to="/dashboard">
                    Dashboard
                  </Button>
                  <Button color="inherit" onClick={logout}>
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Button color="inherit" component={RouterLink} to="/login">
                    Login
                  </Button>
                  <Button color="inherit" component={RouterLink} to="/register">
                    Register
                  </Button>
                </>
              )}
            </Stack>
          </Toolbar>
        </AppBar>
        <Container sx={{ py: 3 }}>
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute>
                    <Dashboard />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </ErrorBoundary>
        </Container>
      </Router>
    </Box>
  );
};

export default App;
