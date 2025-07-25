# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import argparse
from src.graph.builder import build_graph
from src.utils.logging import setup_logging, enable_debug_logging


def main(debug=False):
    """
    Main function to run the Kairos agent.
    """
    setup_logging()
    if debug:
        enable_debug_logging()

    graph = build_graph()

    # Initialize state with required fields
    initial_state = {
        "raw_events": [],
        "processed_contexts": None,
        "is_significant_event": False,
        "intent_candidates": None,
        "selected_task": None,
        "approved_tasks": [],
        "task_result": None,
        "final_feedback": None,
        "messages": []  # Initialize messages as empty list
    }

    # Stream the graph execution
    for s in graph.stream(initial_state):
        # The final output of the graph is the state of the last node
        # We don't need to print every step here as nodes do it themselves
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the Kairos Proactive AI Partner.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    main(debug=args.debug)