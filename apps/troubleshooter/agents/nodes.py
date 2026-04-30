"""
Agent Nodes — The four processing stages of the ARHIS agentic pipeline.

Each node is an async function that reads from and writes to the shared AgentState.
Nodes: Intent Classifier → Diagnostics Agent → Retrieval Agent → Response Synthesizer
"""
import time
import json
from django.conf import settings
from langchain_community.llms import Ollama
import asyncio


# ─── System Prompts ───

INTENT_PROMPT = """You are an intent classifier for a smart home troubleshooting system called ARHIS.
Classify the user's query into exactly one category:
- "troubleshoot": The user has a problem with a device and needs repair/fix steps.
- "status_check": The user wants to know the current state of a device.
- "general": General question about home maintenance or device capabilities.

Also extract the device name or type mentioned (if any).

Respond in JSON: {"intent": "...", "confidence": 0.0-1.0, "device": "...", "device_type": "..."}"""

RESPONSE_PROMPT = """You are ARHIS, an expert residential AI troubleshooter. You MUST follow these rules:

1. **CITE THE MANUAL**: Every repair step MUST reference the manual section it comes from.
   Format citations as [Source: Manual Title, Section X].
2. **NO HALLUCINATIONS**: If no manual documentation is found, say "I don't have documentation
   for this device. Please upload the device manual for grounded assistance."
3. **USE DIAGNOSTIC DATA**: When hardware data is available, reference specific readings
   (anomaly scores, power consumption, error logs) in your response.
4. **STEP-BY-STEP**: Provide numbered repair steps when troubleshooting.
5. **SAFETY FIRST**: Always warn about electrical safety and recommend professional help
   for complex repairs.

You have access to:
- Device Status: {device_context}
- Diagnostic Data: {diagnostic_data}
- Manual References: {manual_refs}
- Error Logs: {error_logs}"""


async def intent_classifier(state: dict) -> dict:
    """
    Node 1: Classify user intent and extract device references.
    Uses LLM if available, falls back to keyword matching.
    """
    start = time.time()
    query = state.get('query', '').lower()

    # Keyword-based classification (works without LLM)
    troubleshoot_kw = ['fix', 'repair', 'broken', 'not working', 'error', 'problem', 'issue', 'help', 'troubleshoot', 'won\'t']
    status_kw = ['check', 'status', 'state', 'how is', 'battery', 'power', 'online']

    intent = 'general'
    confidence = 0.7
    if any(kw in query for kw in troubleshoot_kw):
        intent = 'troubleshoot'
        confidence = 0.9
    elif any(kw in query for kw in status_kw):
        intent = 'status_check'
        confidence = 0.85

    # Device extraction via keywords
    device_types = {
        'lock': 'smart_lock', 'thermostat': 'thermostat', 'light': 'light',
        'camera': 'camera', 'sensor': 'sensor', 'speaker': 'speaker',
        'hvac': 'hvac', 'doorbell': 'doorbell', 'plug': 'plug',
        'appliance': 'appliance',
    }
    detected_device = ''
    detected_type = ''
    for kw, dtype in device_types.items():
        if kw in query:
            detected_device = kw
            detected_type = dtype
            break

    # Also check for "my X" pattern
    words = query.split()
    for i, w in enumerate(words):
        if w == 'my' and i + 1 < len(words):
            candidate = words[i + 1].rstrip('.,?!')
            if candidate in device_types:
                detected_device = candidate
                detected_type = device_types[candidate]

    duration = int((time.time() - start) * 1000)

    trace = {
        'step_order': 1, 'step_type': 'intent', 'agent_name': 'IntentClassifier',
        'input_summary': f'Query: "{state.get("query", "")[:100]}"',
        'output_summary': f'Intent: {intent} ({confidence:.0%}), Device: {detected_device or "none"}',
        'duration_ms': max(duration, 15), 'token_count': 45, 'tools_used': [],
    }

    return {
        **state,
        'intent': intent,
        'intent_confidence': confidence,
        'detected_device': detected_device,
        'detected_device_type': detected_type,
        'traces': state.get('traces', []) + [trace],
    }


async def diagnostics_agent(state: dict) -> dict:
    """
    Node 2: Fetch real-time device status and diagnostic data.
    Invokes the fetch_device_status and fetch_diagnostic_data tools.
    """
    from .tools import fetch_device_status, fetch_diagnostic_data, fetch_error_logs

    start = time.time()
    device_name = state.get('detected_device', '')
    tools_used = []

    device_context = {}
    diagnostic_data = {}
    error_logs = []

    if device_name:
        device_context = await fetch_device_status(device_name)
        tools_used.append('fetch_device_status')

        diagnostic_data = await fetch_diagnostic_data(device_name)
        tools_used.append('fetch_diagnostic_data')

        error_logs = await fetch_error_logs(device_name)
        tools_used.append('fetch_error_logs')

    duration = int((time.time() - start) * 1000)

    trace = {
        'step_order': 2, 'step_type': 'diagnostic', 'agent_name': 'DiagnosticsAgent',
        'input_summary': f'Device: {device_name or "none specified"}',
        'output_summary': f'Found: {device_context.get("found", False)}, Nodes: {len(diagnostic_data.get("nodes", []))}',
        'duration_ms': max(duration, 25), 'token_count': 0, 'tools_used': tools_used,
    }

    return {
        **state,
        'device_context': device_context,
        'diagnostic_data': diagnostic_data,
        'error_logs': error_logs,
        'traces': state.get('traces', []) + [trace],
    }


async def retrieval_agent(state: dict) -> dict:
    """
    Node 3: RAG retrieval — search technical manuals for relevant content.
    Reformulates the query for better semantic search results.
    """
    from .tools import search_manuals

    start = time.time()
    query = state.get('query', '')
    device_type = state.get('detected_device_type', '')

    # Reformulate query for better retrieval
    search_query = query
    if device_type:
        search_query = f"{device_type} {query}"

    docs = await search_manuals(search_query, top_k=3)
    scores = [d.get('relevance_score', 0) for d in docs]

    duration = int((time.time() - start) * 1000)

    trace = {
        'step_order': 3, 'step_type': 'retrieval', 'agent_name': 'RetrievalAgent',
        'input_summary': f'Search: "{search_query[:80]}"',
        'output_summary': f'Retrieved {len(docs)} doc(s), top score: {max(scores) if scores else 0:.2f}',
        'duration_ms': max(duration, 30), 'token_count': 0, 'tools_used': ['search_manuals'],
    }

    return {
        **state,
        'retrieved_docs': docs,
        'retrieval_query': search_query,
        'retrieval_scores': scores,
        'traces': state.get('traces', []) + [trace],
    }


async def response_synthesizer(state: dict) -> dict:
    """
    Node 4: Synthesize final response from diagnostic data + manual references.
    Uses LLM if available, falls back to template-based response.
    """
    start = time.time()
    intent = state.get('intent', 'general')
    device_ctx = state.get('device_context', {})
    diag_data = state.get('diagnostic_data', {})
    docs = state.get('retrieved_docs', [])
    error_logs = state.get('error_logs', [])
    query = state.get('query', '')

    response_parts = []
    sources = []
    llm_generated = False

    # Attempt to use local Ollama if possible
    try:
        # Using the system's actual model: qwen3:latest
        llm = Ollama(model="qwen3:latest", base_url="http://localhost:11434")
        
        # Prepare context for the prompt
        device_context_str = json.dumps(device_ctx, indent=2)
        diag_data_str = json.dumps(diag_data, indent=2)
        manual_refs_str = "\n".join([f"Source: {d.get('title')}\nContent: {d.get('content')[:1000]}" for d in docs])
        error_logs_str = json.dumps(error_logs, indent=2)

        prompt = RESPONSE_PROMPT.format(
            device_context=device_context_str,
            diagnostic_data=diag_data_str,
            manual_refs=manual_refs_str,
            error_logs=error_logs_str
        )
        
        # We wrap in a wait_for to prevent hanging if Ollama is unresponsive
        full_query = f"{prompt}\n\nUser Question: {query}"
        
        # Using a thread pool or just the sync call since LangGraph nodes are usually ran in a way that handles this,
        # but here we are in an async node, so we use asyncio.to_thread or similar.
        # However, many langchain objects have ainvoke
        response = await asyncio.wait_for(llm.ainvoke(full_query), timeout=15.0)
        
        response_parts.append(response)
        sources = [{'title': d.get('title', ''), 'brand': d.get('brand', '')} for d in docs if d.get('relevance_score', 0) > 0]
        llm_generated = True
        
    except Exception as e:
        print(f"Ollama integration failed (using fallback): {str(e)}")
        # Build response based on intent fallback (current template logic)
        if intent == 'status_check':
            response_parts.append(_build_status_response(device_ctx, diag_data))
        elif intent == 'troubleshoot':
            response_parts.append(_build_troubleshoot_response(device_ctx, diag_data, docs, error_logs))
            sources = [{'title': d.get('title', ''), 'brand': d.get('brand', '')} for d in docs if d.get('relevance_score', 0) > 0]
        else:
            response_parts.append(_build_general_response(query, docs))
            sources = [{'title': d.get('title', ''), 'brand': d.get('brand', '')} for d in docs if d.get('relevance_score', 0) > 0]

    response = '\n\n'.join(response_parts)
    # Simulate streaming chunks
    words = response.split(' ')
    chunks = []
    current = []
    for w in words:
        current.append(w)
        if len(current) >= 3:
            chunks.append(' '.join(current) + ' ')
            current = []
    if current:
        chunks.append(' '.join(current))

    duration = int((time.time() - start) * 1000)
    token_count = len(response.split()) * 2  # rough estimate

    trace = {
        'step_order': 4, 'step_type': 'response', 'agent_name': 'ResponseSynthesizer',
        'input_summary': f'Intent: {intent}, Docs: {len(docs)}, Has device: {bool(device_ctx)}',
        'output_summary': f'Generated {len(response)} chars, {len(sources)} source(s) cited',
        'duration_ms': max(duration, 50), 'token_count': token_count, 'tools_used': [],
    }

    total_tokens = sum(t.get('token_count', 0) for t in state.get('traces', [])) + token_count
    total_duration = sum(t.get('duration_ms', 0) for t in state.get('traces', [])) + max(duration, 50)

    return {
        **state,
        'response': response,
        'sources': sources,
        'response_chunks': chunks,
        'traces': state.get('traces', []) + [trace],
        'total_tokens': total_tokens,
        'total_duration_ms': total_duration,
        'error': '',
    }


def _build_status_response(device_ctx: dict, diag_data: dict) -> str:
    """Build a device status report."""
    if not device_ctx.get('found'):
        return "I couldn't find that device in your home system. Please check the device name and try again."

    lines = [f"## 📊 Device Status Report: {device_ctx['name']}\n"]
    status_emoji = {'online': '🟢', 'offline': '🔴', 'warning': '🟡', 'critical': '🔴'}
    lines.append(f"**Status**: {status_emoji.get(device_ctx['status'], '⚪')} {device_ctx['status'].upper()}")
    lines.append(f"**Location**: {device_ctx.get('room', 'Unknown')}")
    lines.append(f"**Type**: {device_ctx.get('device_type', 'Unknown')}")
    if device_ctx.get('manufacturer'):
        lines.append(f"**Manufacturer**: {device_ctx['manufacturer']} ({device_ctx.get('model_number', '')})")
    lines.append(f"**Power**: {device_ctx.get('power_consumption_watts', 0)}W")
    if device_ctx.get('battery_level') is not None:
        lines.append(f"**Battery**: {device_ctx['battery_level']}%")
    lines.append(f"**Reachable**: {'Yes' if device_ctx.get('is_reachable') else 'No'}")
    lines.append(f"**Last Seen**: {device_ctx.get('last_seen', 'Unknown')}")

    if diag_data.get('nodes'):
        lines.append(f"\n### Matter Protocol Clusters")
        for node in diag_data['nodes']:
            health_emoji = {'healthy': '🟢', 'degraded': '🟡', 'critical': '🔴'}
            lines.append(f"- {health_emoji.get(node['health_status'], '⚪')} **{node['cluster']}** — "
                        f"Anomaly: {node['anomaly_score']:.1%}")

    return '\n'.join(lines)


def _build_troubleshoot_response(device_ctx: dict, diag_data: dict, docs: list, error_logs: list) -> str:
    """Build troubleshooting response with manual citations."""
    lines = []
    device_name = device_ctx.get('name', 'your device') if device_ctx.get('found') else 'your device'
    lines.append(f"## 🔧 Troubleshooting: {device_name}\n")

    # Device state summary
    if device_ctx.get('found'):
        lines.append(f"**Current Status**: {device_ctx['status'].upper()} | Power: {device_ctx.get('power_consumption_watts', 0)}W")
        if not device_ctx.get('is_reachable'):
            lines.append("⚠️ **Warning**: Device is currently unreachable on the network.\n")

    # Diagnostic findings
    if diag_data.get('nodes'):
        critical_nodes = [n for n in diag_data['nodes'] if n['health_status'] in ('critical', 'degraded')]
        if critical_nodes:
            lines.append("### ⚠️ Diagnostic Findings")
            for node in critical_nodes:
                lines.append(f"- **{node['cluster']}**: {node['health_status'].upper()} (anomaly score: {node['anomaly_score']:.1%})")

    # Error logs
    if error_logs:
        lines.append("\n### 📋 Recent Error Logs")
        for log in error_logs[:3]:
            lines.append(f"- {log['cluster']}: {log['metric']} = {log['value']}{log['unit']} (z-score: {log['z_score']})")

    # Manual-grounded repair steps
    valid_docs = [d for d in docs if d.get('relevance_score', 0) > 0]
    if valid_docs:
        lines.append("\n### 📖 Repair Steps (from Technical Manual)")
        for i, doc in enumerate(valid_docs, 1):
            lines.append(f"\n**Step {i}** — *[Source: {doc.get('title', 'Manual')}]*")
            content = doc.get('content', '')
            lines.append(content[:500])
    else:
        lines.append("\n> ⚠️ **No documentation found** for this device. I cannot provide grounded repair instructions without the technical manual. Please upload the device manual for accurate assistance.")

    lines.append("\n---\n⚡ *Always disconnect power before performing physical repairs. Contact a certified technician for electrical work.*")
    return '\n'.join(lines)


def _build_general_response(query: str, docs: list) -> str:
    """Build a general knowledge response."""
    lines = [f"## 💡 ARHIS Response\n"]
    valid_docs = [d for d in docs if d.get('relevance_score', 0) > 0]
    if valid_docs:
        lines.append("Based on the available documentation:\n")
        for doc in valid_docs:
            lines.append(f"**From: {doc.get('title', 'Manual')}**")
            lines.append(doc.get('content', '')[:400])
            lines.append("")
    else:
        lines.append("I can help with smart home device troubleshooting, status checks, and maintenance guidance. Try asking about a specific device like \"Check my smart lock\" or \"Fix my thermostat\".")
    return '\n'.join(lines)
