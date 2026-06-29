import { z } from "zod";

export const alertSchema = z.object({
  serviceName: z.string().min(1, "serviceName is required").max(255),
  environment: z.string().min(1, "environment is required").max(100),
  severity: z.enum(["critical", "high", "medium", "low"]),
  errorMessage: z.string().min(1, "errorMessage is required").max(5000),
  rawLogs: z.string().optional().default(""),
});

export type AlertCreate = z.infer<typeof alertSchema>;
