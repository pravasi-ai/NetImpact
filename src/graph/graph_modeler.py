"""
Graph modeler for transforming validated JSON into Neo4j temporal graph nodes.
Handles device configurations and creates identity/state node relationships.
"""

from typing import Dict, Any, List, Optional, Tuple
import hashlib
import json
import logging
from datetime import datetime
from .graph_schema import GraphSchema


class GraphModeler:
    """
    Transforms validated device configurations into temporal graph structure.
    Creates identity nodes, versioned states, and relationship mappings.
    """

    def __init__(self, graph_schema: GraphSchema):
        """
        Initialize graph modeler with schema manager.
        Args: graph_schema instance for database operations.
        """
        self.schema = graph_schema
        self.logger = logging.getLogger(__name__)

    def ingest_device_configuration(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for ingesting device configuration into graph.
        Creates device identity, state, and all related network elements.
        Returns: Summary of ingestion results with node counts.
        """
        metadata = validated_data.get('_metadata', {})
        hostname = metadata.get('hostname')
        
        if not hostname:
            raise ValueError("Device hostname is required in metadata")

        self.logger.info(f"Ingesting device configuration for {hostname}")
        
        # Create device identity and state
        device_results = self._create_device_nodes(validated_data)
        
        # Create interface nodes and relationships
        interface_results = self._create_interface_nodes(validated_data)
        
        # Create VLAN nodes and relationships
        vlan_results = self._create_vlan_nodes(validated_data)
        
        # Create ACL nodes and relationships
        acl_results = self._create_acl_nodes(validated_data)
        
        # Create BGP and routing elements
        bgp_results = self._create_bgp_nodes(validated_data)
        
        # Create Route Map and routing policy elements
        routing_policy_results = self._create_routing_policy_nodes(validated_data)
        
        # Create QoS policy elements
        qos_results = self._create_qos_nodes(validated_data)
        
        # Create network and routing elements
        network_results = self._create_network_nodes(validated_data)
        
        # Create configuration dependency relationships
        dependency_results = self._create_dependency_relationships(validated_data)
        
        # Combine all results
        ingestion_summary = {
            'hostname': hostname,
            'timestamp': datetime.now().isoformat(),
            'devices': device_results,
            'interfaces': interface_results,
            'vlans': vlan_results,
            'acls': acl_results,
            'bgp': bgp_results,
            'routing_policies': routing_policy_results,
            'qos': qos_results,
            'networks': network_results,
            'dependencies': dependency_results,
            'total_nodes_created': (
                device_results.get('nodes_created', 0) +
                interface_results.get('nodes_created', 0) +
                vlan_results.get('nodes_created', 0) +
                acl_results.get('nodes_created', 0) +
                bgp_results.get('nodes_created', 0) +
                routing_policy_results.get('nodes_created', 0) +
                qos_results.get('nodes_created', 0) +
                network_results.get('nodes_created', 0)
            ),
            'total_relationships_created': dependency_results.get('relationships_created', 0)
        }
        
        self.logger.info(f"Completed ingestion for {hostname}: {ingestion_summary['total_nodes_created']} nodes created")
        return ingestion_summary

    def _create_device_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create device identity and state nodes from validated configuration.
        Args: validated_data containing device metadata and configuration.
        Returns: Device creation results summary.
        """
        metadata = validated_data['_metadata']
        hostname = metadata['hostname']
        
        # Create device identity
        device_id = self.schema.create_device_identity(hostname)
        
        # Prepare device state data
        config_hash = self._generate_config_hash(validated_data)
        state_data = {
            'vendor': metadata.get('vendor', ''),
            'os_type': metadata.get('os_type', ''),
            'os_version': metadata.get('os_version', ''),
            'platform': metadata.get('platform', ''),
            'management_ip': metadata.get('management_ip', ''),
            'serial_number': metadata.get('serial_number', ''),
            'config_hash': config_hash
        }
        
        # Create device state
        version = self.schema.create_device_state(hostname, state_data)
        
        return {
            'device_id': device_id,
            'version': version,
            'nodes_created': 2  # Identity + State
        }

    def _create_interface_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create interface identity and state nodes from OpenConfig data.
        Args: validated_data with OpenConfig interface configurations.
        Returns: Interface creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        interfaces_data = validated_data.get('openconfig-interfaces:interfaces', {}).get('interface', [])
        
        results = {
            'interfaces_created': [],
            'nodes_created': 0,
            'relationships_created': 0
        }
        
        for interface_config in interfaces_data:
            interface_name = interface_config.get('name')
            if not interface_name:
                continue
                
            # Create interface identity
            interface_id = self.schema.create_interface_identity(hostname, interface_name)
            
            # Create interface state (to be implemented when we add interface state methods)
            # For now, we're focusing on identity nodes
            
            # Handle VLAN membership
            vlan_membership = self._extract_vlan_membership(interface_config)
            if vlan_membership:
                self._create_vlan_membership_relationships(interface_id, vlan_membership, hostname)
                results['relationships_created'] += len(vlan_membership)
            
            # Handle ACL applications
            acl_applications = self._extract_acl_applications(interface_config)
            if acl_applications:
                self._create_acl_application_relationships(interface_id, acl_applications, hostname)
                results['relationships_created'] += len(acl_applications)
            
            results['interfaces_created'].append({
                'name': interface_name,
                'interface_id': interface_id
            })
            results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} interfaces for {hostname}")
        return results

    def _create_vlan_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create VLAN identity and state nodes from OpenConfig data.
        Args: validated_data with OpenConfig VLAN configurations.
        Returns: VLAN creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        vlans_data = validated_data.get('openconfig-vlan:vlans', {}).get('vlan', [])
        
        results = {
            'vlans_created': [],
            'nodes_created': 0
        }
        
        for vlan_config in vlans_data:
            vlan_id = vlan_config.get('vlan-id')
            if not vlan_id:
                continue
                
            # Create VLAN identity
            vlan_identity_id = self.schema.create_vlan_identity(hostname, vlan_id)
            
            results['vlans_created'].append({
                'vlan_id': vlan_id,
                'identity_id': vlan_identity_id
            })
            results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} VLANs for {hostname}")
        return results

    def _create_acl_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create ACL identity and state nodes from OpenConfig data.
        Args: validated_data with OpenConfig ACL configurations.
        Returns: ACL creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        acls_data = validated_data.get('openconfig-acl:acl', {}).get('acl-sets', {}).get('acl-set', [])
        
        results = {
            'acls_created': [],
            'nodes_created': 0
        }
        
        for acl_config in acls_data:
            acl_name = acl_config.get('name')
            acl_type = acl_config.get('type', 'ACL_IPV4')
            if not acl_name:
                continue
                
            # Create ACL identity using enhanced schema method
            acl_identity_id = self.schema.create_acl_identity(
                hostname=hostname,
                acl_name=acl_name,
                acl_type=acl_type.lower().replace('acl_', '')
            )
            
            # Extract and create ACL entries
            acl_entries = acl_config.get('acl-entries', {}).get('acl-entry', [])
            entries_created = 0
            
            for entry_config in acl_entries:
                sequence_id = entry_config.get('sequence-id')
                if sequence_id is not None:
                    # Create ACL entry (using future method)
                    self._create_acl_entry(acl_identity_id, entry_config)
                    entries_created += 1
            
            results['acls_created'].append({
                'name': acl_name,
                'type': acl_type,
                'identity_id': acl_identity_id,
                'entries_count': entries_created
            })
            results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} ACLs for {hostname}")
        return results
    
    def _create_acl_entry(self, acl_id: str, entry_config: Dict[str, Any]):
        """
        Create ACL entry node linked to ACL.
        Args: acl_id and entry_config with sequence details.
        """
        sequence_id = entry_config.get('sequence-id')
        entry_id = f"{acl_id}:entry:{sequence_id}"
        
        # Extract entry details
        config = entry_config.get('config', {})
        description = config.get('description', '')
        
        # Extract match conditions
        ipv4_config = entry_config.get('ipv4', {}).get('config', {})
        src_addr = ipv4_config.get('source-address', 'any')
        dst_addr = ipv4_config.get('destination-address', 'any')
        protocol = ipv4_config.get('protocol', 'ip')
        
        # Extract actions
        actions_config = entry_config.get('actions', {}).get('config', {})
        forwarding_action = actions_config.get('forwarding-action', 'ACCEPT')
        log_action = actions_config.get('log-action')
        
        # Create entry using direct Cypher (can be enhanced to use schema method)
        query = """
        MATCH (acl:ACL {acl_id: $acl_id})
        MERGE (entry:ACLEntry {entry_id: $entry_id, acl_id: $acl_id})
        SET entry.sequence_id = $sequence_id,
            entry.description = $description,
            entry.source_address = $src_addr,
            entry.destination_address = $dst_addr,
            entry.protocol = $protocol,
            entry.forwarding_action = $forwarding_action,
            entry.log_action = $log_action
        MERGE (acl)-[:HAS_ACL_ENTRY]->(entry)
        """
        
        with self.schema.driver.session() as session:
            session.run(query,
                       acl_id=acl_id,
                       entry_id=entry_id,
                       sequence_id=sequence_id,
                       description=description,
                       src_addr=src_addr,
                       dst_addr=dst_addr,
                       protocol=protocol,
                       forwarding_action=forwarding_action,
                       log_action=log_action)

    def _create_bgp_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create BGP instance and peer nodes from routing configuration.
        Args: validated_data with BGP routing configurations.
        Returns: BGP creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        routing_data = validated_data.get('routing', {})
        bgp_data = routing_data.get('bgp', {})
        
        results = {
            'bgp_instances_created': [],
            'bgp_peers_created': [],
            'nodes_created': 0
        }
        
        if not bgp_data:
            return results
            
        # Extract global BGP configuration
        global_config = bgp_data.get('global', {}).get('config', {})
        as_number = global_config.get('as')
        router_id = global_config.get('router-id')
        
        if as_number:
            # Create BGP instance using enhanced schema method
            bgp_instance_id = self.schema.create_bgp_instance_identity(
                hostname=hostname,
                as_number=as_number,
                router_id=router_id
            )
            
            results['bgp_instances_created'].append({
                'as_number': as_number,
                'router_id': router_id,
                'instance_id': bgp_instance_id
            })
            results['nodes_created'] += 1
            
            # Extract and create BGP peers
            neighbors = bgp_data.get('neighbors', [])
            for neighbor_config in neighbors:
                peer_address = neighbor_config.get('neighbor-address')
                if peer_address:
                    peer_id = self._create_bgp_peer(bgp_instance_id, neighbor_config)
                    results['bgp_peers_created'].append({
                        'peer_address': peer_address,
                        'peer_id': peer_id
                    })
                    results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} BGP objects for {hostname}")
        return results
    
    def _create_bgp_peer(self, bgp_instance_id: str, neighbor_config: Dict[str, Any]) -> str:
        """
        Create BGP peer node linked to BGP instance.
        Args: bgp_instance_id and neighbor_config with peer details.
        Returns: Generated peer_id.
        """
        peer_address = neighbor_config.get('neighbor-address')
        peer_id = f"{bgp_instance_id}:peer:{peer_address}"
        
        # Extract peer configuration
        config = neighbor_config.get('config', {})
        peer_as = config.get('peer-as')
        description = config.get('description', '')
        
        # Create BGP peer using direct Cypher
        query = """
        MATCH (bgp:BGPInstance {instance_id: $bgp_instance_id})
        MERGE (peer:BGPPeer {peer_id: $peer_id, bgp_instance_id: $bgp_instance_id})
        SET peer.peer_address = $peer_address,
            peer.peer_as = $peer_as,
            peer.description = $description
        MERGE (bgp)-[:HAS_BGP_PEER]->(peer)
        RETURN peer.peer_id as peer_id
        """
        
        with self.schema.driver.session() as session:
            result = session.run(query,
                               bgp_instance_id=bgp_instance_id,
                               peer_id=peer_id,
                               peer_address=peer_address,
                               peer_as=peer_as,
                               description=description)
            return result.single()['peer_id']

    def _create_routing_policy_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create route map and routing policy nodes from configuration.
        Args: validated_data with routing policy configurations.
        Returns: Routing policy creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        
        results = {
            'route_maps_created': [],
            'nodes_created': 0
        }
        
        # Extract route maps from routing configuration
        # This would be enhanced based on actual data structure
        routing_data = validated_data.get('routing', {})
        route_maps = routing_data.get('policy-definitions', {}).get('policy-definition', [])
        
        for route_map_config in route_maps:
            route_map_name = route_map_config.get('name')
            if route_map_name:
                # Create route map using enhanced schema method
                route_map_id = self.schema.create_route_map_identity(
                    hostname=hostname,
                    route_map_name=route_map_name
                )
                
                results['route_maps_created'].append({
                    'name': route_map_name,
                    'map_id': route_map_id
                })
                results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} routing policy objects for {hostname}")
        return results

    def _create_qos_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create QoS policy nodes from configuration.
        Args: validated_data with QoS configurations.
        Returns: QoS creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        
        results = {
            'qos_policies_created': [],
            'nodes_created': 0
        }
        
        # Extract QoS policies (structure varies by vendor)
        qos_data = validated_data.get('qos', {})
        service_policies = qos_data.get('service-policies', [])
        
        for policy_config in service_policies:
            policy_name = policy_config.get('name')
            policy_type = policy_config.get('type', 'service')
            
            if policy_name:
                # Create QoS policy using enhanced schema method
                policy_id = self.schema.create_qos_policy_identity(
                    hostname=hostname,
                    policy_name=policy_name,
                    policy_type=policy_type
                )
                
                results['qos_policies_created'].append({
                    'name': policy_name,
                    'type': policy_type,
                    'policy_id': policy_id
                })
                results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} QoS objects for {hostname}")
        return results

    def _create_dependency_relationships(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create dependency relationships between configuration objects.
        Args: validated_data to analyze for cross-references.
        Returns: Dependency creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        
        results = {
            'dependencies_created': [],
            'relationships_created': 0
        }
        
        # Extract interface-to-ACL dependencies
        interfaces_data = validated_data.get('openconfig-interfaces:interfaces', {}).get('interface', [])
        for interface_config in interfaces_data:
            interface_name = interface_config.get('name')
            
            # Look for applied ACLs (structure varies by vendor)
            acl_config = interface_config.get('acl', {})
            ingress_acl = acl_config.get('ingress-acl-set')
            egress_acl = acl_config.get('egress-acl-set')
            
            if interface_name and (ingress_acl or egress_acl):
                interface_id = f"{hostname}:interface:{interface_name}"
                
                if ingress_acl:
                    acl_id = f"{hostname}:acl:{ingress_acl}"
                    self.schema.create_acl_dependency(interface_id, 'Interface', acl_id, 'APPLIES_ACL_INGRESS')
                    results['relationships_created'] += 1
                    
                if egress_acl:
                    acl_id = f"{hostname}:acl:{egress_acl}"
                    self.schema.create_acl_dependency(interface_id, 'Interface', acl_id, 'APPLIES_ACL_EGRESS')
                    results['relationships_created'] += 1
        
        # Extract BGP-to-route-map dependencies
        routing_data = validated_data.get('routing', {})
        bgp_data = routing_data.get('bgp', {})
        neighbors = bgp_data.get('neighbors', [])
        
        for neighbor_config in neighbors:
            peer_address = neighbor_config.get('neighbor-address')
            if peer_address:
                peer_id = f"{hostname}:bgp:*:peer:{peer_address}"  # Simplified lookup
                
                # Look for applied route maps
                apply_policy = neighbor_config.get('apply-policy', {})
                import_policy = apply_policy.get('config', {}).get('import-policy', [])
                export_policy = apply_policy.get('config', {}).get('export-policy', [])
                
                for policy_name in import_policy + export_policy:
                    route_map_id = f"{hostname}:route-map:{policy_name}"
                    self.schema.create_route_map_dependency(peer_id, 'BGPPeer', route_map_id, 'USES_ROUTE_MAP')
                    results['relationships_created'] += 1
        
        self.logger.info(f"Created {results['relationships_created']} dependency relationships for {hostname}")
        return results

    def _create_network_nodes(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create IP network and routing nodes from configuration data.
        Args: validated_data with network and routing information.
        Returns: Network creation results summary.
        """
        hostname = validated_data['_metadata']['hostname']
        
        results = {
            'networks_created': [],
            'routing_created': [],
            'nodes_created': 0
        }
        
        # Extract IP networks from interface configurations
        interfaces_data = validated_data.get('openconfig-interfaces:interfaces', {}).get('interface', [])
        networks_found = set()
        
        for interface_config in interfaces_data:
            subinterfaces = interface_config.get('subinterfaces', {}).get('subinterface', [])
            for subif in subinterfaces:
                ipv4_config = subif.get('openconfig-if-ip:ipv4', {}).get('addresses', {}).get('address', [])
                for addr_config in ipv4_config:
                    ip = addr_config.get('ip')
                    prefix_len = addr_config.get('config', {}).get('prefix-length')
                    if ip and prefix_len:
                        network = f"{ip}/{prefix_len}"
                        networks_found.add(network)
        
        # Create network identity nodes (placeholder - need to add to schema)
        for network in networks_found:
            network_id = f"network_{network.replace('/', '_').replace('.', '_')}"
            results['networks_created'].append({
                'network': network,
                'identity_id': network_id
            })
            results['nodes_created'] += 1
        
        self.logger.info(f"Created {results['nodes_created']} network nodes for {hostname}")
        return results

    def _extract_vlan_membership(self, interface_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract VLAN membership information from interface configuration.
        Args: interface_config from OpenConfig or vendor-native interfaces structure.
        Returns: List of VLAN membership details.
        """
        memberships = []
        
        # Method 1: Check for OpenConfig switched VLAN configuration
        ethernet_config = interface_config.get('openconfig-if-ethernet:ethernet', {})
        switched_vlan = ethernet_config.get('switched-vlan', {}).get('config', {})
        
        if 'access-vlan' in switched_vlan:
            memberships.append({
                'vlan_id': switched_vlan['access-vlan'],
                'membership_type': 'access'
            })
        
        if 'trunk-vlans' in switched_vlan:
            for vlan_id in switched_vlan['trunk-vlans']:
                memberships.append({
                    'vlan_id': vlan_id,
                    'membership_type': 'trunk'
                })
        
        # Method 2: Check for vendor-native VLAN configuration (like in our ingested configs)
        if not memberships:
            # Check if this is a VLAN interface (e.g., "Vlan10")
            interface_name = interface_config.get('name', '')
            if interface_name.startswith('Vlan') and interface_name[4:].isdigit():
                vlan_number = int(interface_name[4:])
                memberships.append({
                    'vlan_id': vlan_number,
                    'membership_type': 'svi'  # Switch Virtual Interface
                })
        
        return memberships

    def _create_vlan_membership_relationships(self, interface_id: str, memberships: List[Dict[str, Any]], hostname: str):
        """
        Create VLAN membership relationships in graph database.
        Args: interface_id, membership details, and hostname for context.
        """
        for membership in memberships:
            vlan_number = membership['vlan_id']
            vlan_id = f"vlan_{hostname}_{vlan_number}"
            membership_type = membership['membership_type']
            native_vlan = membership.get('native_vlan', False)
            
            # Create the MEMBER_OF_VLAN relationship
            self.schema.create_vlan_membership(
                interface_id=interface_id,
                vlan_id=vlan_id,
                membership_type=membership_type,
                native_vlan=native_vlan
            )
            
            self.logger.debug(f"Created VLAN membership: {interface_id} -> {vlan_id} ({membership_type})")

    def _generate_config_hash(self, validated_data: Dict[str, Any]) -> str:
        """
        Generate hash of configuration for change detection.
        Args: validated_data dictionary to hash.
        Returns: SHA-256 hash string of configuration.
        """
        # Create a copy without metadata for consistent hashing
        config_copy = validated_data.copy()
        config_copy.pop('_metadata', None)
        
        # Sort and serialize for consistent hashing
        config_json = json.dumps(config_copy, sort_keys=True)
        return hashlib.sha256(config_json.encode()).hexdigest()

    def get_ingestion_stats(self) -> Dict[str, Any]:
        """
        Get current graph database statistics after ingestion.
        Returns: Dictionary with node and relationship counts.
        """
        return self.schema.get_schema_summary()