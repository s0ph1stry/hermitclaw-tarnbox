"""All configuration in one place."""

import os
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


def load_config() -> dict:
    """Load config from config.yaml, with env var overrides."""
    with open(CONFIG_PATH, "r") as f:
        config = yaml.safe_load(f)

    # Provider
    config.setdefault("provider", "ollama")
    config.setdefault("ollama_base", "http://localhost:11434")

    # Environment variable overrides
    config["api_key"] = (
        os.environ.get("OPENAI_API_KEY")
        or config.get("api_key")
    )
    config["model"] = os.environ.get("HERMITCLAW_MODEL") or config.get("model", "qwen2.5:14b")

    # Defaults for numeric settings
    config.setdefault("thinking_pace_seconds", 30)
    config.setdefault("max_thoughts_in_context", 4)
    config.setdefault("environment_path", "./environment")
    config.setdefault("reflection_threshold", 50)
    config.setdefault("memory_retrieval_count", 3)
    config.setdefault("embedding_model", "nomic-embed-text")
    config.setdefault("recency_decay_rate", 0.995)

    # Resolve environment_path relative to project root
    project_root = os.path.dirname(os.path.dirname(__file__))
    if not os.path.isabs(config["environment_path"]):
        config["environment_path"] = os.path.join(project_root, config["environment_path"])

    return config


# Global config — loaded once, can be updated at runtime
config = load_config()
