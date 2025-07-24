# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from src.graph.builder import build_graph

def main():
    """
    Main function to run the Kairos agent.
    """
    graph = build_graph()
    
    # Initial state is empty, the observer will generate the first event
    initial_state = {}
    
    # Stream the graph execution
    for s in graph.stream(initial_state):
        # The final output of the graph is the state of the last node
        # We don't need to print every step here as nodes do it themselves
        pass

if __name__ == "__main__":
    main()
