# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import datetime
import logging
from .graph.state import AgentState

logger = logging.getLogger(__name__)


def process_context(state: AgentState) -> AgentState:
    """
    Processes raw events from the observer into a structured context
    that is more useful for the AI agents.
    """
    logger.info("Processing raw events into context...")

    raw_events = state.get('raw_events')
    if not raw_events:
        # No events to process
        return state

    processed_contexts = []
    for raw_event in raw_events:
        # Enrich the event with a timestamp
        processed_context = {
            "timestamp": datetime.datetime.now().isoformat(),
            "original_event": raw_event
        }

        # Enhanced processing for research-related events
        event_type = raw_event.get("type")
        event_source = raw_event.get("source")
        payload = raw_event.get("payload", {})

        if event_source == "browser" and event_type == "search":
            query = payload.get("query", "")
            url = payload.get("url", "")
            processed_context["summary"] = (
                f"User performed a web search for '{query}' and visited '{url}'. "
                f"This suggests research interest in architectural comparisons and could benefit from detailed analysis."
            )

        elif event_source == "vscode" and event_type == "file_open":
            file_name = payload.get("file", "")
            content = payload.get("content", "")
            processed_context["summary"] = (
                f"User opened file '{file_name}' containing research content about AI markets. "
                f"This indicates active research work that could benefit from comprehensive market analysis."
            )

        elif event_source == "browser" and event_type == "article_view":
            title = payload.get("title", "")
            url = payload.get("url", "")
            processed_context["summary"] = (
                f"User is reading article '{title}' at '{url}' about technology developments. "
                f"This suggests research interest in current technology trends and could benefit from detailed analysis."
            )

        # Example of specific processing for a 'file_modified' event
        elif raw_event.get("type") == "file_modified":
            processed_context["summary"] = (
                f"File '{payload.get('path')}' was modified. "
                f"The new content has {len(payload.get('new_content', ''))} characters."
            )

        # Specific processing for 'feishu' 'message' event
        elif raw_event.get("source") == "feishu" and raw_event.get("type") == "message":
            user = payload.get("user", "Unknown user")
            content = payload.get("content", "")
            processed_context["summary"] = (
                f"New message from {user} in Feishu: '{content}'"
            )

        else:
            # Default processing with research-friendly summary
            processed_context["summary"] = (
                f"User activity detected from {event_source}: {event_type}. "
                f"This activity suggests potential research or analysis opportunity."
            )

        processed_contexts.append(processed_context)

        # Debug logging
        logger.info(f"Processed context: {processed_context['summary']}")

    state['processed_contexts'] = processed_contexts
    return state