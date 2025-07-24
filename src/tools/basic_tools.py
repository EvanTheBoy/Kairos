# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

import subprocess
from pathlib import Path
from langchain_core.tools import tool

@tool
def read_file(path: str) -> str:
    """
    Reads the content of a file at the given path.
    """
    try:
        return Path(path).read_text()
    except Exception as e:
        return f"Error reading file: {e}"

@tool
def write_file(path: str, content: str) -> str:
    """
    Writes content to a file at the given path. Creates the file if it doesn't exist.
    """
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"File written successfully to {path}"
    except Exception as e:
        return f"Error writing file: {e}"

@tool
def execute_shell_command(command: str) -> str:
    """
    Executes a shell command and returns its output.
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e}\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
