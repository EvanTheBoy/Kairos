# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from dataclasses import dataclass, field


@dataclass
class SkillSpec:
    """
    Structured intent produced by the Strategist.

    skill       - matches a key in SkillRegistry.SKILLS
    description - human-readable label shown in the intent selector
    params      - skill-specific parameters the executor will use
    """
    skill: str
    description: str
    params: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> "SkillSpec":
        return cls(
            skill=d.get("skill", "generic"),
            description=d.get("description", d.get("skill", "Unknown task")),
            params=d.get("params", {}),
        )

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "description": self.description,
            "params": self.params,
        }
