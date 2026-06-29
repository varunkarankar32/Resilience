import { Router, Request, Response, NextFunction } from "express";
import { getDb } from "../lib/mongo.js";

const router = Router();

router.get("/", async (_req: Request, res: Response, next: NextFunction) => {
  try {
    const db = getDb();
    const docs = await db
      .collection("incidents")
      .find({})
      .sort({ created_at: -1 })
      .limit(100)
      .toArray();

    const incidents = docs.map((doc) => ({
      id: doc._id.toString(),
      incidentId: doc._id.toString(),
      serviceName: doc.service_name,
      environment: doc.environment,
      status: doc.status,
      severity: doc.severity,
      errorMessage: doc.error_message || "",
      rootCauseAnalysis: doc.root_cause_analysis || null,
      remediationSteps: doc.remediation_steps || [],
      confidenceScore: doc.confidence_score ?? null,
      graphExecutionPath: doc.graph_execution_path || [],
      blastRadius: {
        upstream: doc.blast_radius_upstream || [],
        downstream: doc.blast_radius_downstream || [],
      },
      alerts: (doc.alerts || []).slice(0, 10),
      alertCount: (doc.alerts || []).length,
      createdAt: doc.created_at?.toISOString() || "",
    }));

    res.json({ incidents, total: incidents.length });
  } catch (error) {
    next(error);
  }
});

router.get("/:incidentId", async (req: Request, res: Response, next: NextFunction) => {
  try {
    const db = getDb();
    const { ObjectId } = await import("mongodb");

    let doc;
    try {
      doc = await db
        .collection("incidents")
        .findOne({ _id: new ObjectId(req.params.incidentId) });
    } catch {
      res.status(400).json({ status: "error", message: "Invalid incident ID format" });
      return;
    }

    if (!doc) {
      res.status(404).json({ status: "error", message: "Incident not found" });
      return;
    }

    res.json({
      incidentId: doc._id.toString(),
      serviceName: doc.service_name,
      environment: doc.environment,
      status: doc.status,
      severity: doc.severity,
      errorMessage: doc.error_message || "",
      rootCauseAnalysis: doc.root_cause_analysis || null,
      remediationSteps: doc.remediation_steps || [],
      confidenceScore: doc.confidence_score ?? null,
      graphExecutionPath: doc.graph_execution_path || [],
      blastRadius: {
        upstream: doc.blast_radius_upstream || [],
        downstream: doc.blast_radius_downstream || [],
      },
      alerts: (doc.alerts || []).map((a: Record<string, unknown>) => ({
        timestamp: a.timestamp,
        log: a.log,
      })),
      createdAt: doc.created_at?.toISOString() || "",
      updatedAt: doc.updated_at?.toISOString() || "",
    });
  } catch (error) {
    next(error);
  }
});

export default router;
