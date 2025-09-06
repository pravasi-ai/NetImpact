"""
Graph schema implementation for temporal network configuration modeling.
Defines node types, relationships, and constraints for Neo4j database.
"""

from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add project root to Python path for proper imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config


class GraphSchema:
    """
    Manages Neo4j graph schema with temporal pattern implementation.
    Creates constraints, indexes, and provides schema validation.
    """

    def __init__(self, neo4j_uri: str, username: str, password: str):
        """
        Initialize graph schema manager with Neo4j connection.
        Args: neo4j_uri, username, and password for database connection.
        """
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(username, password))
        self.logger = logging.getLogger(__name__)

    @classmethod
    def from_config(cls):
        """
        Create GraphSchema instance using application configuration.
        Returns: Configured GraphSchema instance.
        """
        neo4j_config = config.get_neo4j_config()
        return cls(
            neo4j_config['uri'],
            neo4j_config['username'], 
            neo4j_config['password']
        )

    def close(self):
        """
        Close Neo4j driver connection.
        """
        if self.driver:
            self.driver.close()

    def create_constraints(self) -> None:
        """
        Create unique constraints for identity nodes.
        Ensures data integrity across all node types.
        """
        constraints = [
            # Core identity node unique constraints
            "CREATE CONSTRAINT device_hostname_unique IF NOT EXISTS FOR (d:Device) REQUIRE d.hostname IS UNIQUE",
            "CREATE CONSTRAINT interface_id_unique IF NOT EXISTS FOR (i:Interface) REQUIRE i.interface_id IS UNIQUE", 
            "CREATE CONSTRAINT vlan_id_unique IF NOT EXISTS FOR (v:VLAN) REQUIRE v.vlan_id IS UNIQUE",
            "CREATE CONSTRAINT network_id_unique IF NOT EXISTS FOR (n:IPNetwork) REQUIRE n.network_id IS UNIQUE",
            
            # Security configuration objects
            "CREATE CONSTRAINT acl_id_unique IF NOT EXISTS FOR (a:ACL) REQUIRE a.acl_id IS UNIQUE",
            "CREATE CONSTRAINT acl_entry_id_unique IF NOT EXISTS FOR (ae:ACLEntry) REQUIRE ae.entry_id IS UNIQUE",
            
            # Routing configuration objects  
            "CREATE CONSTRAINT bgp_instance_id_unique IF NOT EXISTS FOR (b:BGPInstance) REQUIRE b.instance_id IS UNIQUE",
            "CREATE CONSTRAINT bgp_peer_id_unique IF NOT EXISTS FOR (bp:BGPPeer) REQUIRE bp.peer_id IS UNIQUE",
            "CREATE CONSTRAINT route_map_id_unique IF NOT EXISTS FOR (rm:RouteMap) REQUIRE rm.map_id IS UNIQUE",
            "CREATE CONSTRAINT prefix_list_id_unique IF NOT EXISTS FOR (pl:PrefixList) REQUIRE pl.list_id IS UNIQUE",
            "CREATE CONSTRAINT community_list_id_unique IF NOT EXISTS FOR (cl:CommunityList) REQUIRE cl.list_id IS UNIQUE",
            "CREATE CONSTRAINT ospf_instance_id_unique IF NOT EXISTS FOR (o:OSPFInstance) REQUIRE o.instance_id IS UNIQUE",
            "CREATE CONSTRAINT static_route_id_unique IF NOT EXISTS FOR (sr:StaticRoute) REQUIRE sr.route_id IS UNIQUE",
            
            # QoS configuration objects
            "CREATE CONSTRAINT qos_policy_id_unique IF NOT EXISTS FOR (qp:QoSPolicy) REQUIRE qp.policy_id IS UNIQUE",
            "CREATE CONSTRAINT class_map_id_unique IF NOT EXISTS FOR (cm:ClassMap) REQUIRE cm.map_id IS UNIQUE",
            "CREATE CONSTRAINT policy_map_id_unique IF NOT EXISTS FOR (pm:PolicyMap) REQUIRE pm.map_id IS UNIQUE",
            
            # Interface configuration objects
            "CREATE CONSTRAINT port_channel_id_unique IF NOT EXISTS FOR (pc:PortChannel) REQUIRE pc.channel_id IS UNIQUE",
            "CREATE CONSTRAINT vrf_id_unique IF NOT EXISTS FOR (vrf:VRF) REQUIRE vrf.vrf_id IS UNIQUE",
            "CREATE CONSTRAINT svi_id_unique IF NOT EXISTS FOR (svi:SVI) REQUIRE svi.svi_id IS UNIQUE",
            
            # Management configuration objects
            "CREATE CONSTRAINT snmp_community_id_unique IF NOT EXISTS FOR (sc:SNMPCommunity) REQUIRE sc.community_id IS UNIQUE",
            "CREATE CONSTRAINT ntp_server_id_unique IF NOT EXISTS FOR (ntp:NTPServer) REQUIRE ntp.server_id IS UNIQUE",
            "CREATE CONSTRAINT logging_destination_id_unique IF NOT EXISTS FOR (ld:LoggingDestination) REQUIRE ld.destination_id IS UNIQUE"
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                    self.logger.info(f"Created constraint: {constraint.split()[2]}")
                except Exception as e:
                    self.logger.warning(f"Constraint creation failed: {e}")

    def create_indexes(self) -> None:
        """
        Create performance indexes for common query patterns.
        Optimizes dependency traversal and state lookups.
        """
        indexes = [
            # Core query performance indexes
            "CREATE INDEX device_hostname_idx IF NOT EXISTS FOR (d:Device) ON (d.hostname)",
            "CREATE INDEX interface_device_idx IF NOT EXISTS FOR (i:Interface) ON (i.device_hostname)",
            "CREATE INDEX interface_name_idx IF NOT EXISTS FOR (i:Interface) ON (i.name)",
            "CREATE INDEX vlan_number_idx IF NOT EXISTS FOR (v:VLAN) ON (v.vlan_number)",
            
            # Security configuration indexes
            "CREATE INDEX acl_name_idx IF NOT EXISTS FOR (a:ACL) ON (a.name)",
            "CREATE INDEX acl_device_idx IF NOT EXISTS FOR (a:ACL) ON (a.device_hostname)",
            "CREATE INDEX acl_entry_sequence_idx IF NOT EXISTS FOR (ae:ACLEntry) ON (ae.sequence_id)",
            
            # Routing configuration indexes  
            "CREATE INDEX bgp_instance_as_idx IF NOT EXISTS FOR (b:BGPInstance) ON (b.as_number)",
            "CREATE INDEX bgp_peer_address_idx IF NOT EXISTS FOR (bp:BGPPeer) ON (bp.peer_address)",
            "CREATE INDEX route_map_name_idx IF NOT EXISTS FOR (rm:RouteMap) ON (rm.name)",
            "CREATE INDEX prefix_list_name_idx IF NOT EXISTS FOR (pl:PrefixList) ON (pl.name)",
            "CREATE INDEX community_list_name_idx IF NOT EXISTS FOR (cl:CommunityList) ON (cl.name)",
            "CREATE INDEX ospf_instance_process_idx IF NOT EXISTS FOR (o:OSPFInstance) ON (o.process_id)",
            "CREATE INDEX static_route_destination_idx IF NOT EXISTS FOR (sr:StaticRoute) ON (sr.destination_network)",
            
            # QoS configuration indexes
            "CREATE INDEX qos_policy_name_idx IF NOT EXISTS FOR (qp:QoSPolicy) ON (qp.name)",
            "CREATE INDEX class_map_name_idx IF NOT EXISTS FOR (cm:ClassMap) ON (cm.name)",
            "CREATE INDEX policy_map_name_idx IF NOT EXISTS FOR (pm:PolicyMap) ON (pm.name)",
            
            # Interface configuration indexes
            "CREATE INDEX port_channel_name_idx IF NOT EXISTS FOR (pc:PortChannel) ON (pc.name)",
            "CREATE INDEX vrf_name_idx IF NOT EXISTS FOR (vrf:VRF) ON (vrf.name)",
            "CREATE INDEX svi_vlan_idx IF NOT EXISTS FOR (svi:SVI) ON (svi.vlan_number)",
            
            # Management configuration indexes  
            "CREATE INDEX snmp_community_name_idx IF NOT EXISTS FOR (sc:SNMPCommunity) ON (sc.community_name)",
            "CREATE INDEX ntp_server_address_idx IF NOT EXISTS FOR (ntp:NTPServer) ON (ntp.server_address)",
            "CREATE INDEX logging_destination_host_idx IF NOT EXISTS FOR (ld:LoggingDestination) ON (ld.destination_host)",
            
            # State version indexes (existing + new)
            "CREATE INDEX device_state_timestamp_idx IF NOT EXISTS FOR (ds:DeviceState) ON (ds.timestamp)",
            "CREATE INDEX device_state_version_idx IF NOT EXISTS FOR (ds:DeviceState) ON (ds.version)",
            "CREATE INDEX interface_state_timestamp_idx IF NOT EXISTS FOR (is:InterfaceState) ON (is.timestamp)",
            "CREATE INDEX vlan_state_timestamp_idx IF NOT EXISTS FOR (vs:VLANState) ON (vs.timestamp)",
            "CREATE INDEX acl_state_timestamp_idx IF NOT EXISTS FOR (as:ACLState) ON (as.timestamp)",
            "CREATE INDEX bgp_state_timestamp_idx IF NOT EXISTS FOR (bs:BGPState) ON (bs.timestamp)",
            "CREATE INDEX route_map_state_timestamp_idx IF NOT EXISTS FOR (rms:RouteMapState) ON (rms.timestamp)"
        ]

        with self.driver.session() as session:
            for index in indexes:
                try:
                    session.run(index)
                    self.logger.info(f"Created index: {index.split()[2]}")
                except Exception as e:
                    self.logger.warning(f"Index creation failed: {e}")

    def initialize_schema(self) -> None:
        """
        Initialize complete graph schema with constraints and indexes.
        Sets up database structure for temporal network modeling.
        """
        self.logger.info("Initializing graph schema...")
        self.create_constraints()
        self.create_indexes()
        self.logger.info("Graph schema initialization complete")

    def create_device_identity(self, hostname: str, device_id: str = None) -> str:
        """
        Create device identity node if it doesn't exist.
        Args: hostname and optional device_id for device identification.
        Returns: Generated or existing device_id.
        """
        if not device_id:
            device_id = f"device_{hostname}"

        query = """
        MERGE (d:Device {hostname: $hostname})
        ON CREATE SET d.device_id = $device_id, 
                     d.created_at = datetime()
        RETURN d.device_id as device_id
        """
        
        with self.driver.session() as session:
            result = session.run(query, hostname=hostname, device_id=device_id)
            return result.single()["device_id"]

    def create_device_state(self, hostname: str, state_data: Dict[str, Any], version: int = None) -> int:
        """
        Create new device state version and update LATEST relationship.
        Args: hostname, state_data dict, and optional version number.
        Returns: Version number of created state.
        """
        # Generate version if not provided
        if version is None:
            version = self._get_next_version(hostname, "DeviceState")

        query = """
        MATCH (d:Device {hostname: $hostname})
        
        // Create new state node
        CREATE (ds:DeviceState {
            version: $version,
            timestamp: datetime(),
            vendor: $vendor,
            os_type: $os_type, 
            os_version: $os_version,
            platform: $platform,
            management_ip: $management_ip,
            serial_number: $serial_number,
            config_hash: $config_hash
        })
        
        // Link to device identity
        CREATE (d)-[:HAS_STATE]->(ds)
        
        WITH d, ds
        
        // Update LATEST relationship
        OPTIONAL MATCH (d)-[old_latest:LATEST]->(old_state:DeviceState)
        DELETE old_latest
        CREATE (d)-[:LATEST]->(ds)
        
        // Link to previous state
        WITH d, ds, old_state
        WHERE old_state IS NOT NULL
        CREATE (old_state)-[:PREVIOUS_STATE]->(ds)
        
        RETURN ds.version as version
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                hostname=hostname,
                version=version,
                vendor=state_data.get('vendor', ''),
                os_type=state_data.get('os_type', ''),
                os_version=state_data.get('os_version', ''),
                platform=state_data.get('platform', ''),
                management_ip=state_data.get('management_ip', ''),
                serial_number=state_data.get('serial_number', ''),
                config_hash=state_data.get('config_hash', '')
            )
            record = result.single()
            if record:
                return record["version"]
            else:
                return version  # Return provided version if query didn't return result

    def create_interface_identity(self, hostname: str, interface_name: str, interface_id: str = None) -> str:
        """
        Create interface identity node linked to device.
        Args: hostname, interface_name, and optional interface_id.
        Returns: Generated or existing interface_id.
        """
        if not interface_id:
            interface_id = f"interface_{hostname}_{interface_name}"

        query = """
        MATCH (d:Device {hostname: $hostname})
        MERGE (i:Interface {interface_id: $interface_id})
        ON CREATE SET i.name = $interface_name,
                     i.device_hostname = $hostname,
                     i.created_at = datetime()
        
        // Create device-interface relationship
        MERGE (d)-[:HAS_INTERFACE]->(i)
        
        RETURN i.interface_id as interface_id
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                hostname=hostname,
                interface_name=interface_name,
                interface_id=interface_id
            )
            return result.single()["interface_id"]

    def create_vlan_identity(self, hostname: str, vlan_number: int, vlan_id: str = None) -> str:
        """
        Create VLAN identity node for device.
        Args: hostname, vlan_number, and optional vlan_id.
        Returns: Generated or existing vlan_id.
        """
        if not vlan_id:
            vlan_id = f"vlan_{hostname}_{vlan_number}"

        query = """
        MATCH (d:Device {hostname: $hostname})
        MERGE (v:VLAN {vlan_id: $vlan_id})
        ON CREATE SET v.vlan_number = $vlan_number,
                     v.device_hostname = $hostname,
                     v.created_at = datetime()
        
        RETURN v.vlan_id as vlan_id
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                hostname=hostname,
                vlan_number=vlan_number,
                vlan_id=vlan_id
            )
            return result.single()["vlan_id"]
    
    def create_vlan_membership(self, interface_id: str, vlan_id: str, membership_type: str = 'access', native_vlan: bool = False):
        """
        Create VLAN membership relationship between interface and VLAN.
        Args: interface_id, vlan_id, membership_type, and native_vlan flag.
        """
        query = """
        MATCH (i:Interface {interface_id: $interface_id})
        MATCH (v:VLAN {vlan_id: $vlan_id})
        
        MERGE (i)-[r:MEMBER_OF_VLAN]->(v)
        SET r.membership_type = $membership_type,
            r.native_vlan = $native_vlan,
            r.created_at = datetime()
        
        RETURN r
        """
        
        with self.driver.session() as session:
            session.run(
                query,
                interface_id=interface_id,
                vlan_id=vlan_id,
                membership_type=membership_type,
                native_vlan=native_vlan
            )

    def create_physical_connection(self, source_interface_id: str, target_interface_id: str, 
                                 connection_data: Dict[str, Any]) -> None:
        """
        Create physical connectivity relationship between interfaces.
        Args: source_interface_id, target_interface_id, and connection metadata.
        """
        query = """
        MATCH (source:Interface {interface_id: $source_id})
        MATCH (target:Interface {interface_id: $target_id})
        
        MERGE (source)-[conn:CONNECTED_TO]->(target)
        SET conn.connection_type = $connection_type,
            conn.discovered_via = $discovered_via,
            conn.confirmed_at = datetime()
        """

        with self.driver.session() as session:
            session.run(
                query,
                source_id=source_interface_id,
                target_id=target_interface_id,
                connection_type=connection_data.get('connection_type', 'ethernet'),
                discovered_via=connection_data.get('discovered_via', 'lldp')
            )

    def _get_next_version(self, hostname: str, state_type: str) -> int:
        """
        Get next version number for device state.
        Args: hostname and state_type for version sequence.
        Returns: Next version number in sequence.
        """
        query = f"""
        MATCH (d:Device {{hostname: $hostname}})-[:HAS_STATE]->(s:{state_type})
        RETURN COALESCE(MAX(s.version), 0) + 1 as next_version
        """

        with self.driver.session() as session:
            result = session.run(query, hostname=hostname)
            return result.single()["next_version"]

    def get_schema_summary(self) -> Dict[str, Any]:
        """
        Return summary of current graph schema state.
        Returns: Dictionary with node counts, relationship counts, and schema info.
        """
        queries = {
            # Core objects
            'devices': 'MATCH (d:Device) RETURN count(d) as count',
            'interfaces': 'MATCH (i:Interface) RETURN count(i) as count',
            'vlans': 'MATCH (v:VLAN) RETURN count(v) as count',
            
            # Security configuration objects
            'acls': 'MATCH (a:ACL) RETURN count(a) as count',
            'acl_entries': 'MATCH (ae:ACLEntry) RETURN count(ae) as count',
            
            # Routing configuration objects
            'bgp_instances': 'MATCH (b:BGPInstance) RETURN count(b) as count',
            'bgp_peers': 'MATCH (bp:BGPPeer) RETURN count(bp) as count',
            'route_maps': 'MATCH (rm:RouteMap) RETURN count(rm) as count',
            'prefix_lists': 'MATCH (pl:PrefixList) RETURN count(pl) as count',
            'ospf_instances': 'MATCH (o:OSPFInstance) RETURN count(o) as count',
            'static_routes': 'MATCH (sr:StaticRoute) RETURN count(sr) as count',
            
            # QoS configuration objects
            'qos_policies': 'MATCH (qp:QoSPolicy) RETURN count(qp) as count',
            'class_maps': 'MATCH (cm:ClassMap) RETURN count(cm) as count',
            'policy_maps': 'MATCH (pm:PolicyMap) RETURN count(pm) as count',
            
            # Interface configuration objects
            'port_channels': 'MATCH (pc:PortChannel) RETURN count(pc) as count',
            'vrfs': 'MATCH (vrf:VRF) RETURN count(vrf) as count',
            'svis': 'MATCH (svi:SVI) RETURN count(svi) as count',
            
            # State objects
            'device_states': 'MATCH (ds:DeviceState) RETURN count(ds) as count',
            'interface_states': 'MATCH (is:InterfaceState) RETURN count(is) as count',
            
            # Relationships
            'connections': 'MATCH ()-[c:CONNECTED_TO]->() RETURN count(c) as count',
            'acl_dependencies': 'MATCH ()-[ad:APPLIES_ACL]->() RETURN count(ad) as count',
            'route_map_dependencies': 'MATCH ()-[rm:USES_ROUTE_MAP]->() RETURN count(rm) as count',
            'qos_dependencies': 'MATCH ()-[qd:APPLIES_QOS_POLICY]->() RETURN count(qd) as count'
        }

        summary = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                try:
                    result = session.run(query)
                    summary[key] = result.single()["count"]
                except Exception as e:
                    self.logger.warning(f"Summary query failed for {key}: {e}")
                    summary[key] = 0

        return summary

    # ==================== UNIVERSAL CONFIGURATION OBJECT METHODS ====================
    
    def create_acl_identity(self, hostname: str, acl_name: str, acl_type: str = 'standard') -> str:
        """
        Create ACL identity node linked to device.
        Args: hostname, acl_name, and acl_type.
        Returns: Generated acl_id.
        """
        acl_id = f"{hostname}:acl:{acl_name}"
        
        query = """
        MERGE (d:Device {hostname: $hostname})
        MERGE (a:ACL {acl_id: $acl_id, name: $acl_name, device_hostname: $hostname})
        SET a.acl_type = $acl_type
        MERGE (d)-[:HAS_ACL]->(a)
        RETURN a.acl_id as acl_id
        """
        
        with self.driver.session() as session:
            result = session.run(query, 
                               hostname=hostname, 
                               acl_id=acl_id,
                               acl_name=acl_name,
                               acl_type=acl_type)
            return result.single()['acl_id']

    def create_bgp_instance_identity(self, hostname: str, as_number: int, router_id: str = None) -> str:
        """
        Create BGP instance identity node linked to device.
        Args: hostname, as_number, and optional router_id.
        Returns: Generated bgp_instance_id.
        """
        instance_id = f"{hostname}:bgp:{as_number}"
        
        query = """
        MERGE (d:Device {hostname: $hostname})
        MERGE (b:BGPInstance {instance_id: $instance_id, device_hostname: $hostname})
        SET b.as_number = $as_number,
            b.router_id = $router_id
        MERGE (d)-[:HAS_BGP_INSTANCE]->(b)
        RETURN b.instance_id as instance_id
        """
        
        with self.driver.session() as session:
            result = session.run(query,
                               hostname=hostname,
                               instance_id=instance_id,
                               as_number=as_number,
                               router_id=router_id)
            return result.single()['instance_id']

    def create_route_map_identity(self, hostname: str, route_map_name: str) -> str:
        """
        Create route map identity node linked to device.
        Args: hostname and route_map_name.
        Returns: Generated route_map_id.
        """
        map_id = f"{hostname}:route-map:{route_map_name}"
        
        query = """
        MERGE (d:Device {hostname: $hostname})
        MERGE (rm:RouteMap {map_id: $map_id, name: $route_map_name, device_hostname: $hostname})
        MERGE (d)-[:HAS_ROUTE_MAP]->(rm)
        RETURN rm.map_id as map_id
        """
        
        with self.driver.session() as session:
            result = session.run(query,
                               hostname=hostname,
                               map_id=map_id,
                               route_map_name=route_map_name)
            return result.single()['map_id']

    def create_qos_policy_identity(self, hostname: str, policy_name: str, policy_type: str = 'service') -> str:
        """
        Create QoS policy identity node linked to device.
        Args: hostname, policy_name, and policy_type.
        Returns: Generated policy_id.
        """
        policy_id = f"{hostname}:qos:{policy_name}"
        
        query = """
        MERGE (d:Device {hostname: $hostname})
        MERGE (qp:QoSPolicy {policy_id: $policy_id, name: $policy_name, device_hostname: $hostname})
        SET qp.policy_type = $policy_type
        MERGE (d)-[:HAS_QOS_POLICY]->(qp)
        RETURN qp.policy_id as policy_id
        """
        
        with self.driver.session() as session:
            result = session.run(query,
                               hostname=hostname,
                               policy_id=policy_id,
                               policy_name=policy_name,
                               policy_type=policy_type)
            return result.single()['policy_id']

    # ==================== DEPENDENCY RELATIONSHIP METHODS ====================
    
    def create_acl_dependency(self, from_object_id: str, from_object_type: str, acl_id: str, dependency_type: str = 'APPLIES_ACL'):
        """
        Create dependency relationship between any config object and ACL.
        Args: from_object_id, from_object_type, acl_id, and dependency_type.
        """
        query = f"""
        MATCH (source:{from_object_type} {{{'interface_id' if from_object_type == 'Interface' else 'instance_id' if 'Instance' in from_object_type else 'device_id'}: $from_object_id}})
        MATCH (acl:ACL {{acl_id: $acl_id}})
        MERGE (source)-[r:{dependency_type}]->(acl)
        SET r.created_at = datetime()
        """
        
        with self.driver.session() as session:
            session.run(query, from_object_id=from_object_id, acl_id=acl_id)

    def create_route_map_dependency(self, from_object_id: str, from_object_type: str, route_map_id: str, dependency_type: str = 'USES_ROUTE_MAP'):
        """
        Create dependency relationship between any config object and route map.
        Args: from_object_id, from_object_type, route_map_id, and dependency_type.
        """
        query = f"""
        MATCH (source:{from_object_type} {{{'peer_id' if from_object_type == 'BGPPeer' else 'instance_id'}: $from_object_id}})
        MATCH (rm:RouteMap {{map_id: $route_map_id}})
        MERGE (source)-[r:{dependency_type}]->(rm)
        SET r.created_at = datetime()
        """
        
        with self.driver.session() as session:
            session.run(query, from_object_id=from_object_id, route_map_id=route_map_id)

    def create_qos_policy_dependency(self, from_object_id: str, from_object_type: str, policy_id: str, dependency_type: str = 'APPLIES_QOS_POLICY'):
        """
        Create dependency relationship between interface and QoS policy.
        Args: from_object_id, from_object_type, policy_id, and dependency_type.
        """
        query = f"""
        MATCH (source:{from_object_type} {{interface_id: $from_object_id}})
        MATCH (qp:QoSPolicy {{policy_id: $policy_id}})
        MERGE (source)-[r:{dependency_type}]->(qp)
        SET r.created_at = datetime()
        """
        
        with self.driver.session() as session:
            session.run(query, from_object_id=from_object_id, policy_id=policy_id)