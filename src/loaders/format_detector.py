"""
Configuration Format Detection Module.
Determines whether a configuration file is in text format or YANG format (JSON/XML).
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from enum import Enum

class ConfigFormat(Enum):
    """Supported configuration formats."""
    TEXT = "text"
    JSON = "json" 
    XML = "xml"
    UNKNOWN = "unknown"

class FormatDetector:
    """
    Detects configuration file format and validates basic structure.
    Provides clear feedback for unsupported or malformed files.
    """
    
    def __init__(self):
        self.text_indicators = [
            'hostname',
            'interface', 
            'vlan',
            'router',
            'ip route',
            'access-list',
            'line con',
            'line vty',
            'snmp-server'
        ]
        
        self.yang_json_indicators = [
            'openconfig-interfaces:interfaces',
            'openconfig-vlan:vlans',
            'openconfig-network-instance:network-instances',
            'openconfig-acl:acl',
            'device'  # Common device wrapper
        ]
    
    def detect_format(self, file_path: str) -> Tuple[ConfigFormat, Optional[str], Optional[Dict[str, Any]]]:
        """
        Detect configuration format and return format type, error message, and metadata.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Tuple of (format, error_message, metadata)
            - format: Detected ConfigFormat enum
            - error_message: None if successful, error description if failed
            - metadata: Additional information about the format/content
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return ConfigFormat.UNKNOWN, f"File not found: {file_path}", None
                
            if not file_path.is_file():
                return ConfigFormat.UNKNOWN, f"Path is not a file: {file_path}", None
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
            except UnicodeDecodeError:
                return ConfigFormat.UNKNOWN, "File appears to be binary or uses unsupported encoding", None
            except Exception as e:
                return ConfigFormat.UNKNOWN, f"Error reading file: {e}", None
            
            if not content:
                return ConfigFormat.UNKNOWN, "File is empty", None
            
            # Try to detect format
            format_result = self._analyze_content(content, file_path.suffix)
            
            return format_result
            
        except Exception as e:
            return ConfigFormat.UNKNOWN, f"Unexpected error during format detection: {e}", None
    
    def _analyze_content(self, content: str, file_extension: str) -> Tuple[ConfigFormat, Optional[str], Optional[Dict[str, Any]]]:
        """Analyze file content to determine format."""
        
        # Try JSON first
        json_result = self._try_json_format(content)
        if json_result[0] == ConfigFormat.JSON:
            return json_result
        
        # Try XML
        xml_result = self._try_xml_format(content)
        if xml_result[0] == ConfigFormat.XML:
            return xml_result
            
        # Try text format
        text_result = self._try_text_format(content, file_extension)
        if text_result[0] == ConfigFormat.TEXT:
            return text_result
        
        # If nothing matches, provide helpful error
        return ConfigFormat.UNKNOWN, self._generate_format_hint(content), None
    
    def _try_json_format(self, content: str) -> Tuple[ConfigFormat, Optional[str], Optional[Dict[str, Any]]]:
        """Try to parse as JSON and validate YANG structure."""
        try:
            data = json.loads(content)
            
            if not isinstance(data, dict):
                return ConfigFormat.UNKNOWN, "JSON file must contain an object, not array or primitive", None
            
            # Check for YANG indicators
            yang_keys = [key for key in data.keys() if any(indicator in key for indicator in self.yang_json_indicators)]
            
            if yang_keys or 'device' in data:
                metadata = {
                    'yang_objects': yang_keys,
                    'total_keys': len(data.keys()),
                    'has_device_wrapper': 'device' in data
                }
                return ConfigFormat.JSON, None, metadata
            else:
                # Valid JSON but not YANG format
                return ConfigFormat.UNKNOWN, f"Valid JSON but not YANG format. Found keys: {list(data.keys())[:5]}", None
                
        except json.JSONDecodeError as e:
            # Check if it looks like JSON but malformed
            stripped = content.strip()
            if stripped.startswith('{') and stripped.endswith('}'):
                return ConfigFormat.UNKNOWN, f"Malformed JSON: {e}", None
            else:
                # Not JSON, continue to other formats
                return ConfigFormat.UNKNOWN, None, None
    
    def _try_xml_format(self, content: str) -> Tuple[ConfigFormat, Optional[str], Optional[Dict[str, Any]]]:
        """Try to parse as XML and validate YANG structure."""
        try:
            root = ET.fromstring(content)
            
            # Check for YANG/OpenConfig namespaces or structure
            yang_indicators = []
            for elem in root.iter():
                if any(indicator in elem.tag for indicator in ['interfaces', 'vlans', 'network-instance', 'acl']):
                    yang_indicators.append(elem.tag)
            
            if yang_indicators:
                metadata = {
                    'root_tag': root.tag,
                    'yang_elements': yang_indicators[:10],  # Limit to first 10
                    'namespace': root.tag.split('}')[0] if '}' in root.tag else None
                }
                return ConfigFormat.XML, None, metadata
            else:
                return ConfigFormat.UNKNOWN, f"Valid XML but not YANG format. Root element: {root.tag}", None
                
        except ET.ParseError as e:
            # Check if it looks like XML but malformed
            stripped = content.strip()
            if stripped.startswith('<') and stripped.endswith('>'):
                return ConfigFormat.UNKNOWN, f"Malformed XML: {e}", None
            else:
                # Not XML, continue to other formats
                return ConfigFormat.UNKNOWN, None, None
    
    def _try_text_format(self, content: str, file_extension: str) -> Tuple[ConfigFormat, Optional[str], Optional[Dict[str, Any]]]:
        """Try to identify as network device text configuration."""
        lines = content.split('\n')
        
        # Count text configuration indicators
        text_indicators_found = []
        total_config_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('!'):
                continue
                
            total_config_lines += 1
            
            for indicator in self.text_indicators:
                if line.startswith(indicator):
                    text_indicators_found.append(indicator)
                    break
        
        # Determine if this looks like network config text
        if len(text_indicators_found) >= 2 or (len(text_indicators_found) >= 1 and total_config_lines > 10):
            metadata = {
                'indicators_found': text_indicators_found,
                'total_config_lines': total_config_lines,
                'estimated_line_count': len([l for l in lines if l.strip() and not l.strip().startswith('!')])
            }
            
            return ConfigFormat.TEXT, None, metadata
        
        return ConfigFormat.UNKNOWN, None, None
    
    
    def _generate_format_hint(self, content: str) -> str:
        """Generate helpful hint about the file format."""
        content_preview = content[:200].replace('\n', ' ').replace('\r', ' ')
        
        hints = []
        
        if content.strip().startswith('{'):
            hints.append("File appears to start with JSON but parsing failed")
        elif content.strip().startswith('<'):
            hints.append("File appears to start with XML but parsing failed")
        elif any(indicator in content.lower() for indicator in ['hostname', 'interface', 'vlan']):
            hints.append("File contains network configuration keywords but format unclear")
        
        if not hints:
            hints.append("File format could not be determined")
        
        return f"{hints[0]}. Content preview: {content_preview}..."