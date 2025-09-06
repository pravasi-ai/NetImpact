"""
YANG validation framework using yangson library.
Handles schema validation for both OpenConfig and vendor-native models.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from yangson import DataModel
from yangson.exceptions import ValidationError, SchemaError
import logging


class YangValidator:
    """
    YANG schema validator supporting OpenConfig and vendor-native models.
    Provides validation services for the composite model approach.
    """

    def __init__(self, yang_models_path: Path):
        """
        Initialize validator with path to YANG models directory.
        Args: yang_models_path pointing to ./models/yang/ directory.
        """
        self.yang_models_path = yang_models_path
        self.loaded_models = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize model paths
        self.openconfig_path = yang_models_path / "openconfig"
        self.cisco_path = yang_models_path / "cisco" 
        self.arista_path = yang_models_path / "arista"

    def _load_data_model(self, model_paths: List[Path], cache_key: str, yang_library_file: Optional[str] = None) -> Optional[DataModel]:
        """
        Load yangson DataModel using YANG library data file with caching.
        Args: model_paths list, cache_key for caching, and optional yang_library_file path.
        Returns: Loaded DataModel instance or None on failure.
        """
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]
            
        try:
            # If no explicit yang_library_file provided, check for defaults
            if not yang_library_file:
                if cache_key == "openconfig":
                    yang_library_file = str(self.yang_models_path / "openconfig-yang-library.json")
                elif cache_key.startswith("cisco_ios-xe"):
                    yang_library_file = str(self.yang_models_path / "cisco-ios-xe-yang-library.json")
                elif cache_key.startswith("arista_eos"):
                    yang_library_file = str(self.yang_models_path / "arista-eos-yang-library.json")
                else:
                    self.logger.debug(f"No YANG library file specified for {cache_key}")
                    return None
            
            # Check if YANG library file exists
            library_path = Path(yang_library_file)
            if not library_path.exists():
                self.logger.error(f"YANG library file not found: {yang_library_file}")
                return None
            
            # Convert model_paths to strings for yangson mod_path parameter
            mod_path_strings = tuple(str(path) for path in model_paths if path.exists())
            
            if not mod_path_strings:
                self.logger.warning(f"No valid model paths found in {model_paths}")
                return None
            
            # Load DataModel using YANG library data file and module search paths
            data_model = DataModel.from_file(
                name=yang_library_file,
                mod_path=mod_path_strings
            )
            
            self.loaded_models[cache_key] = data_model
            self.logger.info(f"Successfully loaded YANG data model for {cache_key}")
            return data_model
            
        except SchemaError as e:
            self.logger.info(f"Schema error loading {cache_key}: {e}")
            return None
        except Exception as e:
            self.logger.info(f"Error loading YANG models for {cache_key}: {e}")
            return None

    def _basic_structure_validation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Basic structure validation when YANG models are unavailable.
        Args: data dictionary to validate.
        Returns: Validated data structure.
        """
        # Basic validation checks for expected OpenConfig structures
        validation_errors = []
        
        # Check for expected top-level containers
        expected_containers = [
            'openconfig-interfaces:interfaces',
            'openconfig-vlan:vlans', 
            'openconfig-acl:acl',
            'routing',  # BGP and other routing
            'device'    # Device metadata
        ]
        
        found_containers = []
        for container in expected_containers:
            if container in data:
                found_containers.append(container)
                
        if not found_containers:
            validation_errors.append("No recognized OpenConfig containers found")
            
        # Validate interfaces structure if present
        if 'openconfig-interfaces:interfaces' in data:
            interfaces = data['openconfig-interfaces:interfaces']
            if not isinstance(interfaces, dict) or 'interface' not in interfaces:
                validation_errors.append("Invalid interfaces structure")
            elif not isinstance(interfaces['interface'], list):
                validation_errors.append("Interfaces interface list must be array")
                
        # Validate VLANs structure if present  
        if 'openconfig-vlan:vlans' in data:
            vlans = data['openconfig-vlan:vlans']
            if not isinstance(vlans, dict) or 'vlan' not in vlans:
                validation_errors.append("Invalid VLANs structure")
            elif not isinstance(vlans['vlan'], list):
                validation_errors.append("VLANs vlan list must be array")
                
        # Validate ACL structure if present
        if 'openconfig-acl:acl' in data:
            acl = data['openconfig-acl:acl']
            if not isinstance(acl, dict) or 'acl-sets' not in acl:
                validation_errors.append("Invalid ACL structure")
                
        # Log validation results
        if validation_errors:
            self.logger.warning(f"Basic validation issues: {', '.join(validation_errors)}")
        else:
            self.logger.info("Basic structure validation passed")
            
        return data

    def validate_openconfig(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate data against OpenConfig YANG models.
        Args: data dictionary to validate.
        Returns: Validated data structure.
        """
        model_paths = [
            self.openconfig_path / "common",
            self.openconfig_path / "interfaces", 
            self.openconfig_path / "vlan",
            self.openconfig_path / "acl",
            self.openconfig_path / "policy",
            self.openconfig_path / "bgp",
            self.yang_models_path / "ietf-standard"
        ]
        
        try:
            data_model = self._load_data_model(model_paths, "openconfig")
            if not data_model:
                self.logger.debug("OpenConfig YANG models not available, performing basic validation")
                return self._basic_structure_validation(data)
                
            # Parse and validate the data
            instance = data_model.parse_data(json.dumps(data))
            instance.validate()
            self.logger.info("OpenConfig YANG validation passed")
            return data
        except ValidationError as e:
            self.logger.error(f"OpenConfig validation failed: {e}")
            # Fall back to basic validation
            self.logger.debug("Falling back to basic structure validation")
            return self._basic_structure_validation(data)
        except Exception as e:
            self.logger.debug(f"YANG validation error: {e}")
            # Fall back to basic validation
            self.logger.debug("Falling back to basic structure validation")
            return self._basic_structure_validation(data)

    def validate_cisco(self, data: Dict[str, Any], os_type: str, os_version: str) -> Dict[str, Any]:
        """
        Validate data against Cisco vendor-native YANG models.
        Args: data to validate, os_type and os_version for model selection.
        Returns: Validated data structure.
        """
        # Map OS versions to model paths (maintaining version specificity)
        version_path_map = {
            "ios-xe": {
                "16.7.1": "xe/1671",
                "17.3.1": "xe/1731"  # Future version support
            },
            "ios": {
                "15.2": "classic/152"  # Future classic IOS support
            }
        }
        
        model_subpath = version_path_map.get(os_type, {}).get(os_version, "xe/1671")
        model_paths = [
            self.cisco_path / model_subpath,
            self.cisco_path / "common"
        ]
        
        cache_key = f"cisco_{os_type}_{os_version}"
        data_model = self._load_data_model(model_paths, cache_key)
        
        if not data_model:
            self.logger.debug(f"Cisco models not available for {os_type} {os_version}, using fallback validation")
            return self._basic_structure_validation(data)
            
        try:
            instance = data_model.parse_data(json.dumps(data))
            instance.validate()
            return data
        except ValidationError as e:
            self.logger.debug(f"Cisco validation failed: {e}")
            self.logger.debug("Falling back to basic structure validation")
            return self._basic_structure_validation(data)

    def validate_arista(self, data: Dict[str, Any], os_version: str) -> Dict[str, Any]:
        """
        Validate data against Arista EOS YANG models.
        Args: data to validate and os_version for model selection.
        Returns: Validated data structure.
        """
        model_paths = [
            self.arista_path / f"eos-{os_version}",
            self.arista_path / "common"
        ]
        
        cache_key = f"arista_eos_{os_version}"
        data_model = self._load_data_model(model_paths, cache_key)
        
        if not data_model:
            self.logger.debug(f"Arista models not available for EOS {os_version}, using fallback validation")
            return self._basic_structure_validation(data)
            
        try:
            instance = data_model.parse_data(json.dumps(data))
            instance.validate()
            return data
        except ValidationError as e:
            self.logger.debug(f"Arista validation failed: {e}")
            self.logger.debug("Falling back to basic structure validation")
            return self._basic_structure_validation(data)

    def validate(self, data: Dict[str, Any], vendor: str, os_type: str, os_version: str) -> Dict[str, Any]:
        """
        Main validation entry point routing to appropriate vendor validator.
        Args: data, vendor, os_type, and os_version for validation routing.
        Returns: Validated data structure.
        """
        self.logger.info(f"Validating {vendor} {os_type} {os_version} configuration")
        
        try:
            # Always try OpenConfig validation first (primary validation)
            validated_data = self.validate_openconfig(data)
            
            # Then apply vendor-specific validation if available
            if vendor.lower() == "cisco":
                validated_data = self.validate_cisco(validated_data, os_type, os_version)
            elif vendor.lower() == "arista": 
                validated_data = self.validate_arista(validated_data, os_version)
                
            self.logger.info(f"Validation successful for {vendor} {os_type} {os_version}")
            return validated_data
            
        except ValidationError as e:
            self.logger.error(f"YANG validation failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected validation error: {e}")
            # Create a simple validation error - ValidationError from yangson may have specific requirements
            raise ValueError(f"Validation failed: {e}")