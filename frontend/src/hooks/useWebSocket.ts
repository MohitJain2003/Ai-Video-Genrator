/**
 * WebSocket hook for real-time job status tracking.
 */

"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getWSURL } from "@/lib/api";
import type { WSStatusUpdate, JobStatus } from "@/types";

interface UseWebSocketReturn {
  status: JobStatus | null;
  overallScore: number | null;
  error: string | null;
  isConnected: boolean;
  lastUpdate: WSStatusUpdate | null;
}

export function useJobWebSocket(jobId: string | null): UseWebSocketReturn {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [overallScore, setOverallScore] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<WSStatusUpdate | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const wsUrl = getWSURL(jobId);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const data: WSStatusUpdate = JSON.parse(event.data);
        setLastUpdate(data);

        if (data.type === "status_update" || data.type === "pipeline_complete") {
          setStatus(data.status);
          if (data.overall_score !== undefined) {
            setOverallScore(data.overall_score);
          }
          if (data.error_message) {
            setError(data.error_message);
          }
        }

        if (data.type === "error") {
          setError(data.message || "Unknown error");
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection error");
      setIsConnected(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [jobId]);

  return { status, overallScore, error, isConnected, lastUpdate };
}
