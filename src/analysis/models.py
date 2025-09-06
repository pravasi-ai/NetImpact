from dataclasses import dataclass
from typing import Any

@dataclass
class TrueSchemaDependency:
    """TRUE schema-driven dependency found in configuration analysis."""
    config_change_path: str
    affected_leafref_source: str
    affected_leafref_target: str
    leafref_description: str
    dependency_type: str
    actual_object_identifier: str = ""  # Actual object name (e.g., "USER_INBOUND_V4")
    confidence: str = "schema_verified"

@dataclass
class ConfigurationChange:
    """Represents a change between current and proposed configurations."""
    path: str
    change_type: str  # added, modified, deleted
    old_value: Any = None
    new_value: Any = None
