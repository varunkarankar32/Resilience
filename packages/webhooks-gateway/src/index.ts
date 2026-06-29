import "dotenv/config";
import { config } from "./config.js";
import { createApp } from "./app.js";
import { connectMongo, disconnectMongo } from "./lib/mongo.js";
import { startWorker } from "./queue/index.js";
import { createServer } from "http";
import { Server as SocketIOServer } from "socket.io";

async function bootstrap(): Promise<void> {
  console.log("=".repeat(60));
  console.log("  ResilienceAI — Webhooks Gateway");
  console.log("=".repeat(60));

  try {
    await connectMongo();
  } catch (error) {
    console.warn(
      "[Gateway] MongoDB unavailable — alert ingestion will function but persistence is degraded"
    );
  }

  const worker = startWorker();

  const app = createApp();
  const server = createServer(app);

  // ── Socket.io with CORS for dashboard ──
  const io = new SocketIOServer(server, {
    path: "/socket.io",
    cors: {
      origin: "*",
      methods: ["GET", "POST"],
    },
    transports: ["websocket", "polling"],
  });

  io.on("connection", (socket) => {
    console.log(`[Socket.io] Client connected: ${socket.id}`);

    socket.on("disconnect", (reason) => {
      console.log(`[Socket.io] Client disconnected: ${socket.id} (${reason})`);
    });
  });

  // ── MongoDB Change Streams → Socket.io ──
  try {
    const db = (await import("./lib/mongo.js")).getDb();
    const changeStream = db.collection("incidents").watch(
      [{ $match: { operationType: { $in: ["update", "replace", "insert"] } } }],
      { fullDocument: "updateLookup" }
    );

    changeStream.on("change", (change) => {
      const doc = change.fullDocument as Record<string, unknown> | undefined;
      if (!doc) return;

      const payload = {
        incidentId: doc._id?.toString(),
        serviceName: doc.service_name,
        status: doc.status,
        rootCauseAnalysis: doc.root_cause_analysis || null,
        remediationSteps: doc.remediation_steps || [],
        confidenceScore: doc.confidence_score ?? null,
        graphExecutionPath: doc.graph_execution_path || [],
        blastRadius: {
          upstream: doc.blast_radius_upstream || [],
          downstream: doc.blast_radius_downstream || [],
        },
      };

      io.emit("incident-update", payload);
      console.log(`[ChangeStream] Broadcast incident-update for ${payload.serviceName} (${payload.incidentId})`);
    });

    changeStream.on("error", (err) => {
      console.error("[ChangeStream] Error:", err.message);
    });

    console.log("[ChangeStream] Watching incidents collection for real-time updates");
  } catch (err) {
    console.warn("[ChangeStream] Could not initialize — MongoDB may not be available:", (err as Error).message);
  }

  server.listen(config.WEBHOOKS_GATEWAY_PORT, () => {
    console.log(`[Gateway] Listening on http://0.0.0.0:${config.WEBHOOKS_GATEWAY_PORT}`);
    console.log(`[Gateway] Alert endpoint: POST http://localhost:${config.WEBHOOKS_GATEWAY_PORT}/api/v1/alerts`);
    console.log(`[Gateway] Socket.io: ws://localhost:${config.WEBHOOKS_GATEWAY_PORT}/socket.io`);
  });

  const shutdown = async (signal: string) => {
    console.log(`\n[Gateway] Received ${signal} — shutting down gracefully...`);
    await worker.close();
    io.close();
    await disconnectMongo();
    server.close(() => {
      console.log("[Gateway] HTTP server closed");
      process.exit(0);
    });
  };

  process.on("SIGINT", () => shutdown("SIGINT"));
  process.on("SIGTERM", () => shutdown("SIGTERM"));
}

bootstrap().catch((error) => {
  console.error("[Gateway] Fatal bootstrap error:", error);
  process.exit(1);
});
