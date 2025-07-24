# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import logging
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from langgraph.graph import StateGraph, END, START
from .state import AgentState
from src.observer import observe
from src.context_processor import process_context
from src.agents.agents import (
    create_event_aggregator_node,
    create_strategist_node,
    create_executor_agent,
)

logger = logging.getLogger(__name__)

# ==============================================================================
# Node Functions (Placeholders)
# ==============================================================================

def human_feedback_node(state: AgentState) -> AgentState:
    logger.info("Awaiting human feedback...")
    candidates = state.get('intent_candidates')
    if not candidates:
        logger.warning("No candidates to choose from.")
        return state
        
    # In a real UI, this would be a clickable list.
    # We simulate it with a command-line prompter.
    selected_task = inquirer.select(
        message="Please select a task to execute:",
        choices=[Choice(value=c, name=c) for c in candidates]
    ).execute()
    
    state['selected_task'] = selected_task
    return state

def task_orchestrator_node(state: AgentState) -> AgentState:
    logger.info("Orchestrating task...")
    
    # Initialize approved_tasks if it doesn't exist
    if 'approved_tasks' not in state:
        state['approved_tasks'] = []

    # This node is entered from two places:
    # 1. From human_feedback: a new task is selected and needs to be added to the queue.
    # 2. From executor: a task has finished, and we need to pick the next one.
    
    # If selected_task has a value, it's a new task from the user.
    # Add it to the end of the queue.
    if state.get('selected_task'):
        logger.debug(f"Adding new task to queue: {state['selected_task']}")
        state['approved_tasks'].append(state['selected_task'])
    
    # Now, figure out what the next task is.
    if state['approved_tasks']:
        # Pop the next task from the front of the queue
        next_task = state['approved_tasks'].pop(0)
        state['selected_task'] = next_task
        logger.debug(f"Next task to execute: {next_task}")
        logger.debug(f"Remaining tasks in queue: {state['approved_tasks']}")
    else:
        # No more tasks to run
        state['selected_task'] = None
        logger.debug("Task queue is empty.")
        
    return state

def executor_node(state: AgentState) -> AgentState:
    task = state.get('selected_task')
    logger.info(f"Executing task: {task}")
    
    executor = create_executor_agent()
    result_state = executor.invoke(state)
    
    # The result of the ReAct agent is in the 'messages' of the returned state
    last_message = result_state.get('messages', [])[-1]
    
    # Update our main state with the new messages from the executor
    state['messages'] = result_state.get('messages', [])
    state['task_result'] = last_message.content
    
    logger.debug(f"Task '{task}' executed. Result: {last_message.content}")
    
    # Clear the selected task, so we don't re-add it to the queue
    state['selected_task'] = None
    
    return state

def final_review_node(state: AgentState) -> AgentState:
    logger.info("Awaiting final review...")
    
    # The last message from the executor is the result.
    final_result = state.get('messages', [])[-1].content
    logger.info(f"\n✅ Final Result:\n{final_result}\n")
    
    # Ask for feedback
    feedback_action = inquirer.select(
        message="How do you want to proceed?",
        choices=[
            Choice(value="accept", name="Accept and Finish"),
            Choice(value="needs_modification", name="Request Modification"),
        ]
    ).execute()
    
    if feedback_action == "needs_modification":
        modification_request = inquirer.text(
            message="Please describe the required modifications:"
        ).execute()
        state['final_feedback'] = modification_request
    else:
        state['final_feedback'] = "accept"
        
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
    if state.get('selected_task'):
        return "executor"
    else:
        return "final_review"

def should_refine_or_end(state: AgentState) -> str:
    """
    Determines whether to refine the strategy or end the flow based on feedback.
    """
    if state.get('final_feedback') != "accept":
        # Any feedback other than "accept" will trigger a refinement
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
    builder.add_node("observer", observe)
    builder.add_node("context_processor", process_context)
    builder.add_node("event_aggregator", create_event_aggregator_node())
    builder.add_node("strategist", create_strategist_node())
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
