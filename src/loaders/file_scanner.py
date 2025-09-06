"""
File ingestion logic for discovering and routing configuration files.
Scans config directory and uses inventory to dispatch to correct loaders.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging


class ConfigFileScanner:
    """
    Discovers configuration files and maps them to vendor loaders.
    Handles inventory parsing and file-to-loader routing logic.
    """

    def __init__(self, configs_path: Path, inventory_path: Path):
        """
        Initialize scanner with paths to configs and inventory.
        Args: configs_path to device files, inventory_path to CSV mapping.
        """
        self.configs_path = configs_path
        self.inventory_path = inventory_path
        self.inventory = {}
        self.logger = logging.getLogger(__name__)
        self._load_inventory()

    def _load_inventory(self) -> None:
        """
        Load device inventory from CSV file into memory.
        Creates hostname-to-device-info mapping for loader routing.
        """
        try:
            with open(self.inventory_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    hostname = row['hostname']
                    self.inventory[hostname] = {
                        'hostname': hostname,
                        'vendor': row['vendor'].lower(),
                        'os_type': row['os_type'].lower(), 
                        'os_version': row['os_version'],
                        'platform': row.get('platform', ''),
                        'management_ip': row.get('management_ip', ''),
                        'role': row.get('role', ''),
                        'serial_number': row.get('serial_number', '')
                    }
            self.logger.info(f"Loaded {len(self.inventory)} devices from inventory")
        except Exception as e:
            self.logger.error(f"Failed to load inventory: {e}")
            raise

    def discover_config_files(self) -> List[Dict[str, Any]]:
        """
        Scan configs directory and match files to inventory entries.
        Returns: List of file-to-device mappings for processing.
        """
        discovered_files = []
        
        if not self.configs_path.exists():
            self.logger.error(f"Configs directory not found: {self.configs_path}")
            return discovered_files

        # Scan for JSON and XML config files
        for file_path in self.configs_path.glob("*"):
            if file_path.suffix.lower() in ['.json', '.xml']:
                # Extract hostname from filename (e.g., 'core-sw-01.json' -> 'core-sw-01')
                hostname = file_path.stem
                
                if hostname in self.inventory:
                    device_info = self.inventory[hostname]
                    file_mapping = {
                        'file_path': file_path,
                        'hostname': hostname,
                        'device_info': device_info,
                        'file_format': file_path.suffix.lower()[1:]  # Remove dot from extension
                    }
                    discovered_files.append(file_mapping)
                    self.logger.info(f"Found config: {hostname} ({device_info['vendor']} {device_info['os_type']})")
                else:
                    self.logger.warning(f"Config file {file_path.name} not found in inventory")

        self.logger.info(f"Discovered {len(discovered_files)} configuration files")
        return discovered_files

    def get_device_info(self, hostname: str) -> Optional[Dict[str, str]]:
        """
        Retrieve device information from inventory by hostname.
        Args: hostname to lookup in inventory.
        Returns: Device info dict or None if not found.
        """
        return self.inventory.get(hostname)

    def get_loader_type(self, device_info: Dict[str, str]) -> str:
        """
        Determine appropriate loader type based on device info.
        Args: device_info from inventory with vendor/OS details.
        Returns: Loader type string for plugin selection.
        """
        vendor = device_info['vendor']
        os_type = device_info['os_type']
        
        # Map vendor/OS combinations to loader types
        loader_map = {
            ('cisco', 'ios'): 'cisco_ios',
            ('cisco', 'ios-xe'): 'cisco_ios',  # Same loader handles both
            ('arista', 'eos'): 'arista_eos'
        }
        
        loader_type = loader_map.get((vendor, os_type))
        if not loader_type:
            raise ValueError(f"No loader available for {vendor} {os_type}")
            
        return loader_type

    def filter_by_vendor(self, file_mappings: List[Dict[str, Any]], vendor: str) -> List[Dict[str, Any]]:
        """
        Filter discovered files by vendor for selective processing.
        Args: file_mappings list and vendor name to filter by.
        Returns: Filtered list containing only specified vendor files.
        """
        return [
            mapping for mapping in file_mappings 
            if mapping['device_info']['vendor'].lower() == vendor.lower()
        ]

    def filter_by_os_type(self, file_mappings: List[Dict[str, Any]], os_type: str) -> List[Dict[str, Any]]:
        """
        Filter discovered files by OS type for selective processing.
        Args: file_mappings list and os_type to filter by.
        Returns: Filtered list containing only specified OS type files.
        """
        return [
            mapping for mapping in file_mappings 
            if mapping['device_info']['os_type'].lower() == os_type.lower()
        ]

    def get_summary(self) -> Dict[str, Any]:
        """
        Generate summary statistics of inventory and discovered files.
        Returns: Summary dict with counts by vendor, OS, and file formats.
        """
        files = self.discover_config_files()
        
        vendor_counts = {}
        os_counts = {}
        format_counts = {}
        
        for file_mapping in files:
            device_info = file_mapping['device_info']
            vendor = device_info['vendor']
            os_type = device_info['os_type']
            file_format = file_mapping['file_format']
            
            vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
            os_counts[f"{vendor}_{os_type}"] = os_counts.get(f"{vendor}_{os_type}", 0) + 1
            format_counts[file_format] = format_counts.get(file_format, 0) + 1
        
        return {
            'total_devices_inventory': len(self.inventory),
            'total_config_files': len(files),
            'vendor_breakdown': vendor_counts,
            'os_breakdown': os_counts,
            'format_breakdown': format_counts
        }