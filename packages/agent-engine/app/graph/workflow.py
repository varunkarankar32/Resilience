"""
ResilienceAI — LangGraph Workflow
Full LLM-powered incident triage → tool execution → evaluation loop.

Architecture:
  Router LLM → selects tool based on alert signature
  Tool Execution → runs topology / knowledge_base / log_parser
  Evaluator LLM → scores diagnosis confidence, loops or writes RCA

Ports the JanShakti-AI pattern of LLM enrichment with confidence gating.
"""

import json
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from app.config import settings
from app.tools.topology import fetch_topology
from app.tools.knowledge_base import query_knowledge_base
from app.tools.incident_parser import parse_incident_logs
from app.models.incident import Incident, IncidentStatus
from datetime import datetime


# ── State ──
class IncidentState(TypedDict):
    service_name: str
    environment: str
    severity: str
    error_message: str
    sanitized_logs: str
    topology_upstream: list[str]
    topology_downstream: list[str]
    runbook_matches: list[dict]
    root_cause_analysis: str
    remediation_steps: list[str]
    confidence_score: float
    execution_path: list[str]
    current_query: str
    iteration_count: int
    evaluator_reasoning: str


# ── LLM instances ──
def _get_llm(temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_url,
        temperature=temperature,
        max_tokens=1024,
        request_timeout=45,
    )


# ── Router Node: LLM selects tool ──
ROUTER_SYSTEM_PROMPT = """You are an SRE incident router. Given an alert, select the FIRST tool to invoke.

Available tools:
1. `fetch_topology` — retrieves upstream/downstream microservice dependencies. Use when: alert mentions cascading failures, timeouts, or inter-service calls.
2. `query_knowledge_base` — searches historical runbooks and post-mortems. Use when: error looks familiar (e.g., OOM, connection pool exhaustion, rate limiting).
3. `parse_incident_logs` — sanitizes raw logs for analysis. Use when: raw logs are provided and need cleaning before deeper analysis.

Respond with ONLY a JSON object: {"tool": "<tool_name>", "reasoning": "<one-line reason>"}"""


async def router_node(state: IncidentState) -> IncidentState:
    """LLM-based router: analyzes alert and selects which tool to invoke."""
    state["execution_path"].append("router")
    llm = _get_llm()

    messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Service: {state['service_name']}
Environment: {state['environment']}
Severity: {state['severity']}
Error: {state['error_message']}
Sanitized Logs: {state.get('sanitized_logs', 'N/A')[:500]}"""),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].split("```")[0]
            content = content.replace("json", "").strip()
        selection = json.loads(content)
        state["execution_path"].append(f"router→{selection.get('tool', 'unknown')}")
    except Exception:
        # Fallback: always start with knowledge base if LLM unavailable
        state["execution_path"].append("router→fallback:query_knowledge_base")
        selection = {"tool": "query_knowledge_base", "reasoning": "LLM routing failed, defaulting to knowledge base"}

    state["router_selection"] = selection.get("tool", "query_knowledge_base")
    return state


# ── Tool Execution Nodes ──

async def topology_node(state: IncidentState) -> IncidentState:
    """Execute fetch_topology tool."""
    state["execution_path"].append("tool:fetch_topology")
    try:
        result = await fetch_topology(state["service_name"])
        state["topology_upstream"] = result.upstream
        state["topology_downstream"] = result.downstream
        if not result.found:
            state["execution_path"].append("topology:not_found")
    except Exception as exc:
        state["execution_path"].append(f"topology:error:{str(exc)[:60]}")
    return state


async def knowledge_base_node(state: IncidentState) -> IncidentState:
    """Execute query_knowledge_base tool."""
    state["execution_path"].append("tool:query_knowledge_base")
    query = state.get("current_query", state["error_message"])
    try:
        result = await query_knowledge_base(
            query=query,
            target_service=state["service_name"],
            top_k=5,
        )
        state["runbook_matches"] = [
            {"title": m.title, "content": m.content[:800], "score": m.score}
            for m in result.matches
        ]
        if not result.matches:
            state["execution_path"].append("kb:no_matches")
        else:
            state["execution_path"].append(f"kb:{len(result.matches)}_matches")
    except Exception as exc:
        state["execution_path"].append(f"kb:error:{str(exc)[:60]}")
    return state


async def log_parser_node(state: IncidentState) -> IncidentState:
    """Execute parse_incident_logs tool."""
    state["execution_path"].append("tool:parse_incident_logs")
    raw = state.get("sanitized_logs") or state["error_message"]
    try:
        result = await parse_incident_logs(raw, state["service_name"])
        state["sanitized_logs"] = result.sanitized_logs
        state["execution_path"].append(f"parser:{result.tokens_replaced}_replaced")
    except Exception as exc:
        state["execution_path"].append(f"parser:error:{str(exc)[:60]}")
    return state


# ── Evaluator Node ──
EVALUATOR_SYSTEM_PROMPT = """You are an SRE diagnosis evaluator. Given the accumulated evidence
from topology, runbook matches, and sanitized logs, assess whether you can determine
a root cause analysis with high confidence.

Respond with ONLY a JSON object:
{
  "confidence": <float 0.0-1.0>,
  "root_cause_analysis": "<detailed RCA or empty if confidence < 0.8>",
  "remediation_steps": ["<step 1>", "<step 2>", ...],
  "reasoning": "<one-paragraph reasoning>",
  "needs_more_info": <true|false>,
  "refined_query": "<what to search next if confidence < 0.8>"
}"""


async def evaluator_node(state: IncidentState) -> IncidentState:
    """LLM evaluator: checks if diagnosis is confident enough to finalize."""
    state["execution_path"].append("evaluator")
    llm = _get_llm(temperature=0.1)

    evidence = f"""Service: {state['service_name']}
Environment: {state['environment']}
Severity: {state['severity']}
Error Message: {state['error_message']}

--- Topology ---
Upstream: {state.get('topology_upstream', [])}
Downstream: {state.get('topology_downstream', [])}

--- Runbook Matches ---
{json.dumps(state.get('runbook_matches', []), indent=2)}

--- Sanitized Logs ---
{state.get('sanitized_logs', 'N/A')[:2000]}"""

    messages = [
        SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=evidence),
    ]

    try:
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].split("```")[0]
            content = content.replace("json", "").strip()
        evaluation = json.loads(content)
    except Exception:
        evaluation = {
            "confidence": 0.0,
            "root_cause_analysis": "",
            "remediation_steps": [],
            "reasoning": "LLM evaluation failed",
            "needs_more_info": True,
            "refined_query": state["error_message"],
        }

    state["confidence_score"] = float(evaluation.get("confidence", 0.0))
    state["root_cause_analysis"] = evaluation.get("root_cause_analysis", "")
    state["remediation_steps"] = evaluation.get("remediation_steps", [])
    state["evaluator_reasoning"] = evaluation.get("reasoning", "")
    state["current_query"] = evaluation.get("refined_query", state["error_message"])
    state["needs_more_info"] = evaluation.get("needs_more_info", True)

    return state


# ── Routing Logic ──
def select_tool(state: IncidentState) -> Literal["tool_topology", "tool_knowledge_base", "tool_log_parser"]:
    tool = state.get("router_selection", "query_knowledge_base")
    mapping = {
        "fetch_topology": "tool_topology",
        "query_knowledge_base": "tool_knowledge_base",
        "parse_incident_logs": "tool_log_parser",
    }
    return mapping.get(tool, "tool_knowledge_base")


def should_continue(state: IncidentState) -> Literal["refine", "complete"]:
    confidence = state.get("confidence_score", 0.0)
    max_iterations = 5

    if confidence >= 0.8 or state.get("iteration_count", 0) >= max_iterations:
        state["execution_path"].append("complete")
        return "complete"

    state["iteration_count"] = state.get("iteration_count", 0) + 1
    state["execution_path"].append("refine")
    return "refine"


# ── Graph Builder ──
def build_incident_graph() -> StateGraph:
    workflow = StateGraph(IncidentState)

    workflow.add_node("router", router_node)
    workflow.add_node("tool_topology", topology_node)
    workflow.add_node("tool_knowledge_base", knowledge_base_node)
    workflow.add_node("tool_log_parser", log_parser_node)
    workflow.add_node("evaluator", evaluator_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        select_tool,
        {
            "tool_topology": "tool_topology",
            "tool_knowledge_base": "tool_knowledge_base",
            "tool_log_parser": "tool_log_parser",
        },
    )

    workflow.add_edge("tool_topology", "evaluator")
    workflow.add_edge("tool_knowledge_base", "evaluator")
    workflow.add_edge("tool_log_parser", "evaluator")

    workflow.add_conditional_edges(
        "evaluator",
        should_continue,
        {
            "refine": "router",
            "complete": END,
        },
    )

    return workflow


incident_graph = build_incident_graph()


# ── Orchestrator: run and persist ──
async def run_diagnosis_and_persist(
    service_name: str,
    environment: str,
    severity: str,
    error_message: str,
    raw_logs: str = "",
    incident_id: str | None = None,
) -> dict:
    """Run the full LangGraph diagnosis workflow and write results to MongoDB."""

    initial_state: IncidentState = {
        "service_name": service_name,
        "environment": environment,
        "severity": severity,
        "error_message": error_message,
        "sanitized_logs": raw_logs,
        "topology_upstream": [],
        "topology_downstream": [],
        "runbook_matches": [],
        "root_cause_analysis": "",
        "remediation_steps": [],
        "confidence_score": 0.0,
        "execution_path": [],
        "current_query": error_message,
        "iteration_count": 0,
        "evaluator_reasoning": "",
        "router_selection": "",
    }

    graph = incident_graph.compile()
    result = graph.invoke(initial_state)

    # Persist to MongoDB
    if incident_id:
        from beanie import PydanticObjectId
        try:
            incident = await Incident.get(PydanticObjectId(incident_id))
            if incident:
                incident.root_cause_analysis = result.get("root_cause_analysis", "")
                incident.remediation_steps = result.get("remediation_steps", [])
                incident.confidence_score = result.get("confidence_score", 0.0)
                incident.graph_execution_path = result.get("execution_path", [])
                incident.updated_at = datetime.utcnow()
                if result.get("confidence_score", 0.0) >= 0.8:
                    incident.status = IncidentStatus.TRIAGE
                await incident.save()
        except Exception as exc:
            print(f"[MongoDB] Failed to persist diagnosis: {exc}")

    return {
        "service_name": service_name,
        "root_cause_analysis": result.get("root_cause_analysis", ""),
        "remediation_steps": result.get("remediation_steps", []),
        "confidence_score": result.get("confidence_score", 0.0),
        "execution_path": result.get("execution_path", []),
        "topology_upstream": result.get("topology_upstream", []),
        "topology_downstream": result.get("topology_downstream", []),
        "runbook_matches": result.get("runbook_matches", []),
    }
