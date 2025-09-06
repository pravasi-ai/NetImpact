"""
Text Configuration to YANG Model Converter.
Orchestrates the conversion of text-based network configurations to YANG models.
"""

import json
import csv
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

# Import existing text parsing components
from ..parsing.text_parser import ConfigTextParser
from ..parsing.config_transformer import YangTransformer

class TextToYangConverter:
    """
    Converts text-based network configurations to YANG models.
    Provides detailed error reporting and validation.
    """
    
    def __init__(self):
        self.supported_vendors = ['cisco_ios', 'cisco_nxos', 'cisco_iosxr', 'arista_eos']
        self.inventory_path = Path(__file__).parent.parent.parent / 'data' / 'inventory' / 'inventory.csv'
    
    def convert(self, file_path: str, vendor: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], Dict[str, Any]]:
        """
        Convert text configuration to YANG model.
        
        Args:
            file_path: Path to text configuration file
            vendor: Vendor type (cisco_ios, arista_eos) or None for auto-detection
            
        Returns:
            Tuple of (success, yang_data, error_message, conversion_metadata)
            - success: True if conversion succeeded
            - yang_data: YANG model dict if successful, None if failed
            - error_message: Error description if failed, None if successful
            - conversion_metadata: Information about the conversion process
        """
        
        conversion_metadata = {
            'input_file': file_path,
            'vendor_detected': None,
            'vendor_used': None,
            'parsing_stats': {},
            'transformation_stats': {},
            'warnings': [],
            'partial_success': False
        }
        
        try:
            # Read configuration file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_text = f.read()
            except Exception as e:
                return False, None, f"Error reading file: {e}", conversion_metadata
            
            if not config_text.strip():
                return False, None, "Configuration file is empty", conversion_metadata
            
            # Detect vendor if not provided
            if vendor is None:
                # Try to get vendor from filename/hostname first
                hostname = self._extract_hostname(config_text)
                if hostname:
                    vendor = self._lookup_vendor_from_inventory(hostname)
                    conversion_metadata['vendor_source'] = 'inventory'
                
                # Fallback to content-based detection if inventory lookup fails
                if not vendor or vendor == 'unknown':
                    vendor = self._detect_vendor_from_content(config_text)
                    conversion_metadata['vendor_source'] = 'content_detection'
                
                conversion_metadata['vendor_detected'] = vendor
                
                if vendor == 'unknown':
                    return False, None, (
                        "Could not detect network device vendor. "
                        "Please specify vendor manually using --vendor parameter. "
                        f"Supported vendors: {', '.join(self.supported_vendors)}"
                    ), conversion_metadata
            
            if vendor not in self.supported_vendors:
                return False, None, (
                    f"Unsupported vendor: {vendor}. "
                    f"Supported vendors: {', '.join(self.supported_vendors)}"
                ), conversion_metadata
            
            conversion_metadata['vendor_used'] = vendor
            
            # Parse text configuration
            parsing_success, parsed_data, parsing_error = self._parse_text_config(config_text, vendor)
            
            if not parsing_success:
                return False, None, f"Text parsing failed: {parsing_error}", conversion_metadata
            
            conversion_metadata['parsing_stats'] = self._generate_parsing_stats(parsed_data)
            
            # Transform to YANG
            transformation_success, yang_data, transformation_error = self._transform_to_yang(parsed_data, vendor)
            
            if not transformation_success:
                return False, None, f"YANG transformation failed: {transformation_error}", conversion_metadata
            
            conversion_metadata['transformation_stats'] = self._generate_transformation_stats(yang_data)
            
            # Validate critical sections were converted
            validation_success, validation_warnings = self._validate_conversion(parsed_data, yang_data)
            conversion_metadata['warnings'] = validation_warnings
            
            if not validation_success:
                # Critical sections missing - this is a failure
                critical_missing = [w for w in validation_warnings if 'critical' in w.lower()]
                if critical_missing:
                    return False, None, (
                        "Critical configuration sections could not be converted to YANG. "
                        f"Missing: {', '.join(critical_missing)}"
                    ), conversion_metadata
            
            # Success with possible warnings
            return True, yang_data, None, conversion_metadata
            
        except Exception as e:
            return False, None, f"Unexpected error during conversion: {e}", conversion_metadata
    
    def _extract_hostname(self, config_text: str) -> Optional[str]:
        """Extract hostname from configuration text."""
        lines = config_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('hostname '):
                return line.split('hostname ')[1].strip()
        return None
    
    def _lookup_vendor_from_inventory(self, hostname: str) -> str:
        """Lookup vendor information from inventory CSV."""
        try:
            if not self.inventory_path.exists():
                return 'unknown'
            
            with open(self.inventory_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['hostname'].strip() == hostname:
                        vendor = row['vendor'].strip().lower()
                        os_type = row['os_type'].strip().lower()
                        
                        # Map inventory data to our vendor types
                        if vendor == 'cisco':
                            # Check more specific OS types first
                            if 'ios-xr' in os_type or 'iosxr' in os_type:
                                return 'cisco_iosxr'
                            elif 'nx-os' in os_type or 'nxos' in os_type:
                                return 'cisco_nxos'
                            elif 'ios-xe' in os_type or 'ios' in os_type:
                                return 'cisco_ios'
                            else:
                                return 'cisco_ios'  # Default fallback
                        elif vendor == 'arista':
                            return 'arista_eos'
                        
                        return 'unknown'
        except Exception:
            return 'unknown'
        
        return 'unknown'
    
    def _detect_vendor_from_content(self, config_text: str) -> str:
        """Detect vendor from configuration text content."""
        config_lower = config_text.lower()
        
        # Cisco indicators
        cisco_indicators = [
            'version 15', 'version 16', 'service timestamps', 
            'boot-start-marker', 'ip domain-name', 'spanning-tree mode rapid-pvst',
            'line con 0', 'line vty'
        ]
        
        # Arista indicators
        arista_indicators = [
            'spanning-tree mode mstp', 'management api', 'daemon terminattr',
            'transceiver qsfp', 'service routing protocols model multi-agent',
            'peer-group', 'mlag configuration'
        ]
        
        cisco_score = sum(1 for indicator in cisco_indicators if indicator in config_lower)
        arista_score = sum(1 for indicator in arista_indicators if indicator in config_lower)
        
        if cisco_score > arista_score and cisco_score >= 2:
            return 'cisco_ios'
        elif arista_score > cisco_score and arista_score >= 2:
            return 'arista_eos'
        else:
            return 'unknown'
    
    def _parse_text_config(self, config_text: str, vendor: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Parse text configuration using appropriate parser."""
        try:
            parser = ConfigTextParser(os_type=vendor)
            parsed_data = parser.parse_config(config_text)
            
            if not parsed_data:
                return False, None, "Parser returned empty data"
            
            # Check if we got any meaningful data
            non_empty_sections = [section for section, data in parsed_data.items() if data]
            
            if len(non_empty_sections) < 2:
                return False, None, (
                    f"Parser found insufficient configuration data. "
                    f"Only {len(non_empty_sections)} sections parsed: {non_empty_sections}. "
                    f"Expected at least hostname and one other section."
                )
            
            return True, parsed_data, None
            
        except Exception as e:
            return False, None, f"Parser error: {e}"
    
    def _transform_to_yang(self, parsed_data: Dict[str, Any], vendor: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """Transform parsed data to YANG model."""
        try:
            transformer = YangTransformer()
            yang_data = transformer.transform(parsed_data, vendor)
            
            if not yang_data:
                return False, None, "Transformer returned empty YANG data"
            
            # Verify we have core YANG objects
            expected_objects = ['openconfig-interfaces:interfaces', 'openconfig-vlan:vlans']
            missing_objects = [obj for obj in expected_objects if obj not in yang_data]
            
            if len(missing_objects) >= 2:  # If both core objects missing, it's a failure
                return False, None, f"Critical YANG objects missing: {missing_objects}"
            
            return True, yang_data, None
            
        except Exception as e:
            return False, None, f"Transformation error: {e}"
    
    def _generate_parsing_stats(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics about parsing results."""
        stats = {}
        
        for section, data in parsed_data.items():
            if isinstance(data, dict):
                stats[section] = len(data)
            elif isinstance(data, list):
                stats[section] = len(data)
            else:
                stats[section] = 1 if data else 0
        
        stats['total_sections'] = len([k for k, v in parsed_data.items() if v])
        stats['empty_sections'] = len([k for k, v in parsed_data.items() if not v])
        
        return stats
    
    def _generate_transformation_stats(self, yang_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics about YANG transformation."""
        stats = {
            'yang_objects': len(yang_data),
            'object_names': list(yang_data.keys())
        }
        
        # Count elements in key objects
        if 'openconfig-interfaces:interfaces' in yang_data:
            interfaces = yang_data['openconfig-interfaces:interfaces'].get('interface', [])
            stats['interfaces_count'] = len(interfaces)
        
        if 'openconfig-vlan:vlans' in yang_data:
            vlans = yang_data['openconfig-vlan:vlans'].get('vlan', [])
            stats['vlans_count'] = len(vlans)
        
        if 'openconfig-acl:acl' in yang_data:
            acls = yang_data['openconfig-acl:acl'].get('acl-sets', {}).get('acl-set', [])
            stats['acls_count'] = len(acls)
        
        return stats
    
    def _validate_conversion(self, parsed_data: Dict[str, Any], yang_data: Dict[str, Any]) -> Tuple[bool, list]:
        """Validate that critical data was converted successfully."""
        warnings = []
        critical_failure = False
        
        # Check hostname
        if 'hostname' in parsed_data and parsed_data['hostname']:
            # Hostname should be preserved somewhere in YANG (often in device wrapper)
            found_hostname = False
            # Note: OpenConfig doesn't have a standard hostname object, this is vendor-specific
            # We'll just warn if hostname was parsed but can't be easily verified in YANG
            warnings.append("Hostname was parsed but may not be preserved in OpenConfig YANG format")
        
        # Check interfaces
        if 'interfaces' in parsed_data and parsed_data['interfaces']:
            if 'openconfig-interfaces:interfaces' not in yang_data:
                warnings.append("CRITICAL: Interfaces were parsed but not converted to YANG")
                critical_failure = True
            else:
                parsed_count = len(parsed_data['interfaces'])
                yang_interfaces = yang_data['openconfig-interfaces:interfaces'].get('interface', [])
                yang_count = len(yang_interfaces)
                
                if yang_count < parsed_count:
                    warnings.append(f"Interface conversion incomplete: {yang_count}/{parsed_count} interfaces converted")
        
        # Check VLANs
        if 'vlans' in parsed_data and parsed_data['vlans']:
            if 'openconfig-vlan:vlans' not in yang_data:
                warnings.append("VLANs were parsed but not converted to YANG")
            else:
                parsed_count = len(parsed_data['vlans'])
                yang_vlans = yang_data['openconfig-vlan:vlans'].get('vlan', [])
                yang_count = len(yang_vlans)
                
                if yang_count < parsed_count:
                    warnings.append(f"VLAN conversion incomplete: {yang_count}/{parsed_count} VLANs converted")
        
        # Check ACLs
        if 'acls' in parsed_data and parsed_data['acls']:
            if 'openconfig-acl:acl' not in yang_data:
                warnings.append("ACLs were parsed but not converted to YANG")
        
        return not critical_failure, warnings
    
    def get_vendor_from_filename(self, file_path: str) -> Optional[str]:
        """Try to determine vendor from filename patterns."""
        filename = Path(file_path).name.lower()
        
        if any(keyword in filename for keyword in ['cisco', 'ios']):
            return 'cisco_ios'
        elif any(keyword in filename for keyword in ['arista', 'eos']):
            return 'arista_eos'
        
        return None