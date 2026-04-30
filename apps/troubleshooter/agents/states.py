"""
Agentic State Schemas — TypedDict definitions for the LangGraph pipeline.

The state flows through the graph:
  START → Intent → Diagnostic → Retrieval → Response → END
Each node reads and writes to this shared state.
"""
from typing import TypedDict, Optional
from dataclasses import dataclass, field


class TraceStep(TypedDict):
    """A single step in the thought trace."""
    step_order: int
    step_type: str         # intent | diagnostic | retrieval | response
    agent_name: str
    input_summary: str
    output_summary: str
    duration_ms: int
    token_count: int
    tools_used: list


class AgentState(TypedDict):
    """
    Shared state that flows through the LangGraph pipeline.
    Each node reads what it needs and writes its outputs.
    """
    # ── Input ──
    query: str                          # User's original question
    session_id: str                     # Chat session identifier

    # ── Intent Classification ──
    intent: str                         # troubleshoot | status_check | general
    intent_confidence: float            # 0.0 - 1.0
    detected_device: str                # Device name extracted from query
    detected_device_type: str           # Device type (smart_lock, thermostat, etc.)

    # ── Diagnostic Data ──
    device_context: dict                # Full device status from Dashboard API
    diagnostic_data: dict               # Matter node + anomaly data
    error_logs: list                    # Recent error entries

    # ── Retrieval (RAG) ──
    retrieved_docs: list                # List of manual chunks from FAISS
    retrieval_query: str                # Reformulated search query
    retrieval_scores: list              # Similarity scores

    # ── Response ──
    response: str                       # Final assembled response
    sources: list                       # Cited manual sections
    response_chunks: list               # For streaming: list of token chunks

    # ── Observability ──
    traces: list                        # List of TraceStep dicts
    total_tokens: int
    total_duration_ms: int
    error: str                          # Error message if pipeline fails
