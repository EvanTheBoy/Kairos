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
    determine_agent_route,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Node Functions
# ==============================================================================

def human_feedback_node(state: AgentState) -> AgentState:
    logger.info("Awaiting human feedback...")
    candidates = state.get('intent_candidates')
    if not candidates:
        logger.warning("No candidates to choose from.")
        return state

    selected_task = inquirer.select(
        message="Please select a task to execute:",
        choices=[Choice(value=c, name=c) for c in candidates]
    ).execute()

    state['selected_task'] = selected_task
    return state


def task_orchestrator_node(state: AgentState) -> AgentState:
    logger.info("Orchestrating task...")

    if 'approved_tasks' not in state:
        state['approved_tasks'] = []

    # This node is entered from two places:
    # 1. From human_feedback: a new task is selected and needs to be added to the queue.
    # 2. From executor/research_agent: a task has finished, and we need to pick the next one.

    # If selected_task has a value, it's a new task from the user.
    # Add it to the end of the queue.
    if state.get('selected_task'):
        current_task = state['selected_task']
        logger.debug(f"Adding new task to queue: '{current_task}' (type: {type(current_task)})")
        state['approved_tasks'].append(current_task)

    if state['approved_tasks']:
        # Pop the next task from the front of the queue
        next_task = state['approved_tasks'].pop(0)
        state['selected_task'] = next_task
        logger.info(f"Next task to execute: '{next_task}' (length: {len(str(next_task))} chars)")
        logger.debug(f"Remaining tasks in queue: {state['approved_tasks']}")

        # Additional validation
        if not next_task or not str(next_task).strip():
            logger.error(f"Selected task is empty or whitespace only: '{next_task}'")
            state['selected_task'] = None

    else:
        state['selected_task'] = None
        logger.debug("Task queue is empty.")

    return state


def executor_node(state: AgentState) -> AgentState:
    task = state.get('selected_task')
    logger.info(f"Executing task: {task}")

    executor = create_executor_agent()
    result_state = executor.invoke(state)

    last_message = result_state.get('messages', [])[-1]

    state['messages'] = result_state.get('messages', [])
    state['task_result'] = last_message.content

    logger.debug(f"Task '{task}' executed. Result: {last_message.content}")

    state['selected_task'] = None

    return state


def research_agent_node(state: AgentState) -> AgentState:
    task = state.get('selected_task')
    logger.info(f"Research agent node executing task: {task}")

    if not task:
        logger.error("No task provided to research agent node")
        state['messages'] = [{'role': 'assistant', 'content': 'ERROR: No task provided'}]
        state['task_result'] = 'ERROR: No task provided'
        state['selected_task'] = None
        return state

    try:
        from src.tools.research_tools import comprehensive_topic_research

        logger.info(f"Starting comprehensive research on: {task}")

        research_result = comprehensive_topic_research(task)

        logger.info(f"Research completed successfully. Result length: {len(research_result)} chars")

        state['messages'] = [{'role': 'assistant', 'content': research_result}]
        state['task_result'] = research_result

    except ImportError as e:
        logger.error(f"Research tools not available: {e}")
        error_msg = f'ERROR: Research tools not available: {str(e)}'
        state['messages'] = [{'role': 'assistant', 'content': error_msg}]
        state['task_result'] = error_msg

    except Exception as e:
        logger.error(f"Error in research execution: {e}")
        error_msg = f'ERROR: Research failed: {str(e)}'
        state['messages'] = [{'role': 'assistant', 'content': error_msg}]
        state['task_result'] = error_msg

    state['selected_task'] = None

    return state


def final_review_node(state: AgentState) -> AgentState:
    logger.info("Awaiting final review...")

    messages = state.get('messages', [])
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            final_result = last_message.get('content', str(last_message))
        else:
            final_result = getattr(last_message, 'content', str(last_message))
    else:
        final_result = state.get('task_result', 'No result available')

    logger.info(f"\n✅ Final Result:\n{final_result}\n")

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
    Determines if there are more tasks to execute and routes to appropriate agent.
    """
    if state.get('selected_task'):
        agent_route = determine_agent_route(state)
        logger.info(f"Routing task '{state.get('selected_task')}' to: {agent_route}")
        return agent_route
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
    """Builds and returns the Kairos agent workflow graph with research capabilities."""
    builder = StateGraph(AgentState)

    # --- Add Nodes ---
    builder.add_node("observer", observe)
    builder.add_node("context_processor", process_context)
    builder.add_node("event_aggregator", create_event_aggregator_node())
    builder.add_node("strategist", create_strategist_node())
    builder.add_node("human_feedback", human_feedback_node)
    builder.add_node("task_orchestrator", task_orchestrator_node)
    builder.add_node("executor", executor_node)
    builder.add_node("research_agent", research_agent_node)  # Add research agent
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
        {
            "executor": "executor",
            "research_agent": "research_agent",
            "final_review": "final_review"
        }
    )

    # Both agents loop back to orchestrator
    builder.add_edge("executor", "task_orchestrator")
    builder.add_edge("research_agent", "task_orchestrator")

    builder.add_conditional_edges(
        "final_review",
        should_refine_or_end,
        {"strategist": "strategist", END: END}
    )

    logger.info("Built Kairos workflow graph with research agent capabilities")
    return builder.compile()