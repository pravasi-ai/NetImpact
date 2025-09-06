"""
Loader factory for creating appropriate vendor-specific loader instances.
Central registry and factory pattern for pluggable loader architecture.
"""

from pathlib import Path
from typing import Dict, Any, Optional
from .base_loader import BaseLoader
from .cisco_ios import CiscoIosLoader
from .arista_eos import AristaEosLoader
try:
    from ..validation.yang_validator import YangValidator
except ImportError:
    # Fallback for standalone execution
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    from src.validation.yang_validator import YangValidator
import logging


class LoaderFactory:
    """
    Factory class for creating vendor-specific loader instances.
    Manages loader registry and provides unified loader creation interface.
    """

    def __init__(self, yang_models_path: Path):
        """
        Initialize factory with path to YANG models directory.
        Args: yang_models_path pointing to ./models/yang/ directory.
        """
        self.yang_models_path = yang_models_path
        self.yang_validator = YangValidator(yang_models_path)
        self.logger = logging.getLogger(__name__)
        
        # Registry of available loaders
        self._loader_registry = {
            'cisco_ios': CiscoIosLoader,
            'arista_eos': AristaEosLoader
        }

    def create_loader(self, device_info: Dict[str, str]) -> BaseLoader:
        """
        Create appropriate loader instance based on device information.
        Args: device_info dict containing vendor, OS type, and version.
        Returns: Configured loader instance for the specified device.
        """
        vendor = device_info.get('vendor', '').lower()
        os_type = device_info.get('os_type', '').lower()
        
        # Determine loader type
        loader_type = self._get_loader_type(vendor, os_type)
        
        if loader_type not in self._loader_registry:
            raise ValueError(f"No loader available for {vendor} {os_type}")
            
        # Create and return loader instance
        loader_class = self._loader_registry[loader_type]
        loader_instance = loader_class(self.yang_validator, device_info)
        
        self.logger.info(f"Created {loader_type} loader for {device_info.get('hostname')}")
        return loader_instance

    def _get_loader_type(self, vendor: str, os_type: str) -> str:
        """
        Map vendor/OS combination to appropriate loader type.
        Args: vendor name and os_type from device inventory.
        Returns: Loader type string for registry lookup.
        """
        # Mapping rules for loader selection
        loader_map = {
            ('cisco', 'ios'): 'cisco_ios',
            ('cisco', 'ios-xe'): 'cisco_ios',  # Same loader handles both
            ('arista', 'eos'): 'arista_eos'
        }
        
        return loader_map.get((vendor, os_type), 'unknown')

    def get_supported_vendors(self) -> Dict[str, Any]:
        """
        Return information about supported vendors and OS types.
        Returns: Dictionary with supported vendor/OS combinations.
        """
        return {
            'cisco': {
                'os_types': ['ios', 'ios-xe'],
                'loader_type': 'cisco_ios',
                'description': 'Cisco IOS and IOS-XE support'
            },
            'arista': {
                'os_types': ['eos'],
                'loader_type': 'arista_eos', 
                'description': 'Arista EOS support'
            }
        }

    def register_loader(self, loader_type: str, loader_class: type) -> None:
        """
        Register new loader type in the factory registry.
        Args: loader_type identifier and loader_class implementing BaseLoader.
        """
        if not issubclass(loader_class, BaseLoader):
            raise ValueError(f"Loader class must inherit from BaseLoader")
            
        self._loader_registry[loader_type] = loader_class
        self.logger.info(f"Registered loader type: {loader_type}")

    def validate_device_support(self, device_info: Dict[str, str]) -> bool:
        """
        Check if device vendor/OS combination is supported.
        Args: device_info dict with vendor and os_type information.
        Returns: True if supported, False otherwise.
        """
        vendor = device_info.get('vendor', '').lower()
        os_type = device_info.get('os_type', '').lower()
        
        loader_type = self._get_loader_type(vendor, os_type)
        return loader_type in self._loader_registry

    def get_loader_info(self) -> Dict[str, int]:
        """
        Return summary information about available loaders.
        Returns: Dictionary with loader counts and registry information.
        """
        return {
            'total_loaders': len(self._loader_registry),
            'loader_types': list(self._loader_registry.keys()),
            'yang_validator_initialized': self.yang_validator is not None
        }