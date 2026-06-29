# ResilienceAI — Event-Driven SRE Incident Commander

**Intelligent microservice incident triage, diagnosis, and remediation powered by LLM agents.**

## Architecture

```
┌──────────────────────┐     ┌───────────────────┐     ┌─────────────────┐
│   webhooks-gateway   │────▶│   agent-engine     │────▶│   dashboard     │
│   (Express + BullMQ) │     │   (FastAPI+LangGr) │     │   (React+Vite)  │
└──────────┬───────────┘     └─────────┬─────────┘     └────────┬────────┘
           │                           │                        │
           └───────────┬───────────────┴────────────────────────┘
                       │
            ┌──────────▼──────────┐
            │   Shared Services   │
            │  MongoDB · Redis    │
            │       Qdrant        │
            └─────────────────────┘
```

## Quick Start

```bash
# 1. Start infrastructure services
docker compose up -d

# 2. Install dependencies
npm install

# 3. Set up Python environment (agent-engine)
cd packages/agent-engine
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cd ../..

# 4. Copy and configure environment
cp .env.template .env
# Edit .env with your LLM API keys

# 5. Start all services
npm run dev
```

## Packages

| Package | Tech Stack | Port | Purpose |
|---------|-----------|------|---------|
| `webhooks-gateway` | Express + TypeScript + BullMQ | 4000 | Alert ingestion, deduplication, queue routing |
| `agent-engine` | FastAPI + LangGraph + Beanie | 8000 | LLM-powered incident diagnosis and remediation |
| `dashboard` | React + Vite + Socket.io | 5173 | Real-time incident investigation interface |

## System Flow

1. **Alert Ingestion** — External monitoring tools POST alerts to `webhooks-gateway`
2. **Deduplication** — 10-second sliding window prevents duplicate alert storms
3. **Queue Routing** — BullMQ (Redis-backed) queues each alert for processing
4. **Agent Diagnosis** — LangGraph LLM workflow analyzes incident with tool chain:
   - `fetch_topology` — Pulls upstream/downstream microservice dependencies
   - `query_knowledge_base` — Semantic runbook search in Qdrant
   - `parse_incident_logs` — Regex-based log sanitization
5. **Real-time Updates** — MongoDB Change Streams → Socket.io → React dashboard
6. **Remediation** — Markdown runbooks rendered as interactive checklists

## Requirements

- **Node.js** >= 20.0.0
- **Python** >= 3.10
- **Docker** >= 24.0.0
- **npm** >= 10.0.0

## License

Proprietary — Internal use only.
