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
        
        # Example of specific processing for a 'file_modified' event
        if raw_event.get("type") == "file_modified":
            payload = raw_event.get("payload", {})
            processed_context["summary"] = (
                f"File '{payload.get('path')}' was modified. "
                f"The new content has {len(payload.get('new_content', ''))} characters."
            )
        
        # Specific processing for 'feishu' 'message' event
        elif raw_event.get("source") == "feishu" and raw_event.get("type") == "message":
            payload = raw_event.get("payload", {})
            user = payload.get("user", "Unknown user")
            content = payload.get("content", "")
            processed_context["summary"] = (
                f"New message from {user} in Feishu: '{content}'"
            )
            
        processed_contexts.append(processed_context)

    state['processed_contexts'] = processed_contexts
    return state
