import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "../contexts/AuthContext";

export const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }

  return <>{children}</>;
};
