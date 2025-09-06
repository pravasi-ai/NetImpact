"""
Dynamic dependency analyzer using YANG models to discover configuration interdependencies.
Leverages yangson DataModel to automatically find schema-defined references between config objects.
"""

from pathlib import Path
from typing import Dict, Any, List, Set, Tuple
from yangson import DataModel
import json
import logging


class DynamicDependencyAnalyzer:
    """
    Dynamically discovers configuration dependencies using YANG model schema.
    Uses schema introspection to find leafref and other reference types.
    """
    
    def __init__(self, yang_models_path: Path):
        """
        Initialize with YANG models for schema introspection.
        Args: yang_models_path to models directory.
        """
        self.yang_models_path = yang_models_path
        self.logger = logging.getLogger(__name__)
        self.data_models = {}
        self._reference_cache = {}
        
    def discover_dependencies(self, config_data: Dict[str, Any], model_type: str = "openconfig") -> Dict[str, List[Dict[str, Any]]]:
        """
        Dynamically discover all dependencies in configuration data.
        Args: config_data to analyze, model_type (openconfig/cisco/arista).
        Returns: Dictionary mapping config objects to their dependencies.
        """
        try:
            # Load appropriate YANG model
            data_model = self._get_data_model(model_type)
            if not data_model:
                return {}
            
            # Find all reference relationships in the schema
            reference_map = self._build_reference_map(data_model)
            
            # Traverse config data and identify actual dependencies
            dependencies = self._find_actual_dependencies(config_data, reference_map)
            
            return dependencies
            
        except Exception as e:
            self.logger.error(f"Dynamic dependency discovery failed: {e}")
            return {}
    
    def _get_data_model(self, model_type: str) -> DataModel:
        """
        Load and cache YANG data model.
        Args: model_type to load.
        Returns: DataModel instance.
        """
        if model_type in self.data_models:
            return self.data_models[model_type]
            
        try:
            if model_type == "openconfig":
                library_file = self.yang_models_path / "dependency-focused.json"
                if library_file.exists():
                    with open(library_file, 'r') as f:
                        library_data = f.read()
                    
                    # Provide all YANG model search paths
                    search_paths = [
                        str(self.yang_models_path),
                        str(self.yang_models_path / "openconfig"),
                        str(self.yang_models_path / "openconfig" / "common"),
                        str(self.yang_models_path / "openconfig" / "acl"), 
                        str(self.yang_models_path / "openconfig" / "interfaces"),
                        str(self.yang_models_path / "openconfig" / "vlan"),
                        str(self.yang_models_path / "openconfig" / "bgp"),
                        str(self.yang_models_path / "ietf-standard"),
                    ]
                    
                    self.data_models[model_type] = DataModel(
                        library_data, 
                        tuple(search_paths)
                    )
                    return self.data_models[model_type]
                    
        except Exception as e:
            self.logger.error(f"Failed to load {model_type} model: {e}")
            return None
    
    def _build_reference_map(self, data_model: DataModel) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build map of all reference relationships in YANG schema.
        Args: data_model to analyze.
        Returns: Map of schema paths to their reference targets.
        """
        cache_key = id(data_model)
        if cache_key in self._reference_cache:
            return self._reference_cache[cache_key]
            
        reference_map = {}
        
        try:
            # Get root schema node
            root_node = data_model.get_schema_node()
            
            # Recursively traverse schema to find references
            self._traverse_schema_for_references(root_node, "", reference_map)
            
            self._reference_cache[cache_key] = reference_map
            self.logger.info(f"Built reference map with {len(reference_map)} reference paths")
            
        except Exception as e:
            self.logger.error(f"Failed to build reference map: {e}")
            
        return reference_map
    
    def _traverse_schema_for_references(self, schema_node, current_path: str, reference_map: Dict[str, List[Dict[str, Any]]]):
        """
        Recursively traverse YANG schema to find leafref and other references.
        Args: schema_node to examine, current_path in schema, reference_map to populate.
        """
        try:
            # Check if current node is a reference type
            if hasattr(schema_node, 'type') and schema_node.type:
                type_obj = schema_node.type
                
                # Check for leafref (most common reference type)
                if hasattr(type_obj, 'path') and type_obj.path:
                    target_path = str(type_obj.path)
                    if current_path not in reference_map:
                        reference_map[current_path] = []
                    
                    reference_map[current_path].append({
                        'type': 'leafref',
                        'target_path': target_path,
                        'source_path': current_path
                    })
                    
                    self.logger.debug(f"Found leafref: {current_path} -> {target_path}")
            
            # Traverse child nodes
            if hasattr(schema_node, 'children'):
                for child_name, child_node in schema_node.children.items():
                    child_path = f"{current_path}/{child_name}" if current_path else child_name
                    self._traverse_schema_for_references(child_node, child_path, reference_map)
                    
        except Exception as e:
            self.logger.debug(f"Error traversing schema node {current_path}: {e}")
    
    def _find_actual_dependencies(self, config_data: Dict[str, Any], reference_map: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find actual dependencies in config data using schema reference map.
        Args: config_data to analyze, reference_map with schema references.
        Returns: Dictionary of actual dependencies found.
        """
        dependencies = {}
        
        # Traverse config data and check for reference values
        for config_path, reference_info_list in reference_map.items():
            for reference_info in reference_info_list:
                target_path = reference_info['target_path']
                
                # Find actual values at the reference source path
                source_values = self._extract_values_at_path(config_data, config_path)
                
                for source_value in source_values:
                    # Find what this value references in the target path
                    target_objects = self._find_referenced_objects(config_data, target_path, source_value)
                    
                    if target_objects:
                        if source_value not in dependencies:
                            dependencies[source_value] = []
                        
                        dependencies[source_value].extend([{
                            'dependency_type': 'schema_reference',
                            'reference_type': reference_info['type'],
                            'target_object': target_obj,
                            'target_path': target_path,
                            'source_path': config_path
                        } for target_obj in target_objects])
        
        return dependencies
    
    def _extract_values_at_path(self, config_data: Dict[str, Any], path: str) -> List[str]:
        """
        Extract all values at a specific configuration path.
        Args: config_data to search, path to extract from.
        Returns: List of values found at path.
        """
        try:
            path_parts = [p for p in path.split('/') if p]
            values = []
            
            # Navigate to path and collect values
            current_data = config_data
            for part in path_parts:
                if isinstance(current_data, dict) and part in current_data:
                    current_data = current_data[part]
                elif isinstance(current_data, list):
                    # Handle list elements
                    new_values = []
                    for item in current_data:
                        if isinstance(item, dict) and part in item:
                            new_values.append(item[part])
                    current_data = new_values
                else:
                    return []
            
            # Collect final values
            if isinstance(current_data, list):
                values.extend([str(v) for v in current_data if v])
            elif current_data:
                values.append(str(current_data))
                
            return values
            
        except Exception as e:
            self.logger.debug(f"Error extracting values at path {path}: {e}")
            return []
    
    def _find_referenced_objects(self, config_data: Dict[str, Any], target_path: str, reference_value: str) -> List[str]:
        """
        Find objects at target path that match the reference value.
        Args: config_data to search, target_path to look in, reference_value to match.
        Returns: List of objects that match the reference.
        """
        try:
            # Find objects at target path that match reference_value
            target_values = self._extract_values_at_path(config_data, target_path)
            
            # Return objects that match the reference value
            return [obj for obj in target_values if str(obj) == reference_value]
            
        except Exception as e:
            self.logger.debug(f"Error finding referenced objects: {e}")
            return []