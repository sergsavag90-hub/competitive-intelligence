import { useEffect, useRef, useState } from "react";
import { ScanStatus } from "../types/api";
import { useAuth } from "../contexts/AuthContext";

export const useScanStatus = (jobId?: string) => {
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const { token } = useAuth();

  useEffect(() => {
    if (!jobId) return;
    const url = new URL(`${window.location.origin.replace(/^http/, "ws")}/ws/scan/${jobId}`);
    if (token) {
      url.searchParams.set("token", token);
    }
    const ws = new WebSocket(url.toString());
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus((prev) => ({ ...(prev || {}), ...data }));
      } catch {
        /* ignore */
      }
    };
    wsRef.current = ws;

    ws.onclose = () => {
      // basic reconnect
      setTimeout(() => {
        setStatus(null);
        wsRef.current = null;
      }, 5000);
    };
    return () => {
      ws.close();
    };
  }, [jobId, token]);

  return status;
};
