"""
Configuration management for the OneDrive Organizer.
Loads configuration from YAML files with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict
import yaml
from dotenv import load_dotenv


class ConfigLoader:
    """Load and manage configuration from YAML files."""

    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to the configuration YAML file
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}

        # Load environment variables from .env file
        env_path = Path(".env")
        if env_path.exists():
            load_dotenv(env_path)

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            yaml.YAMLError: If configuration file is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            config_text = f.read()

        # Substitute environment variables
        config_text = self._substitute_env_vars(config_text)

        # Parse YAML
        self.config = yaml.safe_load(config_text)

        return self.config

    def _substitute_env_vars(self, text: str) -> str:
        """
        Replace ${VAR_NAME} patterns with environment variable values.

        Args:
            text: Text containing environment variable references

        Returns:
            Text with substituted values
        """
        def replace_var(match):
            var_name = match.group(1)
            value = os.environ.get(var_name)

            if value is None:
                raise ValueError(
                    f"Environment variable '{var_name}' not found. "
                    f"Please set it in .env file or environment."
                )

            return value

        # Replace ${VAR_NAME} patterns
        pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
        return re.sub(pattern, replace_var, text)

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Args:
            key_path: Dot-separated path (e.g., "organization.source_folder")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            config.get("authentication.client_id")
            config.get("organization.filters.skip_already_organized", True)
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def get_required(self, key_path: str) -> Any:
        """
        Get required configuration value.

        Args:
            key_path: Dot-separated path

        Returns:
            Configuration value

        Raises:
            ValueError: If required key is not found
        """
        value = self.get(key_path)

        if value is None:
            raise ValueError(
                f"Required configuration key '{key_path}' not found"
            )

        return value

    def validate(self) -> None:
        """
        Validate that all required configuration keys are present.

        Raises:
            ValueError: If validation fails
        """
        required_keys = [
            "authentication.client_id",
            "authentication.tenant_id",
            "authentication.scopes",
            "organization.destination_root",
            "organization.date_field",
            "organization.folder_structure",
        ]

        for key in required_keys:
            self.get_required(key)


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    loader = ConfigLoader(config_path)
    return loader.load()
