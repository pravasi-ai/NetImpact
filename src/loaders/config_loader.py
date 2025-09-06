"""
Configuration loader for current device configs and proposed user configs.
Handles both JSON and XML formats with unified interface.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import json
import xml.etree.ElementTree as ET
import xmltodict
import logging


class ConfigLoader:
    """
    Loads device configurations from standardized project locations.
    Current configs: ./data/configs/{device}.json|xml
    Proposed configs: ./tests/proposed-*.json|xml
    """
    
    def __init__(self, project_root: Path):
        """
        Initialize config loader with project paths.
        Args: project_root path to the project directory.
        """
        self.project_root = project_root
        self.current_configs_dir = project_root / "data" / "configs"
        self.proposed_configs_dir = project_root / "tests"
        self.logger = logging.getLogger(__name__)
        
    def load_current_config(self, device_name: str) -> Optional[Dict[str, Any]]:
        """
        Load current device configuration from data/configs directory.
        Args: device_name to load config for.
        Returns: Configuration dictionary or None if not found.
        """
        # Try JSON first, then XML
        json_path = self.current_configs_dir / f"{device_name}.json"
        xml_path = self.current_configs_dir / f"{device_name}.xml"
        
        if json_path.exists():
            return self._load_json_config(json_path)
        elif xml_path.exists():
            return self._load_xml_config(xml_path)
        else:
            self.logger.error(f"Current config not found for device: {device_name}")
            self.logger.error(f"Searched: {json_path} and {xml_path}")
            return None
    
    def load_proposed_config(self, config_file: str) -> Optional[Dict[str, Any]]:
        """
        Load proposed configuration from tests directory.
        Args: config_file name or path relative to tests directory.
        Returns: Configuration dictionary or None if not found.
        """
        # Handle both absolute and relative paths
        if config_file.startswith('./tests/') or config_file.startswith('tests/'):
            config_path = self.project_root / config_file.lstrip('./')
        elif config_file.startswith('/'):
            config_path = Path(config_file)
        else:
            # Assume it's relative to tests directory
            config_path = self.proposed_configs_dir / config_file
        
        if not config_path.exists():
            self.logger.error(f"Proposed config not found: {config_path}")
            return None
            
        if config_path.suffix.lower() == '.json':
            return self._load_json_config(config_path)
        elif config_path.suffix.lower() == '.xml':
            return self._load_xml_config(config_path)
        else:
            self.logger.error(f"Unsupported config format: {config_path.suffix}")
            return None
    
    def _load_json_config(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load JSON configuration file.
        Args: file_path to JSON config.
        Returns: Configuration dictionary or None on error.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f"Loaded JSON config from: {file_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading JSON config {file_path}: {e}")
            return None
    
    def _load_xml_config(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load XML configuration file and convert to dictionary.
        Args: file_path to XML config.
        Returns: Configuration dictionary or None on error.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            
            # Convert XML to dictionary using xmltodict
            config = xmltodict.parse(xml_content)
            
            self.logger.info(f"Loaded XML config from: {file_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading XML config {file_path}: {e}")
            return None
    
    def list_available_devices(self) -> Dict[str, List[str]]:
        """
        List all available device configurations.
        Returns: Dictionary with current and proposed config lists.
        """
        available = {
            'current_devices': [],
            'proposed_configs': []
        }
        
        # Scan current configs directory
        if self.current_configs_dir.exists():
            for config_file in self.current_configs_dir.glob("*"):
                if config_file.suffix.lower() in ['.json', '.xml']:
                    device_name = config_file.stem
                    available['current_devices'].append(device_name)
        
        # Scan tests directory for proposed configs
        if self.proposed_configs_dir.exists():
            for config_file in self.proposed_configs_dir.glob("proposed-*"):
                if config_file.suffix.lower() in ['.json', '.xml']:
                    available['proposed_configs'].append(config_file.name)
        
        return available
    
    def validate_device_exists(self, device_name: str) -> bool:
        """
        Check if current config exists for device.
        Args: device_name to check.
        Returns: True if device config exists.
        """
        json_path = self.current_configs_dir / f"{device_name}.json"
        xml_path = self.current_configs_dir / f"{device_name}.xml"
        return json_path.exists() or xml_path.exists()
    
    def extract_device_info(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract basic device information from configuration.
        Args: config dictionary to analyze.
        Returns: Device info dictionary with hostname, vendor, etc.
        """
        device_info = {}
        
        try:
            # Look for device section first
            if 'device' in config:
                device_section = config['device']
                device_info.update({
                    'hostname': device_section.get('hostname', 'unknown'),
                    'vendor': device_section.get('vendor', 'unknown'),
                    'platform': device_section.get('platform', 'unknown'),
                    'os_type': device_section.get('os_type', 'unknown'),
                    'os_version': device_section.get('os_version', 'unknown'),
                    'management_ip': device_section.get('management_ip', 'unknown')
                })
            
            # Look for other common identification fields
            for key, value in config.items():
                if isinstance(value, dict) and 'hostname' in value:
                    device_info['hostname'] = value['hostname']
                elif key == 'hostname' and isinstance(value, str):
                    device_info['hostname'] = value
                    
        except Exception as e:
            self.logger.debug(f"Error extracting device info: {e}")
            
        return device_info
    
    def get_config_sections(self, config: Dict[str, Any]) -> List[str]:
        """
        Get list of top-level configuration sections.
        Args: config dictionary to analyze.
        Returns: List of configuration section names.
        """
        sections = []
        
        for key, value in config.items():
            if isinstance(value, dict) and key != 'device':
                sections.append(key)
                
        return sorted(sections)