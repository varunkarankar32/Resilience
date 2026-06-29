import { Queue, Worker } from "bullmq";
import { config } from "../config.js";
import { connectMongo, getDb } from "../lib/mongo.js";
import { httpClient } from "../lib/httpClient.js";
import crypto from "crypto";

let alertQueue: Queue | null = null;

export function getAlertQueue(): Queue {
  if (!alertQueue) {
    alertQueue = new Queue("alert-processing", {
      connection: { url: config.REDIS_URI },
      defaultJobOptions: {
        attempts: 3,
        backoff: { type: "exponential", delay: 1000 },
        removeOnComplete: 100,
        removeOnFail: 50,
      },
    });
    console.log("[BullMQ] Alert queue initialized");
  }
  return alertQueue;
}

function buildDedupKey(serviceName: string, errorSignature: string): string {
  const hash = crypto.createHash("sha256").update(errorSignature).digest("hex").slice(0, 16);
  return `dedup:${serviceName}:${hash}`;
}

function sanitizeErrorSignature(errorMessage: string): string {
  return errorMessage
    .replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?/g, "")
    .replace(/\b\d{10,13}\b/g, "")
    .replace(/0x[0-9a-fA-F]{6,16}/g, "")
    .replace(/\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b/g, "")
    .replace(/\b(?:\d{1,3}\.){3}\d{1,3}\b/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 512);
}

interface AlertJobData {
  alertId: string;
  receivedAt: string;
  serviceName: string;
  environment: string;
  severity: string;
  errorMessage: string;
  rawLogs?: string;
}

export function startWorker(): Worker {
  const worker = new Worker(
    "alert-processing",
    async (job) => {
      const data = job.data as AlertJobData;
      const { serviceName, severity, errorMessage, rawLogs } = data;

      console.log(`[Worker] Processing alert for ${serviceName} (job ${job.id})`);

      let db;
      try {
        db = await connectMongo();
      } catch {
        console.warn(`[Worker] MongoDB unavailable — alert ${data.alertId} will be retried`);
        throw new Error("MongoDB connection failed");
      }

      const errorSignature = sanitizeErrorSignature(errorMessage);

      // --- DEDUPLICATION: 10-second sliding window ---
      let isDuplicate = false;
      try {
        const IORedis = (await import("ioredis")).default;
        const dedupRedis = new IORedis(config.REDIS_URI, { maxRetriesPerRequest: null });

        const dedupKey = buildDedupKey(serviceName, errorSignature);
        const existing = await dedupRedis.get(dedupKey);

        if (existing) {
          isDuplicate = true;
          console.log(`[Worker] Duplicate alert detected for ${serviceName} (${dedupKey}) — appending to existing incident`);
        } else {
          await dedupRedis.set(dedupKey, data.alertId, "EX", config.DEDUP_WINDOW_SECONDS);
          console.log(`[Worker] New alert for ${serviceName} — dedup key set with ${config.DEDUP_WINDOW_SECONDS}s TTL`);
        }

        await dedupRedis.quit();
      } catch (redisError) {
        console.warn("[Worker] Redis dedup check failed — treating as new alert:", (redisError as Error).message);
      }

      // --- Incident Management ---
      if (isDuplicate) {
        const existingIncident = await db.collection("incidents").findOneAndUpdate(
          { service_name: serviceName, status: { $ne: "Resolved" } },
          {
            $push: {
              alerts: {
                timestamp: new Date(),
                log: rawLogs || errorMessage,
              },
            },
            $set: { updated_at: new Date() },
          },
          { returnDocument: "after", sort: { created_at: -1 } }
        );

        if (existingIncident) {
          console.log(`[Worker] Log appended to incident ${existingIncident._id}`);
        }

        return {
          processed: true,
          jobId: job.id,
          deduplicated: true,
          serviceName,
          existingIncidentId: existingIncident?._id?.toString(),
        };
      }

      // --- NEW INCIDENT: Create MongoDB record ---
      const incidentDoc = {
        service_name: serviceName,
        environment: data.environment,
        status: "Investigating",
        severity,
        alerts: [
          {
            timestamp: new Date(),
            log: rawLogs || errorMessage,
          },
        ],
        error_message: errorMessage,
        sanitized_signature: errorSignature,
        root_cause_analysis: null,
        remediation_steps: [],
        graph_execution_path: [],
        confidence_score: null,
        created_at: new Date(),
        updated_at: new Date(),
      };

      const result = await db.collection("incidents").insertOne(incidentDoc);
      const incidentId = result.insertedId.toString();
      console.log(`[Worker] New incident created: ${incidentId} for ${serviceName}`);

      // --- Agent Engine Call ---
      try {
        const diagnosisResult = await httpClient.post<Record<string, unknown>, Record<string, unknown>>(
          "/api/v1/diagnose",
          {
            serviceName,
            environment: data.environment,
            severity,
            errorMessage,
            rawLogs: rawLogs || "",
          }
        );
        console.log(`[Worker] Agent engine diagnosis initiated for ${serviceName}:`, diagnosisResult);
      } catch (agentError) {
        console.warn(`[Worker] Agent engine call failed for ${serviceName}:`, (agentError as Error).message);
      }

      return {
        processed: true,
        jobId: job.id,
        deduplicated: false,
        serviceName,
        incidentId,
      };
    },
    {
      connection: { url: config.REDIS_URI },
      concurrency: 5,
    }
  );

  worker.on("completed", (job, result) => {
    console.log(`[Worker] Job ${job.id} completed:`, JSON.stringify(result), "\n");
  });

  worker.on("failed", (job, err) => {
    console.error(`[Worker] Job ${job?.id} failed:`, err.message);
  });

  console.log("[BullMQ] Worker started with deduplication (10s window)");
  return worker;
}
