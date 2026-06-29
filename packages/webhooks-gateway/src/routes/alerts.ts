import { Router, Request, Response, NextFunction } from "express";
import { alertSchema, type AlertCreate } from "../schemas/alert.js";
import { validate } from "../middleware/validate.js";
import { getAlertQueue } from "../queue/index.js";
import { v4 as uuidv4 } from "uuid";

const router = Router();

router.post(
  "/",
  validate(alertSchema),
  async (req: Request, res: Response, next: NextFunction) => {
    try {
      const payload = req.body as AlertCreate;
      const queue = getAlertQueue();

      const job = await queue.add("alert-ingest", {
        alertId: uuidv4(),
        receivedAt: new Date().toISOString(),
        serviceName: payload.serviceName,
        environment: payload.environment,
        severity: payload.severity,
        errorMessage: payload.errorMessage,
        rawLogs: payload.rawLogs,
      });

      res.status(202).json({
        status: "accepted",
        message: "Alert received and queued for processing",
        alertId: job.data.alertId,
        jobId: job.id,
        serviceName: payload.serviceName,
        severity: payload.severity,
      });
    } catch (error) {
      if ((error as Error).message?.includes("Redis")) {
        res.status(503).json({
          status: "error",
          message: "Queue service unavailable — alert cannot be processed",
          detail: (error as Error).message,
        });
        return;
      }
      next(error);
    }
  }
);

export default router;
