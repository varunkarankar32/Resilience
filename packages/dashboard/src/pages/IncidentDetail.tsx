import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import { useSocket } from "../hooks/useSocket";

interface IncidentDetail {
  incidentId: string;
  serviceName: string;
  status: string;
  severity: string;
  errorMessage: string;
  rootCauseAnalysis: string | null;
  remediationSteps: string[];
  confidenceScore: number | null;
  graphExecutionPath: string[];
  blastRadius: {
    upstream: string[];
    downstream: string[];
  };
  alerts: { timestamp: string; log: string }[];
}

interface RunbookStep {
  step: number;
  description: string;
  completed: boolean;
}

function parseRunbookSteps(markdownSteps: string[]): RunbookStep[] {
  return markdownSteps.map((step, idx) => ({
    step: idx + 1,
    description: step,
    completed: false,
  }));
}

export default function IncidentDetail() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [runbookSteps, setRunbookSteps] = useState<RunbookStep[]>([]);
  const [loading, setLoading] = useState(true);

  useSocket((update) => {
    if (update.incidentId === incidentId) {
      setIncident((prev) =>
        prev
          ? {
              ...prev,
              status: update.status,
              rootCauseAnalysis: update.rootCauseAnalysis || prev.rootCauseAnalysis,
              remediationSteps: update.remediationSteps.length
                ? update.remediationSteps
                : prev.remediationSteps,
              confidenceScore: update.confidenceScore ?? prev.confidenceScore,
              graphExecutionPath: update.graphExecutionPath.length
                ? update.graphExecutionPath
                : prev.graphExecutionPath,
              blastRadius: update.blastRadius,
            }
          : prev
      );
    }
  });

  useEffect(() => {
    if (!incidentId) return;
    fetch(`/api/v1/incidents/${incidentId}`)
      .then((res) => res.json())
      .then((data) => {
        setIncident(data as IncidentDetail);
        setRunbookSteps(parseRunbookSteps(data.remediationSteps || []));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [incidentId]);

  const toggleStep = (stepIdx: number) => {
    setRunbookSteps((prev) =>
      prev.map((s, i) => (i === stepIdx ? { ...s, completed: !s.completed } : s))
    );
  };

  if (loading) {
    return <div className="loading">Loading incident details...</div>;
  }

  if (!incident) {
    return <div className="error">Incident not found</div>;
  }

  const completedSteps = runbookSteps.filter((s) => s.completed).length;
  const progress = runbookSteps.length
    ? Math.round((completedSteps / runbookSteps.length) * 100)
    : 0;

  return (
    <div className="incident-detail">
      <header className="detail-header">
        <div>
          <h1>
            {incident.incidentId}: {incident.serviceName}
          </h1>
          <span className={`severity-badge severity-${incident.severity}`}>
            {incident.severity}
          </span>
        </div>
        <span className="status-badge" style={{ background: "#3b82f6" }}>
          {incident.status}
        </span>
      </header>

      {/* Blast Radius Section */}
      <section className="detail-section blast-radius">
        <h2>Blast Radius Map</h2>
        <div className="blast-radius-grid">
          <div className="blast-column upstream">
            <h3>Upstream ({incident.blastRadius.upstream.length})</h3>
            {incident.blastRadius.upstream.length === 0 ? (
              <p className="empty">No upstream dependencies found</p>
            ) : (
              <ul>
                {incident.blastRadius.upstream.map((svc) => (
                  <li key={svc}>{svc}</li>
                ))}
              </ul>
            )}
          </div>
          <div className="blast-column center">
            <div className="blast-center-node">{incident.serviceName}</div>
          </div>
          <div className="blast-column downstream">
            <h3>Downstream ({incident.blastRadius.downstream.length})</h3>
            {incident.blastRadius.downstream.length === 0 ? (
              <p className="empty">No downstream dependencies found</p>
            ) : (
              <ul>
                {incident.blastRadius.downstream.map((svc) => (
                  <li key={svc}>{svc}</li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* LangGraph Execution Path */}
      <section className="detail-section">
        <h2>Agent Reasoning Path</h2>
        {incident.graphExecutionPath.length === 0 ? (
          <p className="empty">No execution path recorded yet</p>
        ) : (
          <div className="execution-path">
            {incident.graphExecutionPath.map((node, idx) => (
              <div key={idx} className="execution-node">
                <span className="node-index">{idx + 1}</span>
                <span className="node-name">{node}</span>
                {idx < incident.graphExecutionPath.length - 1 && (
                  <span className="node-arrow">→</span>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Root Cause Analysis */}
      <section className="detail-section">
        <h2>Root Cause Analysis</h2>
        {incident.rootCauseAnalysis ? (
          <div className="rca-content">
            <ReactMarkdown>{incident.rootCauseAnalysis}</ReactMarkdown>
          </div>
        ) : (
          <p className="empty">Diagnosis in progress — awaiting agent evaluation</p>
        )}
      </section>

      {/* Interactive Runbook Checklist */}
      <section className="detail-section">
        <h2>
          Remediation Runbook {runbookSteps.length > 0 && `(${progress}% complete)`}
        </h2>
        {runbookSteps.length === 0 ? (
          <p className="empty">No remediation steps identified yet</p>
        ) : (
          <>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <div className="runbook-checklist">
              {runbookSteps.map((step, idx) => (
                <label
                  key={idx}
                  className={`checklist-item ${step.completed ? "completed" : ""}`}
                >
                  <input
                    type="checkbox"
                    checked={step.completed}
                    onChange={() => toggleStep(idx)}
                  />
                  <span className="step-number">{step.step}.</span>
                  <span className="step-description">{step.description}</span>
                </label>
              ))}
            </div>
          </>
        )}
      </section>

      {/* Error Details */}
      <section className="detail-section">
        <h2>Error Details</h2>
        <pre className="error-message">{incident.errorMessage}</pre>
      </section>

      {/* Confidence Score */}
      {incident.confidenceScore !== null && (
        <section className="detail-section">
          <h2>Diagnosis Confidence</h2>
          <div className="confidence-meter">
            <div
              className="confidence-fill"
              style={{ width: `${incident.confidenceScore * 100}%` }}
            />
            <span className="confidence-value">
              {(incident.confidenceScore * 100).toFixed(0)}%
            </span>
          </div>
        </section>
      )}
    </div>
  );
}
