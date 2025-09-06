"""
Topology data ingestion from LLDP and BGP neighbor CSV files.
Creates physical connectivity and routing relationships in the graph.
"""

import csv
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging
from .graph_schema import GraphSchema
from .cypher_queries import CypherQueries


class TopologyLoader:
    """
    Loads network topology data from CSV files into graph database.
    Handles LLDP physical connections and BGP peering relationships.
    """

    def __init__(self, graph_schema: GraphSchema):
        """
        Initialize topology loader with graph schema.
        Args: graph_schema instance for database operations.
        """
        self.schema = graph_schema
        self.logger = logging.getLogger(__name__)

    def load_all_topology_files(self, topology_path: Path) -> Dict[str, Any]:
        """
        Load all topology files from directory into graph database.
        Args: topology_path directory containing CSV files.
        Returns: Summary of topology loading results.
        """
        if not topology_path.exists():
            raise ValueError(f"Topology directory does not exist: {topology_path}")

        self.logger.info(f"Loading topology files from {topology_path}")
        
        # Load LLDP neighbor files
        lldp_results = self._load_lldp_files(topology_path)
        
        # Load BGP peer files
        bgp_results = self._load_bgp_files(topology_path)
        
        # Combine results
        summary = {
            'topology_path': str(topology_path),
            'lldp_results': lldp_results,
            'bgp_results': bgp_results,
            'total_connections': lldp_results['connections_created'] + bgp_results['peers_created'],
            'files_processed': lldp_results['files_processed'] + bgp_results['files_processed']
        }
        
        self.logger.info(f"Topology loading complete: {summary['total_connections']} connections created")
        return summary

    def _load_lldp_files(self, topology_path: Path) -> Dict[str, Any]:
        """
        Load all LLDP neighbor files and create physical connections.
        Args: topology_path directory containing lldp_neigh.*.csv files.
        Returns: LLDP loading results summary.
        """
        lldp_files = list(topology_path.glob("lldp_neigh.*.csv"))
        
        results = {
            'files_processed': 0,
            'connections_created': 0,
            'devices_processed': [],
            'errors': []
        }
        
        for lldp_file in lldp_files:
            try:
                device_results = self._process_lldp_file(lldp_file)
                results['files_processed'] += 1
                results['connections_created'] += device_results['connections_created']
                results['devices_processed'].append(device_results['hostname'])
                
            except Exception as e:
                error_msg = f"Failed to process {lldp_file.name}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        self.logger.info(f"Processed {results['files_processed']} LLDP files, created {results['connections_created']} connections")
        return results

    def _process_lldp_file(self, lldp_file: Path) -> Dict[str, Any]:
        """
        Process single LLDP neighbor file and create connections.
        Args: lldp_file path to CSV file with neighbor data.
        Returns: Processing results for the file.
        """
        # Extract hostname from filename (e.g., lldp_neigh.core-sw-01.csv -> core-sw-01)
        hostname = lldp_file.stem.replace('lldp_neigh.', '')
        
        connections_created = 0
        
        with open(lldp_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self._create_lldp_connection(hostname, row)
                    connections_created += 1
                except Exception as e:
                    self.logger.warning(f"Failed to create LLDP connection for {hostname}: {e}")
        
        return {
            'hostname': hostname,
            'connections_created': connections_created,
            'file': str(lldp_file)
        }

    def _create_lldp_connection(self, hostname: str, neighbor_data: Dict[str, str]):
        """
        Create physical connection between interfaces based on LLDP data.
        Args: hostname and neighbor_data row from CSV.
        """
        local_interface = neighbor_data.get('local_interface')
        remote_hostname = neighbor_data.get('neighbor_hostname') 
        remote_interface = neighbor_data.get('neighbor_interface')
        
        if not all([local_interface, remote_hostname, remote_interface]):
            self.logger.warning(f"Incomplete LLDP data for {hostname}: {neighbor_data}")
            return
        
        # Create interface IDs
        local_interface_id = f"interface_{hostname}_{local_interface}"
        remote_interface_id = f"interface_{remote_hostname}_{remote_interface}"
        
        # Create connection using Cypher query
        connection_data = {
            'connection_type': 'ethernet',  # Default for LLDP
            'discovered_via': 'lldp',
            'confirmed_at': 'datetime()'
        }
        
        query = """
        MATCH (local_if:Interface {interface_id: $local_interface_id})
        MATCH (remote_if:Interface {interface_id: $remote_interface_id})
        
        MERGE (local_if)-[conn:CONNECTED_TO]->(remote_if)
        SET conn.connection_type = $connection_type,
            conn.discovered_via = $discovered_via,
            conn.confirmed_at = datetime()
        
        RETURN conn
        """
        
        with self.schema.driver.session() as session:
            session.run(
                query,
                local_interface_id=local_interface_id,
                remote_interface_id=remote_interface_id,
                connection_type=connection_data['connection_type'],
                discovered_via=connection_data['discovered_via']
            )
        
        self.logger.debug(f"Created LLDP connection: {hostname}:{local_interface} <-> {remote_hostname}:{remote_interface}")

    def _load_bgp_files(self, topology_path: Path) -> Dict[str, Any]:
        """
        Load all BGP peer files and create peering relationships.
        Args: topology_path directory containing bgp_peers.*.csv files.
        Returns: BGP loading results summary.
        """
        bgp_files = list(topology_path.glob("bgp_peers.*.csv"))
        
        results = {
            'files_processed': 0,
            'peers_created': 0,
            'devices_processed': [],
            'errors': []
        }
        
        for bgp_file in bgp_files:
            try:
                device_results = self._process_bgp_file(bgp_file)
                results['files_processed'] += 1
                results['peers_created'] += device_results['peers_created']
                results['devices_processed'].append(device_results['hostname'])
                
            except Exception as e:
                error_msg = f"Failed to process {bgp_file.name}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        self.logger.info(f"Processed {results['files_processed']} BGP files, created {results['peers_created']} peers")
        return results

    def _process_bgp_file(self, bgp_file: Path) -> Dict[str, Any]:
        """
        Process single BGP peers file and create peering relationships.
        Args: bgp_file path to CSV file with BGP peer data.
        Returns: Processing results for the file.
        """
        # Extract hostname from filename (e.g., bgp_peers.core-sw-01.csv -> core-sw-01)
        hostname = bgp_file.stem.replace('bgp_peers.', '')
        
        peers_created = 0
        
        with open(bgp_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self._create_bgp_peer(hostname, row)
                    peers_created += 1
                except Exception as e:
                    self.logger.warning(f"Failed to create BGP peer for {hostname}: {e}")
        
        return {
            'hostname': hostname,
            'peers_created': peers_created,
            'file': str(bgp_file)
        }

    def _create_bgp_peer(self, hostname: str, peer_data: Dict[str, str]):
        """
        Create BGP peering relationship based on peer data.
        Args: hostname and peer_data row from CSV.
        """
        peer_ip = peer_data.get('peer_ip')
        peer_hostname = peer_data.get('peer_hostname', 'unknown')
        peer_asn = peer_data.get('peer_asn', '65000')
        peer_type = peer_data.get('peer_type', 'ibgp')
        session_state = peer_data.get('session_state', 'unknown')
        
        if not peer_ip:
            self.logger.warning(f"Missing peer_ip in BGP data for {hostname}: {peer_data}")
            return
        
        # Create BGP peer identity
        peer_id = f"bgp_{hostname}_{peer_ip}"
        
        # Create BGP peer nodes and relationships
        query = """
        // Create BGP peer identity
        MERGE (b:BGPPeer {peer_id: $peer_id})
        ON CREATE SET b.local_hostname = $local_hostname,
                     b.peer_ip = $peer_ip,
                     b.created_at = datetime()
        
        // Create BGP peer state
        CREATE (bs:BGPPeerState {
            version: 1,
            timestamp: datetime(),
            peer_asn: $peer_asn,
            session_state: $session_state,
            description: $description
        })
        
        CREATE (b)-[:HAS_STATE]->(bs)
        CREATE (b)-[:LATEST]->(bs)
        
        WITH b, bs
        
        // Link to local device
        MATCH (local_device:Device {hostname: $local_hostname})
        MERGE (local_device)-[r1:BGP_PEER_WITH]->(b)
        SET r1.local_ip = 'unknown',
            r1.peer_ip = $peer_ip
        
        WITH b, bs
        
        // Link to remote device if known
        OPTIONAL MATCH (remote_device:Device {hostname: $peer_hostname})
        FOREACH (rd IN CASE WHEN remote_device IS NOT NULL THEN [remote_device] ELSE [] END |
            MERGE (b)<-[r2:BGP_PEER_WITH]-(rd)
            SET r2.local_ip = $peer_ip,
                r2.peer_ip = 'unknown'
        )
        
        RETURN b.peer_id as peer_id
        """
        
        with self.schema.driver.session() as session:
            result = session.run(
                query,
                peer_id=peer_id,
                local_hostname=hostname,
                peer_ip=peer_ip,
                peer_hostname=peer_hostname,
                peer_asn=int(peer_asn) if peer_asn.isdigit() else 65000,
                session_state=session_state,
                description=f"BGP {peer_type} peer"
            )
            
        self.logger.debug(f"Created BGP peer: {hostname} -> {peer_ip} (AS{peer_asn})")

    def create_site_topology(self, site_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create site hierarchy and device locations for topology visualization.
        Args: site_data list with site and device location information.
        Returns: Site creation results summary.
        """
        results = {
            'sites_created': 0,
            'device_locations_created': 0,
            'errors': []
        }
        
        for site_info in site_data:
            try:
                site_id = self._create_site(site_info)
                results['sites_created'] += 1
                
                # Create device locations for this site
                for device_location in site_info.get('devices', []):
                    self._create_device_location(device_location, site_id)
                    results['device_locations_created'] += 1
                    
            except Exception as e:
                error_msg = f"Failed to create site {site_info.get('name', 'unknown')}: {e}"
                self.logger.error(error_msg)
                results['errors'].append(error_msg)
        
        return results

    def _create_site(self, site_info: Dict[str, Any]) -> str:
        """
        Create site identity node for geographic hierarchy.
        Args: site_info with site details.
        Returns: Created site_id.
        """
        site_id = site_info.get('site_id') or f"site_{site_info['name'].lower().replace(' ', '_')}"
        
        query = """
        MERGE (s:Site {site_id: $site_id})
        ON CREATE SET s.name = $name,
                     s.type = $type,
                     s.address = $address,
                     s.coordinates = $coordinates,
                     s.created_at = datetime()
        RETURN s.site_id as site_id
        """
        
        with self.schema.driver.session() as session:
            result = session.run(
                query,
                site_id=site_id,
                name=site_info.get('name', ''),
                type=site_info.get('type', 'datacenter'),
                address=site_info.get('address', ''),
                coordinates=site_info.get('coordinates', '')
            )
            
        self.logger.debug(f"Created site: {site_id}")
        return site_id

    def _create_device_location(self, device_location: Dict[str, Any], site_id: str):
        """
        Create device location relationship and layout information.
        Args: device_location details and site_id for location.
        """
        hostname = device_location.get('hostname')
        if not hostname:
            return
        
        # Create location relationship
        location_query = """
        MATCH (d:Device {hostname: $hostname})
        MATCH (s:Site {site_id: $site_id})
        
        MERGE (d)-[r:LOCATED_AT]->(s)
        SET r.installation_date = $installation_date,
            r.rack_name = $rack_name
        
        RETURN r
        """
        
        # Create device layout for visualization
        layout_query = """
        MATCH (d:Device {hostname: $hostname})
        
        CREATE (dl:DeviceLayout {
            version: 1,
            timestamp: datetime(),
            x_position: $x_position,
            y_position: $y_position,
            layer: $layer,
            icon_type: $icon_type,
            rack_unit: $rack_unit,
            status_color: $status_color
        })
        
        CREATE (d)-[:HAS_STATE]->(dl)
        CREATE (d)-[:LATEST]->(dl)
        
        RETURN dl.version as version
        """
        
        with self.schema.driver.session() as session:
            # Create location
            session.run(
                location_query,
                hostname=hostname,
                site_id=site_id,
                installation_date=device_location.get('installation_date', 'unknown'),
                rack_name=device_location.get('rack_name', 'unknown')
            )
            
            # Create layout
            session.run(
                layout_query,
                hostname=hostname,
                x_position=float(device_location.get('x_position', 0.0)),
                y_position=float(device_location.get('y_position', 0.0)),
                layer=device_location.get('layer', 'unknown'),
                icon_type=device_location.get('icon_type', 'switch'),
                rack_unit=int(device_location.get('rack_unit', 0)),
                status_color=device_location.get('status_color', 'green')
            )

    def get_topology_summary(self) -> Dict[str, Any]:
        """
        Get summary of topology data in graph database.
        Returns: Topology statistics and connection counts.
        """
        query = """
        MATCH (d:Device)
        OPTIONAL MATCH ()-[lldp:CONNECTED_TO]->()
        OPTIONAL MATCH ()-[bgp:BGP_PEER_WITH]->()
        OPTIONAL MATCH (s:Site)
        OPTIONAL MATCH ()-[loc:LOCATED_AT]->()
        
        RETURN count(DISTINCT d) as devices,
               count(DISTINCT lldp) as physical_connections,
               count(DISTINCT bgp) as bgp_peers,
               count(DISTINCT s) as sites,
               count(DISTINCT loc) as device_locations
        """
        
        with self.schema.driver.session() as session:
            result = session.run(query)
            return dict(result.single())