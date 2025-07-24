# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from jinja2 import Template
from typing import Dict, Any

def apply_prompt_template(template_str: str, state: Dict[str, Any]) -> str:
    """
    Applies the given state to the prompt template using Jinja2.
    
    Args:
        template_str: The prompt template string.
        state: The dictionary containing the current state.
        
    Returns:
        The rendered prompt string.
    """
    template = Template(template_str)
    return template.render(state)
