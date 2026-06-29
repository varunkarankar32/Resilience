import { Router } from "express";

const router = Router();

router.get("/health", (_req, res) => {
  res.json({ status: "healthy", service: "webhooks-gateway" });
});

export default router;
