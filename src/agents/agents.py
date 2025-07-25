# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import json
import logging
from langgraph.prebuilt import create_react_agent

from src.prompts.template import apply_prompt_template
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.utils.json_utils import repair_json_output
from src.graph.state import AgentState


def _create_simple_agent_node(agent_name: str, state_updater):
    """
    Internal factory to create a simple agent node.

    Args:
        agent_name: The name of the agent (and its prompt).
        state_updater: A function that takes (state, llm_response_content) and updates the state.
    """
    logger = logging.getLogger(__name__)
    agent_type = agent_name

    def agent_node(state: AgentState) -> AgentState:
        logger.info(f"Running {agent_name} agent...")
        logger.debug(f"State for {agent_name}: {state}")

        prompt_messages = apply_prompt_template(agent_name, state)
        llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])
        response = llm.invoke(prompt_messages)

        if response and response.content:
            logger.debug(f"{agent_name} response: {response.content}")
            return state_updater(state, response.content)
        else:
            logger.error(f"LLM call failed for {agent_name}.")
            if agent_name == "event_aggregator":
                state['is_significant_event'] = False
            return state

    return agent_node


def create_event_aggregator_node():
    """Creates the graph node for the Event Aggregator agent."""
    logger = logging.getLogger(__name__)

    def state_updater(state: AgentState, response_content: str) -> AgentState:
        try:
            repaired_json = repair_json_output(response_content)
            response_json = json.loads(repaired_json)
            is_significant = response_json.get("trigger_strategist", False)
            state['is_significant_event'] = is_significant
            if is_significant:
                state['aggregated_event'] = response_json.get("aggregated_event")
                logger.info(f"Significant event aggregated: {state['aggregated_event']}")
            else:
                logger.info("Event is not significant.")
        except json.JSONDecodeError:
            logger.error(f"Event Aggregator output was not valid JSON: {response_content}")
            state['is_significant_event'] = False
        return state

    return _create_simple_agent_node("event_aggregator", state_updater)


def create_strategist_node():
    """Creates the graph node for the Strategist agent."""
    logger = logging.getLogger(__name__)

    def state_updater(state: AgentState, response_content: str) -> AgentState:
        try:
            repaired_json = repair_json_output(response_content)
            response_json = json.loads(repaired_json)
            candidates = response_json.get("intent_candidates", [])
            state['intent_candidates'] = candidates
            logger.info(f"Strategist proposed candidates: {candidates}")
        except json.JSONDecodeError:
            logger.error(f"Strategist output was not valid JSON: {response_content}")
            state['intent_candidates'] = []
        return state

    return _create_simple_agent_node("strategist", state_updater)


def create_executor_agent():
    """Creates the ReAct agent for executing tasks with enhanced research capabilities."""
    from src.tools import basic_tools, preference_store

    try:
        from src.tools.research_tools import (
            fetch_webpage_content,
            search_web_information,
            generate_research_report,
            comprehensive_topic_research,
            compare_topics,
            extract_key_facts
        )
        research_tools_available = True
        logger = logging.getLogger(__name__)
        logger.info("Research tools loaded successfully")
    except ImportError as e:
        logger = logging.getLogger(__name__)
        logger.warning(f"Research tools not available: {e}")
        research_tools_available = False

    tools = [
        basic_tools.read_file,
        basic_tools.write_file,
        basic_tools.execute_shell_command,
        preference_store.get_preference,
        preference_store.set_preference,
    ]

    if research_tools_available:
        tools.extend([
            fetch_webpage_content,
            search_web_information,
            generate_research_report,
            comprehensive_topic_research,
            compare_topics,
            extract_key_facts,
        ])

    return create_react_agent_from_config("executor", "executor", tools)


def create_research_agent():
    """Creates a direct research agent that executes tasks immediately."""
    logger = logging.getLogger(__name__)

    def research_agent_function(state: AgentState) -> AgentState:
        task = state.get('selected_task', '')
        logger.info(f"Direct research agent executing: '{task}'")

        if not task or task.strip() == '':
            logger.error("No task provided to research agent")
            state['messages'] = [{
                'role': 'assistant',
                'content': 'ERROR: No research task was provided.'
            }]
            return state

        try:
            from src.tools.research_tools import (
                search_web_information,
                comprehensive_topic_research,
                generate_research_report
            )

            logger.info(f"Starting comprehensive research on: {task}")

            research_result = comprehensive_topic_research(task)

            logger.info(f"Research completed. Result length: {len(research_result)} characters")

            state['messages'] = [{
                'role': 'assistant',
                'content': research_result
            }]

            return state

        except ImportError as e:
            logger.error(f"Research tools not available: {e}")
            state['messages'] = [{
                'role': 'assistant',
                'content': f'ERROR: Research tools not available: {str(e)}'
            }]
            return state
        except Exception as e:
            logger.error(f"Error in research execution: {e}")
            state['messages'] = [{
                'role': 'assistant',
                'content': f'ERROR: Research failed: {str(e)}'
            }]
            return state

    return research_agent_function


def determine_agent_route(state: AgentState) -> str:
    """
    Determine which agent should handle the current task based on intent.

    Args:
        state: Current agent state with intent candidates

    Returns:
        Agent name to route to ("research_agent" or "executor")
    """
    intent_candidates = state.get('intent_candidates', [])
    logger = logging.getLogger(__name__)

    web_research_keywords = [
        'research', 'compare', 'analyze', 'investigate', 'study',
        'search', 'information', 'facts', 'web', 'comprehensive',
        'comparison', 'detailed analysis', 'market research',
        'technology trends', 'industry analysis', 'benchmarking'
    ]

    internal_task_keywords = [
        'crm', 'internal', 'participant', 'registration', 'questionnaire',
        'database', 'report generation', 'leads', 'statistics',
        'enrollment', 'company data', 'persona analysis',
        'booming hub', 'event review', 'specific statistics'
    ]

    for intent in intent_candidates:
        intent_lower = intent.lower()

        if any(keyword in intent_lower for keyword in internal_task_keywords):
            logger.info(f"Routing to executor: Internal/business task detected")
            return "executor"

        if any(keyword in intent_lower for keyword in web_research_keywords):
            logger.info(f"Routing to research_agent: Web research task detected")
            return "research_agent"

        if (' vs ' in intent_lower or ' versus ' in intent_lower or
                'compare' in intent_lower or 'comparison' in intent_lower):
            if not any(keyword in intent_lower for keyword in internal_task_keywords):
                logger.info(f"Routing to research_agent: Comparison task detected")
                return "research_agent"

    logger.info(f"Routing to executor: Default routing for non-research task")
    return "executor"


def create_react_agent_from_config(agent_name: str, agent_type: str, tools: list):
    """Factory function to create ReAct agents with consistent configuration."""

    def prompt_generator(state):
        return apply_prompt_template(agent_name, state)

    return create_react_agent(
        model=get_llm_by_type(AGENT_LLM_MAP[agent_type]),
        tools=tools,
        prompt=prompt_generator,
    )
