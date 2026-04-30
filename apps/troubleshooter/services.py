"""
Troubleshooter Service Layer — Facade for the agentic pipeline.

This is the single entry point that Django views/consumers use
to invoke the AI troubleshooter. Handles persistence of messages,
traces, and metrics.
"""
import asyncio
import time
from typing import AsyncGenerator
from asgiref.sync import sync_to_async

from .agents.graph import run_agent_graph
from .models import ChatSession, Message


async def run_troubleshooter(session_id: str, query: str) -> AsyncGenerator[dict, None]:
    """
    Run the full troubleshooting pipeline and yield streaming chunks.

    Yields dicts with keys:
      - type: 'chunk' | 'sources' | 'trace' | 'done' | 'error'
      - content: the payload

    Usage (in WebSocket consumer):
        async for event in run_troubleshooter(session_id, query):
            await self.send(json.dumps(event))
    """
    # Persist user message
    session = await _get_or_create_session(session_id)
    await _save_message(session, 'user', query)

    # Run the agentic pipeline
    try:
        state = await run_agent_graph(query, session_id)
    except Exception as e:
        yield {'type': 'error', 'content': f'Pipeline error: {str(e)}'}
        return

    # Stream response chunks
    chunks = state.get('response_chunks', [])
    if chunks:
        for chunk in chunks:
            yield {'type': 'chunk', 'content': chunk}
            await asyncio.sleep(0.03)  # Simulate streaming delay
    else:
        yield {'type': 'chunk', 'content': state.get('response', 'No response generated.')}

    # Send sources
    sources = state.get('sources', [])
    yield {'type': 'sources', 'content': sources}

    # Send thought traces
    traces = state.get('traces', [])
    yield {'type': 'trace', 'content': traces}

    # Persist assistant message
    await _save_message(
        session, 'assistant',
        state.get('response', ''),
        sources=sources,
        metadata={
            'intent': state.get('intent', ''),
            'device': state.get('detected_device', ''),
            'total_tokens': state.get('total_tokens', 0),
            'total_duration_ms': state.get('total_duration_ms', 0),
        }
    )

    # Persist traces to observability
    await _save_traces(session, traces, state)

    # Signal completion
    yield {
        'type': 'done',
        'content': {
            'session_id': session_id,
            'intent': state.get('intent', ''),
            'total_tokens': state.get('total_tokens', 0),
            'total_duration_ms': state.get('total_duration_ms', 0),
        }
    }


@sync_to_async
def _get_or_create_session(session_id: str):
    session, _ = ChatSession.objects.get_or_create(
        session_id=session_id,
        defaults={'title': 'New Session'}
    )
    return session


@sync_to_async
def _save_message(session, role, content, sources=None, metadata=None):
    return Message.objects.create(
        session=session,
        role=role,
        content=content,
        sources=sources or [],
        metadata=metadata or {},
        token_count=len(content.split()) * 2,
    )


@sync_to_async
def _save_traces(session, traces, state):
    """Persist thought traces and session metrics to observability models."""
    from apps.observability.models import ThoughtTrace, SessionMetric

    for trace in traces:
        ThoughtTrace.objects.create(
            session=session,
            step_order=trace.get('step_order', 0),
            step_type=trace.get('step_type', 'intent'),
            agent_name=trace.get('agent_name', ''),
            input_summary=trace.get('input_summary', ''),
            output_summary=trace.get('output_summary', ''),
            duration_ms=trace.get('duration_ms', 0),
            token_count=trace.get('token_count', 0),
            tools_used=trace.get('tools_used', []),
        )

    # Aggregate session metrics
    durations = [t.get('duration_ms', 0) for t in traces]
    sorted_d = sorted(durations)
    p95_idx = max(0, int(len(sorted_d) * 0.95) - 1)
    p95 = sorted_d[p95_idx] if sorted_d else 0
    total_tokens = state.get('total_tokens', 0)
    cost = total_tokens * 0.00001  # Rough cost estimate

    SessionMetric.objects.update_or_create(
        session=session,
        defaults={
            'total_latency_ms': state.get('total_duration_ms', 0),
            'p95_latency_ms': p95,
            'total_tokens': total_tokens,
            'prompt_tokens': int(total_tokens * 0.6),
            'completion_tokens': int(total_tokens * 0.4),
            'estimated_cost_usd': cost,
            'steps_count': len(traces),
            'retrieval_count': sum(1 for t in traces if t.get('step_type') == 'retrieval'),
            'tools_invoked': sum(len(t.get('tools_used', [])) for t in traces),
        }
    )
