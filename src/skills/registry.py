# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from __future__ import annotations
from typing import Optional


class SkillRegistry:
    """
    Central registry of all skills Kairos knows about.

    Each skill entry defines:
      description  – what this skill does (shown to the strategist and injected
                     into the strategist prompt via SKILL_LIST)
      params       – parameter keys the strategist should fill in; these are
                     injected into the skill's prompt file at execution time
      prompt_file  – path to the skill's prompt template, relative to
                     src/prompts/ (loaded by create_skill_executor)
      tools        – names of the tools this skill's ReAct agent is allowed to use
                     (resolved against the full tool set in agents.py)

    To add a new skill:
      1. Add an entry here
      2. Create src/prompts/skills/<skill_name>.md
      No other files need to change.
    """

    SKILLS: dict[str, dict] = {
        "research": {
            "description": "Web research and structured report generation on any topic",
            "params": ["topic", "style"],
            "prompt_file": "skills/research.md",
            "tools": [
                "search_web_information",
                "fetch_webpage_content",
                "generate_research_report",
            ],
        },
        "compare": {
            "description": "Compare two subjects with detailed side-by-side analysis",
            "params": ["topic1", "topic2", "focus_areas"],
            "prompt_file": "skills/compare.md",
            "tools": [
                "search_web_information",
                "fetch_webpage_content",
                "compare_topics",
            ],
        },
        "write": {
            "description": "Write documents, advocacy briefs, or summaries",
            "params": ["type", "topic", "audience"],
            "prompt_file": "skills/write.md",
            "tools": [
                "search_web_information",
                "fetch_webpage_content",
                "generate_research_report",
            ],
        },
        "analyze": {
            "description": "Analyze data, documents, or policy content",
            "params": ["content", "focus"],
            "prompt_file": "skills/analyze.md",
            "tools": [
                "extract_key_facts",
                "search_web_information",
                "generate_research_report",
            ],
        },
        "code": {
            "description": "Code generation, refactoring, or explanation",
            "params": ["task", "language", "file"],
            "prompt_file": "skills/code.md",
            "tools": [
                "read_file",
                "write_file",
                "execute_shell_command",
            ],
        },
        "generic": {
            "description": "General-purpose task that does not fit other categories",
            "params": ["task"],
            "prompt_file": "skills/generic.md",
            "tools": [
                "search_web_information",
                "fetch_webpage_content",
                "generate_research_report",
                "extract_key_facts",
                "read_file",
                "write_file",
                "execute_shell_command",
                "get_preference",
                "set_preference",
            ],
        },
    }

    @classmethod
    def get(cls, name: str) -> Optional[dict]:
        return cls.SKILLS.get(name)

    @classmethod
    def skill_names(cls) -> list[str]:
        return list(cls.SKILLS.keys())

    @classmethod
    def get_prompt_file(cls, skill_name: str) -> Optional[str]:
        """Returns the prompt file path for a skill, or None if not found."""
        return cls.SKILLS.get(skill_name, {}).get("prompt_file")

    @classmethod
    def get_tools(cls, skill_name: str) -> list[str]:
        """Returns the list of tool names for a skill."""
        return cls.SKILLS.get(skill_name, {}).get("tools", [])

    @classmethod
    def prompt_description(cls) -> str:
        """Returns a formatted skill list for injection into the strategist prompt."""
        lines = []
        for name, info in cls.SKILLS.items():
            params_str = ", ".join(info["params"])
            lines.append(f'  - "{name}": {info["description"]}  (params: {params_str})')
        return "\n".join(lines)
