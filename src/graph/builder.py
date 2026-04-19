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
    SkillNotFoundError,
)

logger = logging.getLogger(__name__)

DEGRADED_PARAMS: dict[str, dict] = {
    "research":  {"style": "brief"},
    "compare":   {"focus_areas": "key differences only"},
    "write":     {"audience": "general"},
    "analyze":   {"focus": "summary only"},
    "code":      {"task": "minimal implementation"},
    "generic":   {},
}

ERROR_POLICY: dict[type, dict] = {
    SkillNotFoundError: {"failure_type": "not_found", "retry_count": 1},
    RecursionError:     {"failure_type": "fatal",     "retry_count": 1},
    TimeoutError:       {"failure_type": "timeout",   "retry_count": 0},
    Exception:          {"failure_type": "fatal",     "retry_count": 1},
}


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
    import time, json as _json

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

    start_time = time.time()
    success = False
    error_type = None

    try:
        agent = create_skill_executor(skill_name, skill_params)
        result_state = agent.invoke(
            {**state, 'messages': normalised},
            config={"recursion_limit": 25}
        )

        messages = result_state.get('messages', [])
        last = messages[-1] if messages else None
        task_result = getattr(last, 'content', str(last)) if last else 'No result'

        state['messages'] = messages
        state['task_result'] = task_result
        success = True

    except Exception as e:
        error_type = type(e).__name__
        policy = next(
            (v for k, v in ERROR_POLICY.items() if isinstance(e, k)),
            {"failure_type": "fatal", "retry_count": 1},
        )
        state['failure_type'] = policy["failure_type"]
        state['failure_message'] = str(e)
        state['retry_count'] = policy["retry_count"]
        logger.error(f"Skill '{skill_name}' failed [{state['failure_type']}]: {e}")
        state['messages'] = [{'role': 'assistant', 'content': state['failure_message']}]
        state['task_result'] = state['failure_message']

        # Degraded retry: only for recoverable failures on first attempt
        if state['retry_count'] < 1:
            degraded = {**skill_params, **DEGRADED_PARAMS.get(skill_name, {})}
            logger.info(f"Retrying '{skill_name}' with degraded params: {degraded}")
            try:
                agent = create_skill_executor(skill_name, degraded)
                result_state = agent.invoke(
                    {**state, 'messages': normalised},
                    config={"recursion_limit": 25}
                )
                messages = result_state.get('messages', [])
                last = messages[-1] if messages else None
                state['messages'] = messages
                state['task_result'] = getattr(last, 'content', str(last)) if last else 'No result'
                state['failure_type'] = None
                state['failure_message'] = None
                state['result_caveat'] = "Result generated with degraded parameters due to an initial failure."
                success = True
                error_type = None
            except Exception as retry_e:
                logger.error(f"Degraded retry for '{skill_name}' also failed: {retry_e}")
                state['failure_message'] = str(retry_e)
            finally:
                state['retry_count'] += 1

    finally:
        logger.info(_json.dumps({
            "event": "skill_execution_completed",
            "skill": skill_name,
            "success": success,
            "error_type": error_type,
            "duration_ms": int((time.time() - start_time) * 1000),
            "result_chars": len(str(state.get('task_result', ''))),
        }))

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
    builder.add_conditional_edges(
        "human_feedback",
        lambda state: "task_orchestrator" if state.get('skill_spec') else "strategist",
        {"task_orchestrator": "task_orchestrator", "strategist": "strategist"}
    )

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