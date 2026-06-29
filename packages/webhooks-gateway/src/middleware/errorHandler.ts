import { Request, Response, NextFunction } from "express";

export function errorHandler(err: Error, req: Request, res: Response, _next: NextFunction): void {
  console.error(`[Error] ${req.method} ${req.path}:`, err.message);

  if (res.headersSent) {
    return;
  }

  const statusCode = (err as Record<string, unknown>).statusCode as number | undefined;
  res.status(statusCode || 500).json({
    status: "error",
    message: err.message || "Internal server error",
    path: req.path,
  });
}
