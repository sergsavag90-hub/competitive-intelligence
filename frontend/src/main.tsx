import React, { StrictMode, Suspense } from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./pages/App";
import "./index.css";
import { AuthProvider } from "./contexts/AuthContext";

const queryClient = new QueryClient();

const prefersDark =
  window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

// Ensure #root exists (vite dev may serve 404 if not injected correctly)
const rootEl = document.getElementById("root") || (() => {
  const el = document.createElement("div");
  el.id = "root";
  document.body.appendChild(el);
  return el;
})();

const theme = createTheme({
  palette: {
    mode: prefersDark ? "dark" : "light",
  },
});

ReactDOM.createRoot(rootEl).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AuthProvider>
          <Suspense fallback={<div>Loading...</div>}>
            <App />
          </Suspense>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </StrictMode>
);
