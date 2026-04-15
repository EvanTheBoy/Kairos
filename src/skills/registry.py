# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from __future__ import annotations
from typing import Optional


class SkillRegistry:
    """
    Central registry of all skills Kairos knows about.

    Each skill entry defines:
      description  – what this skill does (shown to the strategist)
      params       – expected parameter keys the strategist should fill in
      use_cli      – True  → route to ClaudeCLIAgent (open-ended, benefits from
                             Claude's native tool-use loop and prompt caching)
                     False → route to executor (deterministic / internal tasks)
    """

    SKILLS: dict[str, dict] = {
        "research": {
            "description": "Web research and structured report generation on any topic",
            "params": ["topic", "style"],
            "use_cli": True,
        },
        "compare": {
            "description": "Compare two subjects with detailed side-by-side analysis",
            "params": ["topic1", "topic2", "focus_areas"],
            "use_cli": True,
        },
        "write": {
            "description": "Write documents, advocacy briefs, or summaries",
            "params": ["type", "topic", "audience"],
            "use_cli": True,
        },
        "analyze": {
            "description": "Analyze data, documents, or policy content",
            "params": ["content", "focus"],
            "use_cli": True,
        },
        "code": {
            "description": "Code generation, refactoring, or explanation",
            "params": ["task", "language", "file"],
            "use_cli": False,
        },
        "generic": {
            "description": "General-purpose task that does not fit other categories",
            "params": ["task"],
            "use_cli": False,
        },
    }

    @classmethod
    def get(cls, name: str) -> Optional[dict]:
        return cls.SKILLS.get(name)

    @classmethod
    def use_cli(cls, skill_name: str) -> bool:
        """Returns True if this skill should be routed to ClaudeCLIAgent."""
        return cls.SKILLS.get(skill_name, {}).get("use_cli", False)

    @classmethod
    def skill_names(cls) -> list[str]:
        return list(cls.SKILLS.keys())

    @classmethod
    def prompt_description(cls) -> str:
        """Returns a formatted block for injection into the strategist prompt."""
        lines = []
        for name, info in cls.SKILLS.items():
            params_str = ", ".join(info["params"])
            lines.append(f'  - "{name}": {info["description"]}  (params: {params_str})')
        return "\n".join(lines)
