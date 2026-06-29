import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useSocket } from "../hooks/useSocket";

interface Incident {
  id: string;
  incidentId: string;
  serviceName: string;
  status: "Investigating" | "Triage" | "Resolved";
  severity: "critical" | "high" | "medium" | "low";
  errorMessage: string;
  confidenceScore: number | null;
  graphExecutionPath: string[];
  createdAt: string;
  alertCount: number;
}

const STATUS_COLORS: Record<Incident["status"], string> = {
  Investigating: "#ef4444",
  Triage: "#f59e0b",
  Resolved: "#22c55e",
};

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [connected, setConnected] = useState(false);

  useSocket((update) => {
    setIncidents((prev) => {
      const idx = prev.findIndex((i) => i.incidentId === update.incidentId);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = {
          ...(updated[idx] as Incident),
          status: update.status as Incident["status"],
          confidenceScore: update.confidenceScore,
          graphExecutionPath: update.graphExecutionPath,
          rootCauseAnalysis: update.rootCauseAnalysis,
        };
        return updated;
      }
      return prev;
    });
  });

  useEffect(() => {
    fetch("/api/v1/incidents")
      .then((res) => res.json())
      .then((data) => {
        setIncidents(data.incidents || []);
        setConnected(true);
      })
      .catch(() => setConnected(false));
  }, []);

  const criticalCount = incidents.filter((i) => i.severity === "critical").length;
  const activeCount = incidents.filter(
    (i) => i.status !== "Resolved"
  ).length;

  return (
    <div className="incidents-page">
      <header className="page-header">
        <div>
          <h1>SRE Command Center</h1>
          <p>
            {connected ? "Live — MongoDB Change Streams active" : "Offline — Start backend services"}
          </p>
        </div>
        <div className="status-indicator">
          <span
            className="status-dot"
            style={{ background: connected ? "#22c55e" : "#ef4444" }}
          />
          {connected ? "Connected" : "Disconnected"}
        </div>
      </header>

      <div className="kpi-grid">
        <div className="kpi-card">
          <span className="kpi-value">{incidents.length}</span>
          <span className="kpi-label">Total Incidents</span>
        </div>
        <div className="kpi-card critical">
          <span className="kpi-value">{criticalCount}</span>
          <span className="kpi-label">Critical</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-value">{activeCount}</span>
          <span className="kpi-label">Active</span>
        </div>
        <div className="kpi-card">
          <span className="kpi-value">
            {incidents.filter((i) => i.confidenceScore && i.confidenceScore >= 0.8).length}
          </span>
          <span className="kpi-label">Diagnosed</span>
        </div>
      </div>

      {incidents.length === 0 ? (
        <div className="empty-state">
          <h2>No Active Incidents</h2>
          <p>Send an alert to the webhooks-gateway to see it appear here in real-time.</p>
          <code>POST http://localhost:4000/api/v1/alerts</code>
        </div>
      ) : (
        <div className="incident-table-container">
          <table className="incident-table">
            <thead>
              <tr>
                <th>Incident ID</th>
                <th>Service</th>
                <th>Status</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Alerts</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {incidents.map((incident) => (
                <tr key={incident.incidentId}>
                  <td className="mono">{incident.incidentId}</td>
                  <td>{incident.serviceName}</td>
                  <td>
                    <span
                      className="status-badge"
                      style={{ background: STATUS_COLORS[incident.status] }}
                    >
                      {incident.status}
                    </span>
                  </td>
                  <td>
                    <span className={`severity-badge severity-${incident.severity}`}>
                      {incident.severity}
                    </span>
                  </td>
                  <td>
                    {incident.confidenceScore !== null
                      ? `${(incident.confidenceScore * 100).toFixed(0)}%`
                      : "-"}
                  </td>
                  <td>{incident.alertCount}</td>
                  <td>{new Date(incident.createdAt).toLocaleString()}</td>
                  <td>
                    <Link
                      to={`/incidents/${incident.incidentId}`}
                      className="btn btn-primary btn-sm"
                    >
                      Investigate
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
