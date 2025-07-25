# Copyright (c) 2025 Kirk Lin
# SPDX-License-Identifier: MIT

from pathlib import Path
from typing import Any, Dict
import os
import httpx

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_deepseek import ChatDeepSeek
from typing import get_args

from src.config import load_yaml_config
from src.config.agents import LLMType

# Cache for LLM instances
_llm_cache: dict[LLMType, BaseChatModel] = {}


def _get_config_file_path() -> str:
    """Get the path to the configuration file."""
    return str((Path(__file__).parent.parent.parent / "conf.yml").resolve())


def _get_llm_type_config_keys() -> dict[str, str]:
    """Get mapping of LLM types to their configuration keys."""
    return {
        "basic": "BASIC_MODEL",
        "reasoning": "REASONING_MODEL",
        "vision": "VISION_MODEL",
    }


def _get_env_llm_conf(llm_type: str) -> Dict[str, Any]:
    """
    Get LLM configuration from environment variables.
    Environment variables should follow the format: {LLM_TYPE}_MODEL__{KEY}
    e.g., BASIC_MODEL__api_key, BASIC_MODEL__base_url
    """
    prefix = f"{llm_type.upper()}_MODEL__"
    conf = {}
    for key, value in os.environ.items():
        if key.startswith(prefix):
            conf_key = key[len(prefix):].lower()
            conf[conf_key] = value
    return conf


def _create_llm_use_conf(llm_type: LLMType, conf: Dict[str, Any]) -> BaseChatModel:
    """Create LLM instance using configuration."""
    llm_type_config_keys = _get_llm_type_config_keys()
    config_key = llm_type_config_keys.get(llm_type)

    if not config_key:
        raise ValueError(f"Unknown LLM type: {llm_type}")

    llm_conf = conf.get(config_key, {})
    if not isinstance(llm_conf, dict):
        raise ValueError(f"Invalid LLM configuration for {llm_type}: {llm_conf}")

    # Get configuration from environment variables
    env_conf = _get_env_llm_conf(llm_type)

    # Merge configurations, with environment variables taking precedence
    merged_conf = {**llm_conf, **env_conf}

    if not merged_conf:
        raise ValueError(f"No configuration found for LLM type: {llm_type}")

    # Add max_retries to handle rate limit errors
    if "max_retries" not in merged_conf:
        merged_conf["max_retries"] = 3

    # Handle DeepSeek reasoning model
    if llm_type == "reasoning" and "deepseek" in merged_conf.get("base_url", "").lower():
        merged_conf["api_base"] = merged_conf.pop("base_url", None)

    # Handle SSL verification and timeout settings
    verify_ssl = merged_conf.pop("verify_ssl", True)

    # Create custom HTTP client if SSL verification is disabled
    if not verify_ssl:
        http_client = httpx.Client(verify=False)
        http_async_client = httpx.AsyncClient(verify=False)
        merged_conf["http_client"] = http_client
        merged_conf["http_async_client"] = http_async_client

    # Handle Azure endpoints
    if "azure_endpoint" in merged_conf or os.getenv("AZURE_OPENAI_ENDPOINT"):
        return AzureChatOpenAI(**merged_conf)

    # Handle DeepSeek
    if llm_type == "reasoning" and "deepseek" in merged_conf.get("api_base", "").lower():
        return ChatDeepSeek(**merged_conf)

    # Handle Gemini through Google's OpenAI-compatible endpoint
    if "generativelanguage.googleapis.com" in merged_conf.get("base_url", ""):
        # For Gemini, we need to adjust the configuration
        gemini_conf = merged_conf.copy()

        # Ensure the base_url is correct for OpenAI compatibility
        if not gemini_conf["base_url"].endswith("/"):
            gemini_conf["base_url"] += "/"

        # Add specific headers for Gemini
        default_headers = gemini_conf.get("default_headers", {})
        default_headers.update({
            "x-goog-api-key": gemini_conf["api_key"]
        })
        gemini_conf["default_headers"] = default_headers

        # Adjust model name for Gemini if needed
        model = gemini_conf.get("model", "")
        if not model.startswith("gemini"):
            gemini_conf["model"] = f"gemini-{model}" if model else "gemini-2.5-flash"

        return ChatOpenAI(**gemini_conf)

    # Default to ChatOpenAI for other cases
    return ChatOpenAI(**merged_conf)


def get_llm_by_type(
        llm_type: LLMType,
) -> BaseChatModel:
    """
    Get LLM instance by type. Returns cached instance if available.
    """
    if llm_type in _llm_cache:
        return _llm_cache[llm_type]

    conf = load_yaml_config(_get_config_file_path())
    llm = _create_llm_use_conf(llm_type, conf)
    _llm_cache[llm_type] = llm
    return llm


def get_configured_llm_models() -> dict[str, list[str]]:
    """
    Get all configured LLM models grouped by type.

    Returns:
        Dictionary mapping LLM type to list of configured model names.
    """
    try:
        conf = load_yaml_config(_get_config_file_path())
        llm_type_config_keys = _get_llm_type_config_keys()

        configured_models: dict[str, list[str]] = {}

        for llm_type in get_args(LLMType):
            # Get configuration from YAML file
            config_key = llm_type_config_keys.get(llm_type, "")
            yaml_conf = conf.get(config_key, {}) if config_key else {}

            # Get configuration from environment variables
            env_conf = _get_env_llm_conf(llm_type)

            # Merge configurations, with environment variables taking precedence
            merged_conf = {**yaml_conf, **env_conf}

            # Check if model is configured
            model_name = merged_conf.get("model")
            if model_name:
                configured_models.setdefault(llm_type, []).append(model_name)

        return configured_models

    except Exception as e:
        # Log error and return empty dict to avoid breaking the application
        print(f"Warning: Failed to load LLM configuration: {e}")
        return {}