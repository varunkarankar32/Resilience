import express from "express";
import cors from "cors";
import routes from "./routes/index.js";
import { errorHandler } from "./middleware/errorHandler.js";
import { requestLogger } from "./middleware/requestLogger.js";

export function createApp(): express.Application {
  const app = express();

  app.use(cors());
  app.use(express.json({ limit: "1mb" }));
  app.use(requestLogger);

  app.use("/", routes);

  app.use((_req, res) => {
    res.status(404).json({ status: "error", message: "Route not found" });
  });

  app.use(errorHandler);

  return app;
}
