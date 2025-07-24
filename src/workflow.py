# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from src.graph.builder import build_graph

# This is the entrypoint for the LangGraph Studio.
# It creates a global, runnable graph instance.
graph = build_graph()
