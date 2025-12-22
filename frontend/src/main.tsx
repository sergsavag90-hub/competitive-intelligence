import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import { QueryClient, QueryClientProvider } from "react-query";
import App from "./pages/App";
import "./index.css";

const queryClient = new QueryClient();

const prefersDark =
  window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;

const theme = createTheme({
  palette: {
    mode: prefersDark ? "dark" : "light",
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <React.Suspense fallback={<div>Loading...</div>}>
          <App />
        </React.Suspense>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
);
