# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import logging
from .graph.state import AgentState

logger = logging.getLogger(__name__)


def observe(state: AgentState) -> AgentState:
    """
    Observes the environment for events.
    In a real implementation, this would monitor data sources like file systems,
    IDE events, or APIs.

    For now, we'll simulate receiving events that would trigger research tasks.
    """
    logger.info("Observing environment...")

    # Mock data: Simulate events that would trigger research tasks
    mock_events = [
        {
            "source": "browser",
            "type": "search",
            "payload": {
                "user": "User",
                "query": "Eiffel Tower vs Burj Khalifa height comparison",
                "url": "https://example.com/architecture-comparison"
            }
        },
        {
            "source": "vscode",
            "type": "file_open",
            "payload": {
                "user": "Developer",
                "file": "ai_market_research.md",
                "content": "# AI Market Research\n\nNeed to research current state of artificial intelligence market in 2025..."
            }
        },
        {
            "source": "browser",
            "type": "article_view",
            "payload": {
                "user": "User",
                "title": "Solar Energy Technology Advances",
                "url": "https://example.com/solar-tech-2025",
                "content": "Recent developments in solar panel efficiency..."
            }
        }
    ]

    state['raw_events'] = mock_events
    return state