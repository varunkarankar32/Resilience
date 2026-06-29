import { z } from "zod";

const envSchema = z.object({
  WEBHOOKS_GATEWAY_PORT: z.string().default("4000").transform(Number),
  MONGO_URI: z.string().default("mongodb://localhost:27017/resilienceai?replicaSet=rs0"),
  REDIS_URI: z.string().default("redis://localhost:6379"),
  AGENT_ENGINE_URL: z.string().default("http://localhost:8000"),
  DEDUP_WINDOW_SECONDS: z.string().default("10").transform(Number),
  JWT_SECRET: z.string().default("change-this-in-production"),
});

const raw = {
  WEBHOOKS_GATEWAY_PORT: process.env.WEBHOOKS_GATEWAY_PORT,
  MONGO_URI: process.env.MONGO_URI,
  REDIS_URI: process.env.REDIS_URI,
  AGENT_ENGINE_URL: process.env.AGENT_ENGINE_URL,
  DEDUP_WINDOW_SECONDS: process.env.DEDUP_WINDOW_SECONDS,
  JWT_SECRET: process.env.JWT_SECRET,
};

const parsed = envSchema.safeParse(raw);
if (!parsed.success) {
  console.error("[Config] Invalid environment variables:", parsed.error.flatten().fieldErrors);
  process.exit(1);
}

export const config = Object.freeze(parsed.data);
