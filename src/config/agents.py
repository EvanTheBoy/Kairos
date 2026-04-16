# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from typing import Literal

LLMType = Literal["basic", "reasoning", "vision"]

# Mapping of agent types to LLM types
AGENT_LLM_MAP = {
    "event_aggregator": "basic",
    "strategist": "reasoning",
    "skill_executor": "reasoning",
}