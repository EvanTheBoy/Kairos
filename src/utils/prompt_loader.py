# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import os
from pathlib import Path

def load_prompt(prompt_name: str) -> str:
    """
    Loads a prompt from the 'prompts' directory.

    Args:
        prompt_name: The name of the prompt file (without the .md extension).

    Returns:
        The content of the prompt file as a string.
    """
    # Construct the full path to the prompt file.
    # Path(__file__).parent.parent gives us the 'src' directory.
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.md"

    if not prompt_path.is_file():
        raise FileNotFoundError(f"Prompt file not found at {prompt_path}")

    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
