import { MongoClient, Db } from "mongodb";
import { config } from "./config.js";

let client: MongoClient | null = null;
let db: Db | null = null;

export async function connectMongo(): Promise<Db> {
  if (db) return db;

  try {
    client = new MongoClient(config.MONGO_URI, {
      serverSelectionTimeoutMS: 5000,
      connectTimeoutMS: 5000,
    });
    await client.connect();
    await client.db().command({ ping: 1 });
    db = client.db();
    console.log("[MongoDB] Connected successfully");
    return db;
  } catch (error) {
    console.warn("[MongoDB] Connection failed — running in degraded mode:", (error as Error).message);
    throw error;
  }
}

export async function disconnectMongo(): Promise<void> {
  if (client) {
    try {
      await client.close();
      client = null;
      db = null;
      console.log("[MongoDB] Disconnected");
    } catch (error) {
      console.warn("[MongoDB] Error during disconnect:", (error as Error).message);
    }
  }
}

export function getDb(): Db {
  if (!db) {
    throw new Error("[MongoDB] Database not connected. Call connectMongo() first.");
  }
  return db;
}
