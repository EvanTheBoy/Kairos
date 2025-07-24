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
    
    # Initial state is empty, the observer will generate the first event
    initial_state = {}
    
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
