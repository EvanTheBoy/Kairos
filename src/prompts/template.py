# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import os
import dataclasses
from datetime import datetime
from jinja2 import Environment, FileSystemLoader, select_autoescape
from langgraph.prebuilt.chat_agent_executor import AgentState
from src.config.configuration import Configuration
from src.skills.registry import SkillRegistry

# Initialize Jinja2 environment
env = Environment(
    loader=FileSystemLoader(os.path.dirname(__file__)),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


def render_skill_prompt(skill_name: str, params: dict) -> str:
    """
    Render a skill-specific prompt template with the given parameters.

    Called by create_skill_executor to build the system prompt for a skill's
    ReAct agent. The template file path is read from SkillRegistry so this
    function never needs to know about individual skill names.

    Args:
        skill_name: Key into SkillRegistry (e.g. "research", "compare")
        params:     Skill parameters from the selected SkillSpec, injected as
                    Jinja2 variables (e.g. {{ topic }}, {{ style }})

    Returns:
        Rendered system prompt string.
    """
    prompt_file = SkillRegistry.get_prompt_file(skill_name)
    if not prompt_file:
        raise ValueError(f"No prompt file registered for skill: '{skill_name}'")
    try:
        template = env.get_template(prompt_file)
        return template.render(**params)
    except Exception as e:
        raise ValueError(f"Error rendering skill prompt '{prompt_file}': {e}")


def get_prompt_template(prompt_name: str) -> str:
    """
    Load and return a prompt template using Jinja2.

    Args:
        prompt_name: Name of the prompt template file (without .md extension)

    Returns:
        The template string with proper variable substitution syntax
    """
    try:
        template = env.get_template(f"{prompt_name}.md")
        return template.render()
    except Exception as e:
        raise ValueError(f"Error loading template {prompt_name}: {e}")


def apply_prompt_template(
        prompt_name: str, state: AgentState, configurable: Configuration = None
) -> list:
    """
    Apply template variables to a prompt template and return formatted messages.

    Args:
        prompt_name: Name of the prompt template to use
        state: Current agent state containing variables to substitute

    Returns:
        List of messages with the system prompt as the first message
    """
    # Convert state to dict for template rendering
    state_vars = {
        "CURRENT_TIME": datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"),
        "SKILL_LIST": SkillRegistry.prompt_description(),
        **state,
    }

    # Add configurable variables
    if configurable:
        state_vars.update(dataclasses.asdict(configurable))

    try:
        template = env.get_template(f"{prompt_name}.md")
        system_prompt = template.render(**state_vars)

        # Initialize messages if it doesn't exist
        existing_messages = state.get("messages", [])

        # Convert any LangChain message objects to dict format
        formatted_messages = []
        for msg in existing_messages:
            if hasattr(msg, 'content') and hasattr(msg, 'role'):
                # LangChain message object
                formatted_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            elif isinstance(msg, dict):
                # Already a dict
                formatted_messages.append(msg)
            else:
                # Try to convert to string
                formatted_messages.append({
                    "role": "user",
                    "content": str(msg)
                })

        # Ensure we have proper message format for Gemini
        messages = [{"role": "system", "content": system_prompt}]

        # Add existing messages if any
        if formatted_messages:
            messages.extend(formatted_messages)

        # If no user message exists, add a default one for Gemini compatibility
        has_user_message = any(msg.get("role") == "user" for msg in messages)
        if not has_user_message:
            messages.append({"role": "user", "content": "Please proceed with the task."})

        return messages
    except Exception as e:
        raise ValueError(f"Error applying template {prompt_name}: {e}")