"""Constants for recipe structurer package."""

import os
from typing import Literal

# Get provider from environment variable, fallback to mistral if not set
DEFAULT_MODEL: Literal["deepseek", "mistral", "huggingface"] = os.getenv("LLM_PROVIDER", "mistral")

# Validate that the provider is supported
if DEFAULT_MODEL not in ["deepseek", "mistral", "huggingface"]:
    raise ValueError(f"Unsupported LLM provider: {DEFAULT_MODEL}. Must be one of: deepseek, mistral, huggingface") 