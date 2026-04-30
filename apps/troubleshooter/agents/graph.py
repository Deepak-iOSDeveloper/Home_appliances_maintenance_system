"""
LangGraph State Machine — The ARHIS agentic pipeline.

Graph topology:
  START → intent_classifier
      → IF troubleshoot: diagnostics_agent → retrieval_agent → response_synthesizer
      → IF status_check: diagnostics_agent → response_synthesizer
      → IF general: retrieval_agent → response_synthesizer
  → END
"""
from .nodes import (
    intent_classifier,
    diagnostics_agent,
    retrieval_agent,
    response_synthesizer,
)


def route_by_intent(state: dict) -> str:
    """Conditional edge: route based on classified intent."""
    intent = state.get('intent', 'general')
    if intent == 'troubleshoot':
        return 'diagnostics_agent'
    elif intent == 'status_check':
        return 'diagnostics_agent_only'
    else:
        return 'retrieval_agent_only'


def route_after_diagnostic(state: dict) -> str:
    """After diagnostics, troubleshoot goes to retrieval; status_check goes to response."""
    intent = state.get('intent', 'general')
    if intent == 'troubleshoot':
        return 'retrieval_agent'
    return 'response_synthesizer'


async def run_agent_graph(query: str, session_id: str) -> dict:
    """
    Execute the full agentic pipeline.
    Returns the final state with response, sources, and traces.

    This is a manual graph execution that mirrors LangGraph topology
    but works without the langgraph dependency for maximum compatibility.
    """
    # Initialize state
    state = {
        'query': query,
        'session_id': session_id,
        'intent': '',
        'intent_confidence': 0.0,
        'detected_device': '',
        'detected_device_type': '',
        'device_context': {},
        'diagnostic_data': {},
        'error_logs': [],
        'retrieved_docs': [],
        'retrieval_query': '',
        'retrieval_scores': [],
        'response': '',
        'sources': [],
        'response_chunks': [],
        'traces': [],
        'total_tokens': 0,
        'total_duration_ms': 0,
        'error': '',
    }

    try:
        # Step 1: Intent Classification (always runs)
        state = await intent_classifier(state)
        intent = state.get('intent', 'general')

        if intent == 'troubleshoot':
            # Full pipeline: diagnostics → retrieval → response
            state = await diagnostics_agent(state)
            state = await retrieval_agent(state)
            state = await response_synthesizer(state)
        elif intent == 'status_check':
            # Status: diagnostics → response (skip retrieval)
            state = await diagnostics_agent(state)
            state = await response_synthesizer(state)
        else:
            # General: retrieval → response (skip diagnostics)
            state = await retrieval_agent(state)
            state = await response_synthesizer(state)

    except Exception as e:
        state['error'] = str(e)
        state['response'] = f"I encountered an error while processing your request: {str(e)}"

    return state
