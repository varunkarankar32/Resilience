import { useEffect, useCallback, useRef } from "react";
import { getSocket, disconnectSocket } from "../lib/socket";

interface IncidentUpdate {
  incidentId: string;
  serviceName: string;
  status: string;
  rootCauseAnalysis: string | null;
  remediationSteps: string[];
  confidenceScore: number | null;
  graphExecutionPath: string[];
  blastRadius: {
    upstream: string[];
    downstream: string[];
  };
}

export function useSocket(onIncidentUpdate: (update: IncidentUpdate) => void) {
  const callbackRef = useRef(onIncidentUpdate);
  callbackRef.current = onIncidentUpdate;

  useEffect(() => {
    const socket = getSocket();

    const handler = (data: IncidentUpdate) => {
      callbackRef.current(data);
    };

    socket.on("incident-update", handler);

    return () => {
      socket.off("incident-update", handler);
    };
  }, []);
}

export function useSocketCleanup() {
  useEffect(() => {
    return () => {
      disconnectSocket();
    };
  }, []);
}
