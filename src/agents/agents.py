# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import json
import logging
from langgraph.prebuilt import create_react_agent

from src.prompts.template import apply_prompt_template, render_skill_prompt
from src.llms.llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP
from src.skills.registry import SkillRegistry
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
            logger.warning(json.dumps({
                "event": "json_parse_failed",
                "agent": "event_aggregator",
                "raw_length": len(response_content),
            }))
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

            # Normalise: legacy plain-string format → SkillSpec dicts
            if candidates and isinstance(candidates[0], str):
                logger.warning("Strategist returned legacy string format — wrapping as generic skills")
                candidates = [
                    {"skill": "generic", "description": c, "params": {"task": c}}
                    for c in candidates
                ]

            state['intent_candidates'] = candidates
            logger.info(f"Strategist proposed {len(candidates)} candidate(s)")
        except json.JSONDecodeError:
            logger.warning(json.dumps({
                "event": "json_parse_failed",
                "agent": "strategist",
                "raw_length": len(response_content),
            }))
            state['intent_candidates'] = []
        return state

    return _create_simple_agent_node("strategist", state_updater)




class SkillNotFoundError(KeyError):
    """Raised when a requested skill is not registered in SkillRegistry."""


def _build_tool_registry() -> dict:
    """
    Returns a mapping of tool name → tool object for all tools available in Kairos.
    Used by create_skill_executor to resolve the tool list declared in SkillRegistry.
    """
    from src.tools import basic_tools, preference_store
    from src.tools.research_tools import (
        search_web_information,
        fetch_webpage_content,
        generate_research_report,
        comprehensive_topic_research,
        compare_topics,
        extract_key_facts,
    )
    return {
        "search_web_information": search_web_information,
        "fetch_webpage_content": fetch_webpage_content,
        "generate_research_report": generate_research_report,
        "comprehensive_topic_research": comprehensive_topic_research,
        "compare_topics": compare_topics,
        "extract_key_facts": extract_key_facts,
        "read_file": basic_tools.read_file,
        "write_file": basic_tools.write_file,
        "execute_shell_command": basic_tools.execute_shell_command,
        "get_preference": preference_store.get_preference,
        "set_preference": preference_store.set_preference,
    }


def create_skill_executor(skill_name: str, skill_params: dict):
    """
    Factory that creates a skill-specific ReAct agent.

    Looks up the skill in SkillRegistry to get its prompt file and allowed tools,
    renders the prompt template with the skill params, and returns a runnable agent.

    Args:
        skill_name:   Key into SkillRegistry (e.g. "research", "compare")
        skill_params: Params from the selected SkillSpec, injected into the prompt

    Returns:
        A compiled ReAct agent ready to be invoked with an AgentState.
    """
    logger = logging.getLogger(__name__)

    if SkillRegistry.get(skill_name) is None:
        raise SkillNotFoundError(f"Skill '{skill_name}' is not registered in SkillRegistry")

    tool_names = SkillRegistry.get_tools(skill_name)
    all_tools = _build_tool_registry()
    tools = [all_tools[name] for name in tool_names if name in all_tools]

    missing = [n for n in tool_names if n not in all_tools]
    if missing:
        logger.warning(f"Skill '{skill_name}' references unknown tools: {missing}")

    system_prompt = render_skill_prompt(skill_name, skill_params)

    logger.info(f"Creating skill executor for '{skill_name}' with tools: {tool_names}")

    return create_react_agent(
        model=get_llm_by_type(AGENT_LLM_MAP["skill_executor"]),
        tools=tools,
        prompt=system_prompt,
    )


def create_react_agent_from_config(agent_name: str, agent_type: str, tools: list):
    """Factory function to create ReAct agents with consistent configuration."""

    def prompt_generator(state):
        return apply_prompt_template(agent_name, state)

    return create_react_agent(
        model=get_llm_by_type(AGENT_LLM_MAP[agent_type]),
        tools=tools,
        prompt=prompt_generator,
    )
