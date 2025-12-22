import { useEffect, useRef, useState } from "react";
import { ScanStatus } from "@types/api";

export const useScanStatus = (jobId?: string) => {
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const ws = new WebSocket(`${window.location.origin.replace(/^http/, "ws")}/ws/scan/${jobId}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus((prev) => ({ ...(prev || {}), ...data }));
      } catch {
        /* ignore */
      }
    };
    wsRef.current = ws;
    return () => {
      ws.close();
    };
  }, [jobId]);

  return status;
};
