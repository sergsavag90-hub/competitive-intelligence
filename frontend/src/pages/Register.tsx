import React, { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import { Box, Button, Link, Stack, TextField, Typography } from "@mui/material";
import client from "@api/client";
import { useAuth } from "../contexts/AuthContext";

export const RegisterPage: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuth();

  const handleRegister = async () => {
    setLoading(true);
    try {
      const { data } = await client.post<{ access_token: string; role?: string }>("/auth/register", {
        email,
        password,
      });
      if (data.access_token) {
        login(data.access_token, { email, role: data.role });
        setError(null);
        navigate("/dashboard", { replace: true });
      }
    } catch (exc: any) {
      setError(exc?.response?.data?.detail || exc?.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 400, mx: "auto", mt: 6 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Create account
      </Typography>
      <Stack spacing={2}>
        <TextField label="Email" value={email} onChange={(e) => setEmail(e.target.value)} fullWidth />
        <TextField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          fullWidth
        />
        <Button variant="contained" onClick={handleRegister} disabled={loading}>
          {loading ? "Registering..." : "Register"}
        </Button>
        {error && (
          <Typography color="error" variant="body2">
            {error}
          </Typography>
        )}
        <Link component={RouterLink} to="/login" underline="hover">
          Already have an account? Sign in
        </Link>
      </Stack>
    </Box>
  );
};
