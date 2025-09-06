from typing import Dict, Any

class YangTransformer:
    """
    Transforms a dictionary of parsed configuration data into a YANG-modeled (OpenConfig)
    JSON structure.
    """

    def transform(self, parsed_data: Dict[str, Any], os_type: str) -> Dict[str, Any]:
        """Main transformation entry point."""
        oc_data = {}

        if 'interfaces' in parsed_data and parsed_data['interfaces']:
            oc_data['openconfig-interfaces:interfaces'] = self._transform_interfaces(parsed_data['interfaces'])
        
        if 'vlans' in parsed_data and parsed_data['vlans']:
            oc_data['openconfig-vlan:vlans'] = self._transform_vlans(parsed_data['vlans'])

        # Placeholder for routing transformation
        if ('bgp' in parsed_data and parsed_data['bgp']) or ('ospf' in parsed_data and parsed_data['ospf']) or ('static_routes' in parsed_data and parsed_data['static_routes']):
            oc_data['openconfig-network-instance:network-instances'] = self._transform_routing(parsed_data)

        if 'acls' in parsed_data and parsed_data['acls']:
            oc_data['openconfig-acl:acl'] = self._transform_acls(parsed_data['acls'])
        
        # Add new configuration transformations
        if 'snmp' in parsed_data and parsed_data['snmp']:
            oc_data['openconfig-system:system'] = self._transform_snmp(parsed_data['snmp'])
            
        if 'line' in parsed_data and parsed_data['line']:
            if 'openconfig-system:system' not in oc_data:
                oc_data['openconfig-system:system'] = {}
            # Handle line data which might be a list or dict
            line_data = parsed_data['line']
            if isinstance(line_data, list) and line_data:
                # Convert list to dict format expected by transformer
                line_dict = {}
                for line_entry in line_data:
                    if isinstance(line_entry, tuple) and len(line_entry) >= 2:
                        line_type = line_entry[0] + ' ' + line_entry[1]
                        line_dict[line_type] = {}
                oc_data['openconfig-system:system']['console'] = self._transform_line_config(line_dict)
            elif isinstance(line_data, dict):
                oc_data['openconfig-system:system']['console'] = self._transform_line_config(line_data)
            
        if 'management_api' in parsed_data:
            mgmt_data = parsed_data['management_api']
            if isinstance(mgmt_data, dict):
                oc_data['openconfig-system:management-api'] = self._transform_management_api(mgmt_data)

        return oc_data

    def _transform_interfaces(self, interfaces_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms parsed interface data to OpenConfig format."""
        oc_interfaces = []
        for name, config in interfaces_data.items():
            ip, prefix = self._parse_ip_address(config.get('ip_address'))
            oc_if = {
                'name': name,
                'config': {
                    'name': name,
                    'description': config.get('description')[0] if isinstance(config.get('description'), list) else config.get('description'),
                    'enabled': 'shutdown' not in config
                }
            }
            if ip:
                ipv4_config = {
                    'addresses': {
                        'address': [{
                            'ip': ip,
                            'config': {'ip': ip, 'prefix-length': prefix}
                        }]
                    }
                }
                
                # Add DHCP relay (helper-address) if present
                if 'ip_helper_address' in config:
                    helper_addresses = config['ip_helper_address']
                    if isinstance(helper_addresses, list):
                        ipv4_config['dhcp-relay'] = {
                            'config': {
                                'helper-address': helper_addresses
                            }
                        }
                
                oc_if['subinterfaces'] = {
                    'subinterface': [{
                        'index': 0,
                        'openconfig-if-ip:ipv4': ipv4_config
                    }]
                }
            oc_interfaces.append(oc_if)
        return {'interface': oc_interfaces}

    def _transform_vlans(self, vlans_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms parsed VLAN data to OpenConfig format."""
        oc_vlans = []
        for vlan_id, config in vlans_data.items():
            oc_vlan = {
                'vlan-id': int(vlan_id),
                'config': {
                    'vlan-id': int(vlan_id),
                    'name': config.get('name')[0] if isinstance(config.get('name'), list) else config.get('name'),
                    'status': 'ACTIVE' # Assuming active
                }
            }
            oc_vlans.append(oc_vlan)
        return {'vlan': oc_vlans}

    def _transform_routing(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms routing protocols and static routes to OpenConfig format."""
        protocols = []

        # BGP Transformation
        if 'bgp' in parsed_data:
            for as_number_str, bgp_config in parsed_data['bgp'].items():
                # The parent pattern in YAML gives us the AS number as the key
                as_number = int(as_number_str)
                
                oc_neighbors = []
                if 'neighbor_remote_as' in bgp_config:
                    for neighbor_data in bgp_config['neighbor_remote_as']:
                        # neighbor_data will be a tuple like ('10.0.0.1', '65001')
                        neighbor_address = neighbor_data[0]
                        peer_as = int(neighbor_data[1])
                        oc_neighbors.append({
                            'neighbor-address': neighbor_address,
                            'config': {
                                'neighbor-address': neighbor_address,
                                'peer-as': peer_as
                            }
                        })
                
                oc_networks = []
                if 'network' in bgp_config:
                    for network_data in bgp_config['network']:
                        # network_data will be a tuple like ('10.0.0.0', '255.255.255.0') for Cisco
                        # or '10.0.0.0/24' for Arista
                        if isinstance(network_data, tuple): # Cisco format
                            ip = network_data[0]
                            mask = network_data[1]
                            prefix = sum(bin(int(x)).count('1') for x in mask.split('.'))
                            ip_prefix = f"{ip}/{prefix}"
                        else: # Arista format
                            ip_prefix = network_data
                        
                        oc_networks.append({
                            'prefix': ip_prefix,
                            'config': {
                                'prefix': ip_prefix
                            }
                        })

                protocols.append({
                    'identifier': 'openconfig-policy-types:BGP',
                    'name': f'bgp-{as_number}', # Use AS number as part of the name
                    'bgp': {
                        'global': {
                            'config': {
                                'as': as_number,
                                'router-id': bgp_config.get('router_id')[0] if isinstance(bgp_config.get('router_id'), list) else bgp_config.get('router_id')
                            }
                        },
                        'neighbors': {'neighbor': oc_neighbors} if oc_neighbors else {},
                        'afi-safis': {'afi-safi': oc_networks} if oc_networks else {} # Mapping network statements to afi-safis
                    }
                })

        # OSPF Transformation
        if 'ospf' in parsed_data:
            for process_id_str, ospf_config in parsed_data['ospf'].items():
                process_id = int(process_id_str)
                
                areas_dict = {} # Initialize areas_dict unconditionally
                oc_areas = []
                if 'network_area' in ospf_config:
                    # network_area is a list of tuples: ('10.0.0.0', '0.0.0.255', '0.0.0.0')
                    # or ('10.0.0.0', '0.0.0.0') for Arista
                    for net_area_data in ospf_config['network_area']:
                        if len(net_area_data) == 3: # Cisco format (network, wildcard, area)
                            area_id = net_area_data[2]
                        else: # Arista format (network, area)
                            area_id = net_area_data[1]
                        
                        if area_id not in areas_dict:
                            areas_dict[area_id] = []
                        
                        # Convert network/wildcard to CIDR if necessary
                        if len(net_area_data) == 3: # Cisco
                            ip = net_area_data[0]
                            wildcard = net_area_data[1]
                            # Convert wildcard mask to prefix length
                            # Example: 0.0.0.255 -> 24
                            # This is a simplification, proper conversion needs more logic
                            parts = [str(255 - int(x)) for x in wildcard.split('.')]
                            inverted_mask = ".".join(parts)
                            prefix = sum(bin(int(x)).count('1') for x in inverted_mask.split('.'))
                            network_prefix = f"{ip}/{prefix}"
                        else: # Arista
                            network_prefix = net_area_data[0]

                        areas_dict[area_id].append({'network': network_prefix})
                
                for area_id, networks in areas_dict.items():
                    oc_areas.append({
                        'identifier': area_id,
                        'config': {
                            'identifier': area_id
                        },
                        'interfaces': {
                            'interface': [{'id': net['network']} for net in networks] # Simplified, might need actual interface names
                        }
                    })

                oc_passive_interfaces = []
                if 'passive_interface' in ospf_config:
                    for iface in ospf_config['passive_interface']:
                        oc_passive_interfaces.append({'interface-id': iface})

                protocols.append({
                    'identifier': 'openconfig-policy-types:OSPF',
                    'name': f'ospf-{process_id}',
                    'ospfv2': {
                        'global': {
                            'config': {
                                'router-id': ospf_config.get('router_id')[0] if isinstance(ospf_config.get('router_id'), list) else ospf_config.get('router_id')
                            }
                        },
                        'areas': {'area': oc_areas} if oc_areas else {},
                        'passive-interfaces': {'passive-interface': oc_passive_interfaces} if oc_passive_interfaces else {}
                    }
                })

        # Static Routes Transformation
        if 'static_routes' in parsed_data:
            oc_static_routes = []
            for route_data in parsed_data['static_routes']:
                # route_data is a list of values from the regex match
                # e.g., ('0.0.0.0', '0.0.0.0', '192.168.1.1') for Cisco
                # or ('0.0.0.0/0', '192.168.1.1') for Arista
                
                if isinstance(route_data, dict): # Cisco format
                    ip = route_data['prefix']
                    mask = route_data['mask']
                    next_hop = route_data['next_hop']
                    prefix = sum(bin(int(x)).count('1') for x in mask.split('.'))
                    destination_prefix = f"{ip}/{prefix}"
                elif isinstance(route_data, tuple) and len(route_data) == 2: # Arista format (network/prefix, next-hop)
                    destination_prefix = route_data[0]
                    next_hop = route_data[1]
                else: # Fallback for simple string routes
                    destination_prefix = str(route_data)
                    next_hop = None # Or some default

                route_entry = {
                    'prefix': destination_prefix,
                    'config': {
                        'prefix': destination_prefix
                    }
                }
                if next_hop:
                    route_entry['next-hops'] = {
                        'next-hop': [
                            {
                                'index': 0, # Assuming single next-hop for simplicity
                                'config': {
                                    'index': 0,
                                    'next-hop': next_hop
                                }
                            }
                        ]
                    }
                oc_static_routes.append(route_entry)
            
            protocols.append({
                'identifier': 'openconfig-policy-types:STATIC',
                'name': 'static',
                'static-routes': {'static': oc_static_routes} if oc_static_routes else {}
            })

        return {
            'network-instance': [{
                'name': 'default',
                'config': {'name': 'default', 'type': 'openconfig-network-instance-types:DEFAULT_INSTANCE'},
                'protocols': {'protocol': protocols}
            }]
        }

    def _transform_acls(self, acls_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms parsed ACL data to OpenConfig format."""
        oc_acl_sets = []
        for acl_name, acl_config in acls_data.items():
            acl_type = acl_config.get('type', 'ACL_IPV4').upper() # Default to IPV4
            
            oc_acl_entries = []
            if 'rules' in acl_config:
                for i, rule_data in enumerate(acl_config['rules']):
                    # rule_data is a tuple from regex match
                    # Extended ACL: ('10', 'permit', 'tcp', 'any', 'host 1.1.1.1', '80')
                    # Standard ACL: ('permit', 'host 192.168.10.100') or ('deny', 'any')
                    
                    if len(rule_data) >= 5:  # Extended ACL format
                        sequence_id = int(rule_data[0]) if rule_data[0] and rule_data[0].isdigit() else (i + 1) * 10
                        action = rule_data[1].upper()
                        protocol = rule_data[2].upper()
                        source_address = rule_data[3]
                        destination_address = rule_data[4]
                        destination_port = rule_data[5] if len(rule_data) > 5 else None
                    else:  # Standard ACL format
                        sequence_id = (i + 1) * 10  # Generate sequence ID
                        action = rule_data[0].upper()  # permit/deny
                        protocol = 'IP'  # Default for standard ACLs
                        source_address = rule_data[1] if len(rule_data) > 1 else 'any'
                        destination_address = 'any'  # Standard ACLs don't specify destination
                        destination_port = None

                    oc_entry = {
                        'sequence-id': sequence_id,
                        'config': {
                            'sequence-id': sequence_id
                        },
                        'actions': {
                            'config': {
                                'forwarding-action': 'ACCEPT' if action == 'PERMIT' else 'DROP'
                            }
                        }
                    }

                    oc_ipv4 = {}
                    if source_address:
                        oc_ipv4['source-address'] = source_address.replace('host ', '') # Remove 'host '
                    if destination_address:
                        oc_ipv4['destination-address'] = destination_address.replace('host ', '')
                    if protocol:
                        oc_ipv4['protocol'] = protocol # Needs mapping to openconfig-packet-match-types
                    
                    if oc_ipv4:
                        oc_entry['ipv4'] = {'config': oc_ipv4}

                    if destination_port:
                        oc_entry['transport'] = {'config': {'destination-port': destination_port}}

                    oc_acl_entries.append(oc_entry)

            oc_acl_sets.append({
                'name': acl_name,
                'type': acl_type,
                'config': {
                    'name': acl_name,
                    'type': acl_type
                },
                'acl-entries': {'acl-entry': oc_acl_entries} if oc_acl_entries else {}
            })
        return {'acl-sets': {'acl-set': oc_acl_sets}}

    def _parse_ip_address(self, ip_info):
        """Helper to parse different IP address formats."""
        if not ip_info: return None, None
        if isinstance(ip_info, list) and ip_info:
            ip_info = ip_info[0]

        if isinstance(ip_info, str): # Arista format '1.1.1.1/24'
            parts = ip_info.split('/')
            return parts[0], int(parts[1])
        if isinstance(ip_info, tuple): # Cisco format ('1.1.1.1', '255.255.255.0')
            ip = ip_info[0]
            mask = ip_info[1]
            prefix = sum(bin(int(x)).count('1') for x in mask.split('.'))
            return ip, prefix
        return None, None

    def _transform_snmp(self, snmp_data: list) -> Dict[str, Any]:
        """Transform SNMP configuration to OpenConfig system format."""
        snmp_config = {}
        
        for snmp_entry in snmp_data:
            if isinstance(snmp_entry, tuple):
                if len(snmp_entry) >= 2:
                    # Community string entry: (community, RO/RW, [access-list])
                    if snmp_entry[1] in ['RO', 'RW']:
                        if 'snmp-server' not in snmp_config:
                            snmp_config['snmp-server'] = {'communities': []}
                        
                        community = {
                            'name': snmp_entry[0],
                            'config': {
                                'name': snmp_entry[0],
                                'access': 'READ_ONLY' if snmp_entry[1] == 'RO' else 'READ_WRITE'
                            }
                        }
                        if len(snmp_entry) > 2 and snmp_entry[2]:
                            community['config']['access-list'] = snmp_entry[2]
                        
                        snmp_config['snmp-server']['communities'].append(community)
                    else:
                        # Location entry: (location_string,)
                        if 'snmp-server' not in snmp_config:
                            snmp_config['snmp-server'] = {}
                        snmp_config['snmp-server']['location'] = snmp_entry[0]
                        
        return snmp_config

    def _transform_line_config(self, line_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform line configuration to OpenConfig system console format."""
        console_config = {}
        
        for line_type, line_config in line_data.items():
            if line_type.startswith('con') or line_type.startswith('vty'):
                console_type = 'console' if line_type.startswith('con') else 'vty'
                
                config = {}
                if 'password' in line_config:
                    config['password'] = line_config['password'][0] if isinstance(line_config['password'], list) else line_config['password']
                if 'login' in line_config:
                    config['login'] = True
                if 'transport_input' in line_config:
                    config['transport'] = line_config['transport_input'][0] if isinstance(line_config['transport_input'], list) else line_config['transport_input']
                
                console_config[console_type] = {'config': config}
                
        return console_config

    def _transform_management_api(self, mgmt_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform management API configuration to OpenConfig format."""
        mgmt_config = {}
        
        for api_name, api_config in mgmt_data.items():
            config = {
                'name': api_name,
                'enabled': 'shutdown' not in api_config or not api_config.get('shutdown', True)
            }
            
            mgmt_config[api_name] = {'config': config}
            
        return mgmt_config
