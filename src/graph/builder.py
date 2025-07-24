# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from langgraph.graph import StateGraph, END, START
from .state import AgentState

# ==============================================================================
# Node Functions (Placeholders)
# ==============================================================================

def observer_node(state: AgentState) -> AgentState:
    print("---OBSERVER---")
    # In a real implementation, this would monitor data sources
    # For now, we'll simulate a file change event
    state['raw_event'] = {"type": "file_change", "path": "./example.py"}
    return state

def context_processor_node(state: AgentState) -> AgentState:
    print("---CONTEXT PROCESSOR---")
    # Process the raw event into structured context
    state['processed_context'] = {"code_snippet": "def hello():\n  print('world')"}
    return state

def event_aggregator_node(state: AgentState) -> AgentState:
    print("---EVENT AGGREGATOR---")
    # Decide if the event is significant
    state['is_significant_event'] = True  # Simulate a significant event
    return state

def strategist_node(state: AgentState) -> AgentState:
    print("---STRATEGIST---")
    # Generate intent candidates
    state['intent_candidates'] = ["Refactor the code", "Add documentation", "Run tests"]
    return state

def human_feedback_node(state: AgentState) -> AgentState:
    print("---HUMAN FEEDBACK---")
    # Simulate user selecting a task
    state['selected_task'] = state['intent_candidates'][0]
    return state

def task_orchestrator_node(state: AgentState) -> AgentState:
    print("---TASK ORCHESTRATOR---")
    # Only initialize the approved_tasks list if it's the first time or empty.
    if not state.get('approved_tasks'):
        if state.get('selected_task'):
            state['approved_tasks'] = [state['selected_task']]
            # Clear selected_task after it has been moved to the queue
            state['selected_task'] = None
    return state

def executor_node(state: AgentState) -> AgentState:
    print("---EXECUTOR---")
    # Simulate task execution
    task = state['approved_tasks'].pop(0)
    state['task_result'] = f"Successfully executed: {task}"
    return state

def final_review_node(state: AgentState) -> AgentState:
    print("---FINAL REVIEW---")
    # Simulate user accepting the result
    state['final_feedback'] = "accept"
    print(state['task_result'])
    return state

# ==============================================================================
# Conditional Routing Functions
# ==============================================================================

def should_activate_strategist(state: AgentState) -> str:
    """
    Determines whether to activate the Strategist or end the flow.
    """
    if state.get('is_significant_event'):
        return "strategist"
    else:
        return END

def should_continue_execution(state: AgentState) -> str:
    """
    Determines if there are more tasks to execute.
    """
    if state.get('approved_tasks'):
        return "executor"
    else:
        return "final_review"

def should_refine_or_end(state: AgentState) -> str:
    """
    Determines whether to refine the strategy or end the flow based on feedback.
    """
    if state.get('final_feedback') == "needs_modification":
        return "strategist"
    else:
        return END

# ==============================================================================
# Graph Builder
# ==============================================================================

def build_graph():
    """Builds and returns the Kairos agent workflow graph."""
    builder = StateGraph(AgentState)

    # --- Add Nodes ---
    builder.add_node("observer", observer_node)
    builder.add_node("context_processor", context_processor_node)
    builder.add_node("event_aggregator", event_aggregator_node)
    builder.add_node("strategist", strategist_node)
    builder.add_node("human_feedback", human_feedback_node)
    builder.add_node("task_orchestrator", task_orchestrator_node)
    builder.add_node("executor", executor_node)
    builder.add_node("final_review", final_review_node)

    # --- Add Edges ---
    builder.add_edge(START, "observer")
    builder.add_edge("observer", "context_processor")
    builder.add_edge("context_processor", "event_aggregator")
    
    builder.add_conditional_edges(
        "event_aggregator",
        should_activate_strategist,
        {"strategist": "strategist", END: END}
    )
    
    builder.add_edge("strategist", "human_feedback")
    builder.add_edge("human_feedback", "task_orchestrator")
    
    builder.add_conditional_edges(
        "task_orchestrator",
        should_continue_execution,
        {"executor": "executor", "final_review": "final_review"}
    )
    
    builder.add_edge("executor", "task_orchestrator") # Loop back to orchestrator
    
    builder.add_conditional_edges(
        "final_review",
        should_refine_or_end,
        {"strategist": "strategist", END: END}
    )

    return builder.compile()
