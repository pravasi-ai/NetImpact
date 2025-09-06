"""
Base loader interface for vendor-specific configuration parsers.
Defines the 4-step loading process: Load → Normalize → Merge → Validate.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class BaseLoader(ABC):
    """
    Abstract base class for vendor-specific configuration loaders.
    Implements the standardized 4-step loading process for all vendors.
    """

    def __init__(self, yang_validator, device_info: Dict[str, str]):
        """
        Initialize loader with YANG validator and device information.
        Args: yang_validator for schema validation, device_info from inventory.
        """
        self.yang_validator = yang_validator
        self.device_info = device_info
        self.hostname = device_info.get('hostname')
        self.vendor = device_info.get('vendor')
        self.os_type = device_info.get('os_type')
        self.os_version = device_info.get('os_version')

    @abstractmethod
    def load_structured_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Step 1: Load and normalize structured data from file.
        Handles JSON direct load or XML via xmltodict conversion.
        Returns: Normalized Python dictionary structure.
        """
        pass

    @abstractmethod
    def build_composite_model(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Build composite model by merging vendor-native with OpenConfig.
        Creates unified data structure for validation.
        Returns: Merged composite model dictionary.
        """
        pass

    def validate_against_yang(self, composite_model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 3: Validate composite model against YANG schemas.
        Uses yangson library for schema validation (mandatory gate).
        Returns: Validated data structure or raises validation error.
        """
        return self.yang_validator.validate(
            composite_model, 
            self.vendor, 
            self.os_type, 
            self.os_version
        )

    def load_and_validate(self, file_path: Path) -> Dict[str, Any]:
        """
        Step 4: Execute complete 4-step loading process.
        Orchestrates the entire load → normalize → merge → validate workflow.
        Returns: Final standardized and validated data structure.
        """
        # Step 1: Load and normalize
        structured_data = self.load_structured_data(file_path)
        
        # Step 2: Build composite model
        composite_model = self.build_composite_model(structured_data)
        
        # Step 3: YANG validation (mandatory gate)
        validated_data = self.validate_against_yang(composite_model)
        
        # Add metadata for tracking
        validated_data['_metadata'] = {
            'hostname': self.hostname,
            'vendor': self.vendor,
            'os_type': self.os_type,
            'os_version': self.os_version,
            'source_file': str(file_path),
            'loader_version': '1.0'
        }
        
        return validated_data