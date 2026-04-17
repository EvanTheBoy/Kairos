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
    create_skill_executor,
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

    choices = [Choice(value=c, name=c['description']) for c in candidates]
    choices.append(Choice(value='none', name='以上都不合适，重新生成'))

    selected = inquirer.select(
        message="Please select a task to execute:",
        choices=choices
    ).execute()

    if selected == 'none':
        rejection_reason = inquirer.text(
            message="请描述你的需求或说明为何不合适："
        ).execute()
        state['user_rejection_feedback'] = rejection_reason
        state['skill_spec'] = None
    else:
        state['skill_spec'] = selected
        state['selected_task'] = selected['description']
        state['user_rejection_feedback'] = None

    return state


def task_orchestrator_node(state: AgentState) -> AgentState:
    logger.info("Orchestrating task...")

    if 'approved_tasks' not in state:
        state['approved_tasks'] = []

    # Entered from two places:
    # 1. From human_feedback: skill_spec is freshly set → enqueue it.
    # 2. From skill_executor: skill_spec was cleared → pop the next one.
    if state.get('skill_spec'):
        state['approved_tasks'].append(state['skill_spec'])
        logger.debug(f"Enqueued skill: '{state['skill_spec'].get('description')}'")

    if state['approved_tasks']:
        next_skill = state['approved_tasks'].pop(0)
        state['skill_spec'] = next_skill
        state['selected_task'] = next_skill.get('description', '')
        logger.info(f"Next skill to execute: '{state['selected_task']}'")
        logger.debug(f"Remaining in queue: {len(state['approved_tasks'])}")
    else:
        state['skill_spec'] = None
        state['selected_task'] = None
        logger.debug("Task queue is empty.")

    return state


def skill_executor_node(state: AgentState) -> AgentState:
    skill_spec = state.get('skill_spec')
    if not skill_spec:
        logger.error("skill_executor_node called with no skill_spec in state")
        state['task_result'] = 'ERROR: No skill selected'
        return state

    skill_name = skill_spec.get('skill', 'generic')
    skill_params = skill_spec.get('params', {})
    logger.info(f"Executing skill '{skill_name}': {skill_spec.get('description')}")

    # Each skill execution starts with a clean message history so previous
    # tasks' tool calls don't pollute the new ReAct context.
    # Gemini requires at least one user message, so we seed one.
    normalised = [{'role': 'user', 'content': 'Please proceed with the task.'}]

    try:
        agent = create_skill_executor(skill_name, skill_params)
        result_state = agent.invoke({**state, 'messages': normalised})

        messages = result_state.get('messages', [])
        last = messages[-1] if messages else None
        task_result = getattr(last, 'content', str(last)) if last else 'No result'

        state['messages'] = messages
        state['task_result'] = task_result
        logger.info(f"Skill '{skill_name}' completed. Result: {len(str(task_result))} chars")

    except Exception as e:
        logger.error(f"Skill '{skill_name}' failed: {e}")
        error_msg = f'ERROR: Skill execution failed: {str(e)}'
        state['messages'] = [{'role': 'assistant', 'content': error_msg}]
        state['task_result'] = error_msg

    state['skill_spec'] = None
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
    """Routes to skill_executor if a skill is queued, otherwise to final_review."""
    if state.get('skill_spec'):
        logger.info(f"Routing to skill_executor: '{state['skill_spec'].get('description')}'")
        return "skill_executor"
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
    builder.add_node("skill_executor", skill_executor_node)
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
        {"skill_executor": "skill_executor", "final_review": "final_review"}
    )

    builder.add_edge("skill_executor", "task_orchestrator")

    builder.add_conditional_edges(
        "final_review",
        should_refine_or_end,
        {"strategist": "strategist", END: END}
    )

    logger.info("Built Kairos workflow graph with skills-based execution")
    return builder.compile()