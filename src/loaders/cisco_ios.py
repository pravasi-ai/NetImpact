"""
Cisco IOS/IOS-XE loader plugin implementing the 4-step loading process.
Handles both JSON and XML formats with vendor-native to OpenConfig mapping.
"""

import json
import xmltodict
from pathlib import Path
from typing import Dict, Any, List
from .base_loader import BaseLoader
import logging


class CiscoIosLoader(BaseLoader):
    """
    Cisco IOS/IOS-XE configuration loader with OpenConfig mapping.
    Supports IOS classic and IOS-XE with version-specific YANG models.
    """

    def __init__(self, yang_validator, device_info: Dict[str, str]):
        """
        Initialize Cisco loader with YANG validator and device info.
        Args: yang_validator instance and device_info from inventory.
        """
        super().__init__(yang_validator, device_info)
        self.logger = logging.getLogger(__name__)
        
    def load_structured_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Step 1: Load and normalize Cisco configuration data.
        Handles JSON direct load or XML via xmltodict conversion.
        Returns: Normalized Python dictionary structure.
        """
        self.logger.info(f"Loading {file_path.suffix} configuration for {self.hostname}")
        
        try:
            if file_path.suffix.lower() == '.json':
                # Direct JSON loading
                with open(file_path, 'r') as f:
                    data = json.load(f)
            elif file_path.suffix.lower() == '.xml':
                # XML to dict conversion via xmltodict
                with open(file_path, 'r') as f:
                    xml_content = f.read()
                data = xmltodict.parse(xml_content)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
                
            self.logger.info(f"Successfully loaded structured data from {file_path.name}")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load {file_path}: {e}")
            raise

    def build_composite_model(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Build composite model merging Cisco native with OpenConfig.
        Maps Cisco-specific structures to OpenConfig standard format.
        Returns: Merged composite model dictionary.
        """
        self.logger.info(f"Building composite model for Cisco {self.os_type} {self.os_version}")
        
        # Initialize OpenConfig structure
        composite_model = {
            "openconfig-interfaces:interfaces": {
                "interface": []
            },
            "openconfig-vlan:vlans": {
                "vlan": []
            },
            "openconfig-acl:acl": {
                "acl-sets": {
                    "acl-set": []
                }
            }
        }
        
        # Map Cisco interfaces to OpenConfig format
        if "interfaces" in structured_data:
            composite_model["openconfig-interfaces:interfaces"]["interface"] = \
                self._map_interfaces_to_openconfig(structured_data["interfaces"])
        
        # Map Cisco VLANs to OpenConfig format  
        if "vlans" in structured_data:
            composite_model["openconfig-vlan:vlans"]["vlan"] = \
                self._map_vlans_to_openconfig(structured_data["vlans"])
                
        # Map Cisco ACLs to OpenConfig format
        if "access_lists" in structured_data:
            composite_model["openconfig-acl:acl"]["acl-sets"]["acl-set"] = \
                self._map_acls_to_openconfig(structured_data["access_lists"])
        
        # Add routing information if present
        if "routing" in structured_data:
            composite_model["openconfig-routing-policy:routing-policy"] = \
                self._map_routing_to_openconfig(structured_data["routing"])
                
        # Preserve original Cisco native data in vendor extension
        composite_model["cisco-native"] = structured_data
        
        self.logger.info("Composite model built successfully")
        return composite_model

    def _map_interfaces_to_openconfig(self, cisco_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Cisco interface configuration to OpenConfig format.
        Args: cisco_interfaces dict from native configuration.
        Returns: OpenConfig interface list structure.
        """
        openconfig_interfaces = []
        
        for interface_name, interface_config in cisco_interfaces.items():
            oc_interface = {
                "name": interface_name,
                "config": {
                    "name": interface_name,
                    "type": self._get_interface_type(interface_name),
                    "description": interface_config.get("description", ""),
                    "enabled": interface_config.get("status", "up") == "up"
                }
            }
            
            # Add IP configuration if present
            if "ip_address" in interface_config:
                ip_addr = interface_config["ip_address"]
                oc_interface["subinterfaces"] = {
                    "subinterface": [{
                        "index": 0,
                        "openconfig-if-ip:ipv4": {
                            "addresses": {
                                "address": [{
                                    "ip": ip_addr.split('/')[0],
                                    "config": {
                                        "ip": ip_addr.split('/')[0],
                                        "prefix-length": int(ip_addr.split('/')[1]) if '/' in ip_addr else 24
                                    }
                                }]
                            }
                        }
                    }]
                }
            
            # Add VLAN membership for switched interfaces
            if "access_vlan" in interface_config:
                oc_interface["openconfig-if-ethernet:ethernet"] = {
                    "switched-vlan": {
                        "config": {
                            "access-vlan": interface_config["access_vlan"]
                        }
                    }
                }
            
            openconfig_interfaces.append(oc_interface)
            
        return openconfig_interfaces

    def _map_vlans_to_openconfig(self, cisco_vlans: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Cisco VLAN configuration to OpenConfig format.
        Args: cisco_vlans dict from native configuration.
        Returns: OpenConfig VLAN list structure.
        """
        openconfig_vlans = []
        
        for vlan_id, vlan_config in cisco_vlans.items():
            oc_vlan = {
                "vlan-id": int(vlan_id),
                "config": {
                    "vlan-id": int(vlan_id),
                    "name": vlan_config.get("name", f"VLAN{vlan_id}"),
                    "status": "ACTIVE" if vlan_config.get("status", "active") == "active" else "SUSPEND"
                }
            }
            openconfig_vlans.append(oc_vlan)
            
        return openconfig_vlans

    def _map_acls_to_openconfig(self, cisco_acls: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map Cisco ACL configuration to OpenConfig format.
        Args: cisco_acls dict from native configuration.
        Returns: OpenConfig ACL set list structure.
        """
        openconfig_acls = []
        
        for acl_name, acl_config in cisco_acls.items():
            oc_acl = {
                "name": acl_name,
                "type": "ACL_IPV4" if acl_config.get("type", "extended") == "extended" else "ACL_IPV4",
                "config": {
                    "name": acl_name,
                    "type": "ACL_IPV4"
                },
                "acl-entries": {
                    "acl-entry": []
                }
            }
            
            # Map ACL rules
            for seq_num, rule in enumerate(acl_config.get("rules", []), start=10):
                oc_rule = {
                    "sequence-id": seq_num,
                    "config": {
                        "sequence-id": seq_num
                    },
                    "actions": {
                        "config": {
                            "forwarding-action": "ACCEPT" if rule.get("action", "permit") == "permit" else "DROP"
                        }
                    }
                }
                oc_acl["acl-entries"]["acl-entry"].append(oc_rule)
            
            openconfig_acls.append(oc_acl)
            
        return openconfig_acls

    def _map_routing_to_openconfig(self, cisco_routing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map Cisco routing configuration to OpenConfig format.
        Args: cisco_routing dict from native configuration.
        Returns: OpenConfig routing policy structure.
        """
        return {
            "policy-definitions": {
                "policy-definition": []
            },
            # Placeholder for routing policy mapping
            # Full implementation would map route-maps, prefix-lists, etc.
        }

    def _get_interface_type(self, interface_name: str) -> str:
        """
        Determine OpenConfig interface type from Cisco interface name.
        Args: interface_name string like 'GigabitEthernet1/0/1'.
        Returns: OpenConfig interface type identifier.
        """
        name_lower = interface_name.lower()
        
        if "gigabitethernet" in name_lower or "gi" in name_lower:
            return "iana-if-type:gigabitEthernet"
        elif "tengigabitethernet" in name_lower or "te" in name_lower:
            return "iana-if-type:ieee8023adLag"  # 10GE
        elif "portchannel" in name_lower or "po" in name_lower:
            return "iana-if-type:ieee8023adLag"
        elif "vlan" in name_lower:
            return "iana-if-type:l3ipvlan"
        elif "loopback" in name_lower:
            return "iana-if-type:softwareLoopback"
        else:
            return "iana-if-type:ethernetCsmacd"  # Default to Ethernet