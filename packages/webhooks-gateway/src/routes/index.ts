import { Router } from "express";
import healthRouter from "./health.js";
import alertRouter from "./alerts.js";
import incidentsRouter from "./incidents.js";

const router = Router();

router.use("/health", healthRouter);
router.use("/api/v1/alerts", alertRouter);
router.use("/api/v1/incidents", incidentsRouter);

export default router;
