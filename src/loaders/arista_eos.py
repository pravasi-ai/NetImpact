"""
Arista EOS loader plugin implementing the 4-step loading process.
Handles EOS-specific configuration format with OpenConfig native support.
"""

import json
import xmltodict
from pathlib import Path
from typing import Dict, Any, List
from .base_loader import BaseLoader
import logging


class AristaEosLoader(BaseLoader):
    """
    Arista EOS configuration loader with OpenConfig integration.
    Leverages EOS native OpenConfig support with vendor augmentations.
    """

    def __init__(self, yang_validator, device_info: Dict[str, str]):
        """
        Initialize Arista EOS loader with YANG validator and device info.
        Args: yang_validator instance and device_info from inventory.
        """
        super().__init__(yang_validator, device_info)
        self.logger = logging.getLogger(__name__)

    def load_structured_data(self, file_path: Path) -> Dict[str, Any]:
        """
        Step 1: Load and normalize Arista EOS configuration data.
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
        Step 2: Build composite model merging EOS native with OpenConfig.
        EOS has better OpenConfig support, requiring less transformation.
        Returns: Merged composite model dictionary.
        """
        self.logger.info(f"Building composite model for Arista EOS {self.os_version}")
        
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
        
        # Map EOS interfaces to OpenConfig (more direct mapping than Cisco)
        if "interfaces" in structured_data:
            composite_model["openconfig-interfaces:interfaces"]["interface"] = \
                self._map_interfaces_to_openconfig(structured_data["interfaces"])
        
        # Map EOS VLANs to OpenConfig format
        if "vlans" in structured_data:
            composite_model["openconfig-vlan:vlans"]["vlan"] = \
                self._map_vlans_to_openconfig(structured_data["vlans"])
                
        # Map EOS ACLs to OpenConfig format
        if "acls" in structured_data:
            composite_model["openconfig-acl:acl"]["acl-sets"]["acl-set"] = \
                self._map_acls_to_openconfig(structured_data["acls"])
        
        # Handle EOS-specific features (MLAG, trunk groups, etc.)
        if "mlag" in structured_data:
            composite_model["arista-mlag"] = structured_data["mlag"]
            
        if "trunk_groups" in structured_data:
            composite_model["arista-trunk-groups"] = structured_data["trunk_groups"]
        
        # Add BGP configuration if present
        if "bgp" in structured_data:
            composite_model["openconfig-bgp:bgp"] = \
                self._map_bgp_to_openconfig(structured_data["bgp"])
                
        # Preserve original EOS native data in vendor extension
        composite_model["arista-eos-native"] = structured_data
        
        self.logger.info("Composite model built successfully")
        return composite_model

    def _map_interfaces_to_openconfig(self, eos_interfaces: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map EOS interface configuration to OpenConfig format.
        Args: eos_interfaces dict from native configuration.
        Returns: OpenConfig interface list structure.
        """
        openconfig_interfaces = []
        
        for interface_name, interface_config in eos_interfaces.items():
            oc_interface = {
                "name": interface_name,
                "config": {
                    "name": interface_name,
                    "type": self._get_interface_type(interface_name),
                    "description": interface_config.get("description", ""),
                    "enabled": interface_config.get("shutdown", False) is False
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
            
            # Handle EOS switchport configuration
            if "switchport" in interface_config:
                switchport = interface_config["switchport"]
                ethernet_config = {
                    "switched-vlan": {
                        "config": {}
                    }
                }
                
                if switchport.get("mode") == "access":
                    ethernet_config["switched-vlan"]["config"]["access-vlan"] = \
                        switchport.get("access_vlan", 1)
                elif switchport.get("mode") == "trunk":
                    ethernet_config["switched-vlan"]["config"]["trunk-vlans"] = \
                        switchport.get("trunk_vlans", [])
                        
                oc_interface["openconfig-if-ethernet:ethernet"] = ethernet_config
            
            # Handle channel-group (LACP) configuration
            if "channel_group" in interface_config:
                oc_interface["openconfig-if-aggregate:aggregation"] = {
                    "config": {
                        "lag-type": "LACP",
                        "member": True
                    }
                }
            
            openconfig_interfaces.append(oc_interface)
            
        return openconfig_interfaces

    def _map_vlans_to_openconfig(self, eos_vlans: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map EOS VLAN configuration to OpenConfig format.
        Args: eos_vlans dict from native configuration.
        Returns: OpenConfig VLAN list structure.
        """
        openconfig_vlans = []
        
        for vlan_id, vlan_config in eos_vlans.items():
            oc_vlan = {
                "vlan-id": int(vlan_id),
                "config": {
                    "vlan-id": int(vlan_id),
                    "name": vlan_config.get("name", f"VLAN{vlan_id}"),
                    "status": "ACTIVE"  # EOS VLANs are active by default
                }
            }
            
            # Handle EOS trunk groups
            if "trunk_group" in vlan_config:
                oc_vlan["arista-vlan:trunk-group"] = vlan_config["trunk_group"]
                
            openconfig_vlans.append(oc_vlan)
            
        return openconfig_vlans

    def _map_acls_to_openconfig(self, eos_acls: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map EOS ACL configuration to OpenConfig format.
        Args: eos_acls dict from native configuration.
        Returns: OpenConfig ACL set list structure.
        """
        openconfig_acls = []
        
        for acl_name, acl_config in eos_acls.items():
            oc_acl = {
                "name": acl_name,
                "type": "ACL_IPV4",
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
                
                # Add match conditions
                if "source" in rule:
                    oc_rule["ipv4"] = {
                        "config": {
                            "source-address": rule["source"]
                        }
                    }
                
                oc_acl["acl-entries"]["acl-entry"].append(oc_rule)
            
            openconfig_acls.append(oc_acl)
            
        return openconfig_acls

    def _map_bgp_to_openconfig(self, eos_bgp: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map EOS BGP configuration to OpenConfig format.
        Args: eos_bgp dict from native configuration.
        Returns: OpenConfig BGP structure.
        """
        return {
            "global": {
                "config": {
                    "as": eos_bgp.get("asn", 65001),
                    "router-id": eos_bgp.get("router_id", "1.1.1.1")
                }
            },
            "neighbors": {
                "neighbor": self._map_bgp_neighbors(eos_bgp.get("neighbors", {}))
            }
        }

    def _map_bgp_neighbors(self, eos_neighbors: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Map EOS BGP neighbors to OpenConfig format.
        Args: eos_neighbors dict from BGP configuration.
        Returns: OpenConfig BGP neighbor list.
        """
        oc_neighbors = []
        
        for neighbor_ip, neighbor_config in eos_neighbors.items():
            oc_neighbor = {
                "neighbor-address": neighbor_ip,
                "config": {
                    "neighbor-address": neighbor_ip,
                    "peer-as": neighbor_config.get("remote_as", 65001),
                    "description": neighbor_config.get("description", "")
                }
            }
            oc_neighbors.append(oc_neighbor)
            
        return oc_neighbors

    def _get_interface_type(self, interface_name: str) -> str:
        """
        Determine OpenConfig interface type from EOS interface name.
        Args: interface_name string like 'Ethernet1' or 'Management1'.
        Returns: OpenConfig interface type identifier.
        """
        name_lower = interface_name.lower()
        
        if "ethernet" in name_lower:
            return "iana-if-type:ethernetCsmacd"
        elif "management" in name_lower:
            return "iana-if-type:ethernetCsmacd"
        elif "portchannel" in name_lower:
            return "iana-if-type:ieee8023adLag"
        elif "vlan" in name_lower:
            return "iana-if-type:l3ipvlan"
        elif "loopback" in name_lower:
            return "iana-if-type:softwareLoopback"
        else:
            return "iana-if-type:ethernetCsmacd"  # Default to Ethernet