"""
Generic configuration diff engine using YANG schema introspection.
Protocol-agnostic approach that works with any YANG-modeled configuration.
"""

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import json
import logging
from dataclasses import dataclass


@dataclass
class ConfigChange:
    """Represents a single configuration change."""
    path: str
    change_type: str  # 'added', 'deleted', 'modified'
    old_value: Any = None
    new_value: Any = None
    description: str = ""


class GenericDiffEngine:
    """
    Generic configuration diff engine using YANG schema structure.
    Analyzes only configuration objects present in proposed config.
    """
    
    def __init__(self, yang_models_path: Optional[Path] = None):
        """
        Initialize generic diff engine.
        Args: yang_models_path for schema context (optional).
        """
        self.yang_models_path = yang_models_path
        self.logger = logging.getLogger(__name__)
        
    def compare_configs(self, current_config: Dict[str, Any], proposed_config: Dict[str, Any]) -> List[ConfigChange]:
        """
        Compare proposed config against current config (partial mode).
        Args: current_config full device config, proposed_config partial user config.
        Returns: List of ConfigChange objects for differences found.
        """
        changes = []
        
        # Define metadata sections to filter out
        metadata_sections = {'device'}
        
        # Only analyze config sections present in proposed config (excluding metadata)
        for top_level_key in proposed_config.keys():
            # Skip metadata sections
            if top_level_key in metadata_sections:
                self.logger.debug(f"Skipping metadata section: {top_level_key}")
                continue
                
            if top_level_key in current_config:
                # Compare existing section
                section_changes = self._compare_config_section(
                    current_config[top_level_key],
                    proposed_config[top_level_key], 
                    top_level_key
                )
                changes.extend(section_changes)
            else:
                # New section being added
                changes.append(ConfigChange(
                    path=top_level_key,
                    change_type='added',
                    new_value=proposed_config[top_level_key],
                    description=f"New configuration section: {top_level_key}"
                ))
        
        self.logger.info(f"Found {len(changes)} configuration changes")
        return changes
    
    def _compare_config_section(self, current_section: Any, proposed_section: Any, path: str) -> List[ConfigChange]:
        """
        Recursively compare configuration sections.
        Args: current_section, proposed_section to compare, path context.
        Returns: List of changes found in this section.
        """
        changes = []
        
        if isinstance(proposed_section, dict) and isinstance(current_section, dict):
            # Compare dictionary structures
            for key, proposed_value in proposed_section.items():
                key_path = f"{path}/{key}"
                
                if key not in current_section:
                    # Key added
                    changes.append(ConfigChange(
                        path=key_path,
                        change_type='added',
                        new_value=proposed_value,
                        description=f"Added configuration: {key_path}"
                    ))
                elif current_section[key] != proposed_value:
                    # Recursively compare nested structures
                    if isinstance(proposed_value, (dict, list)):
                        nested_changes = self._compare_config_section(
                            current_section[key], proposed_value, key_path
                        )
                        changes.extend(nested_changes)
                    else:
                        # Value modified
                        changes.append(ConfigChange(
                            path=key_path,
                            change_type='modified',
                            old_value=current_section[key],
                            new_value=proposed_value,
                            description=f"Modified {key_path}: {current_section[key]} → {proposed_value}"
                        ))
                        
        elif isinstance(proposed_section, list) and isinstance(current_section, list):
            # Compare list structures
            changes.extend(self._compare_lists(current_section, proposed_section, path))
            
        elif current_section != proposed_section:
            # Direct value comparison
            changes.append(ConfigChange(
                path=path,
                change_type='modified',
                old_value=current_section,
                new_value=proposed_section,
                description=f"Modified {path}: {current_section} → {proposed_section}"
            ))
        
        return changes
    
    def _compare_lists(self, current_list: List[Any], proposed_list: List[Any], path: str) -> List[ConfigChange]:
        """
        Compare list structures intelligently.
        Args: current_list, proposed_list to compare, path context.
        Returns: List of changes in list items.
        """
        changes = []
        
        # For simple lists, do direct comparison
        if all(not isinstance(item, (dict, list)) for item in proposed_list):
            if current_list != proposed_list:
                changes.append(ConfigChange(
                    path=path,
                    change_type='modified',
                    old_value=current_list,
                    new_value=proposed_list,
                    description=f"List modified at {path}"
                ))
            return changes
        
        # For complex lists, try to match items by key or position
        current_items = {self._get_list_item_key(item, i): item for i, item in enumerate(current_list)}
        proposed_items = {self._get_list_item_key(item, i): item for i, item in enumerate(proposed_list)}
        
        for key, proposed_item in proposed_items.items():
            item_path = f"{path}[{key}]"
            
            if key not in current_items:
                changes.append(ConfigChange(
                    path=item_path,
                    change_type='added',
                    new_value=proposed_item,
                    description=f"Added list item: {item_path}"
                ))
            elif current_items[key] != proposed_item:
                nested_changes = self._compare_config_section(
                    current_items[key], proposed_item, item_path
                )
                changes.extend(nested_changes)
        
        return changes
    
    def _get_list_item_key(self, item: Any, index: int) -> str:
        """
        Extract key for list item identification.
        Args: item to get key for, index fallback.
        Returns: String key for item identification.
        """
        if isinstance(item, dict):
            # Common key fields for network config
            key_candidates = ['name', 'id', 'vlan-id', 'sequence-id', 'interface-id']
            for candidate in key_candidates:
                if candidate in item:
                    return str(item[candidate])
        
        # Fallback to index
        return str(index)
    
    def get_change_summary(self, changes: List[ConfigChange]) -> Dict[str, Any]:
        """
        Generate summary of changes found.
        Args: changes list to summarize.
        Returns: Dictionary with change statistics and details.
        """
        summary = {
            'total_changes': len(changes),
            'added': len([c for c in changes if c.change_type == 'added']),
            'modified': len([c for c in changes if c.change_type == 'modified']),
            'deleted': len([c for c in changes if c.change_type == 'deleted']),
            'changes_by_section': {}
        }
        
        # Group changes by top-level section
        for change in changes:
            section = change.path.split('/')[0]
            if section not in summary['changes_by_section']:
                summary['changes_by_section'][section] = []
            summary['changes_by_section'][section].append(change.description)
        
        return summary