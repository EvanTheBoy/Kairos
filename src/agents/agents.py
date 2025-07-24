# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import json
import logging
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

from src.prompts import apply_prompt_template
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.utils.prompt_loader import load_prompt
from src.utils.json_utils import repair_json_output
from src.graph.state import AgentState

# A more generic agent creator that doesn't rely on ReAct
def _create_simple_agent_node(agent_name: str, state_updater):
    """
    Internal factory to create a simple agent node.
    
    Args:
        agent_name: The name of the agent (and its prompt).
        state_updater: A function that takes (state, llm_response_content) and updates the state.
    """
    logger = logging.getLogger(__name__)
    agent_type = agent_name
    prompt_template_str = load_prompt(agent_name)
    
    def agent_node(state: AgentState) -> AgentState:
        logger.info(f"Running {agent_name} agent...")
        logger.debug(f"State for {agent_name}: {state}")
        
        prompt = apply_prompt_template(prompt_template_str, state)
        llm = get_llm_by_type(AGENT_LLM_MAP[agent_type])
        response = llm.invoke([HumanMessage(content=prompt)])
        
        if response and response.content:
            logger.debug(f"{agent_name} response: {response.content}")
            return state_updater(state, response.content)
        else:
            # Handle LLM failure
            logger.error(f"LLM call failed for {agent_name}.")
            # Set a default state to avoid errors down the line
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
            # The prompt asks for a JSON object with a single key "intent_candidates"
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
    """Creates the ReAct agent for executing tasks."""
    from src.tools import basic_tools, preference_store
    
    # Gather all available tools
    tools = [
        basic_tools.read_file,
        basic_tools.write_file,
        basic_tools.execute_shell_command,
        preference_store.get_preference,
        preference_store.set_preference,
    ]
    
    return create_react_agent_from_config("executor", "executor", tools, "executor")

# We can still have the ReAct agent factory for more complex agents like the Executor
def create_react_agent_from_config(agent_name: str, agent_type: str, tools: list, prompt_template: str):
    """Factory function to create ReAct agents with consistent configuration."""
    
    return create_react_agent(
        model=get_llm_by_type(AGENT_LLM_MAP[agent_type]),
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )
