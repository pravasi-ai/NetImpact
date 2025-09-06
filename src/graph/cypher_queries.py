"""
Parameterized Cypher queries for idempotent graph operations.
Handles all MERGE statements for nodes, relationships, and state management.
"""

from typing import Dict, Any, List


class CypherQueries:
    """
    Collection of parameterized Cypher queries for temporal graph operations.
    All queries use MERGE for idempotent operations to prevent duplicates.
    """

    # Device Operations
    CREATE_ACL_IDENTITY = """
    MATCH (d:Device {hostname: $hostname})
    MERGE (a:ACL {acl_id: $acl_id})
    ON CREATE SET a.name = $name,
                 a.device_hostname = $hostname,
                 a.created_at = datetime()
    RETURN a.acl_id as acl_id
    """

    CREATE_ACL_STATE = """
    MATCH (a:ACL {acl_id: $acl_id})
    
    CREATE (as:ACLState {
        version: $version,
        timestamp: datetime(),
        type: $type,
        rule_count: $rule_count,
        rules_json: $rules_json
    })
    
    CREATE (a)-[:HAS_STATE]->(as)
    
    WITH a, as
    OPTIONAL MATCH (a)-[old_latest:LATEST]->(old_state:ACLState)
    DELETE old_latest
    CREATE (a)-[:LATEST]->(as)
    
    WITH a, as, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(as)
    
    RETURN as.version as version
    """

    CREATE_INTERFACE_STATE = """
    MATCH (i:Interface {interface_id: $interface_id})
    
    CREATE (is:InterfaceState {
        version: $version,
        timestamp: datetime(),
        description: $description,
        type: $type,
        enabled: $enabled,
        ip_address: $ip_address,
        speed: $speed,
        duplex: $duplex,
        mtu: $mtu
    })
    
    CREATE (i)-[:HAS_STATE]->(is)
    
    WITH i, is
    OPTIONAL MATCH (i)-[old_latest:LATEST]->(old_state:InterfaceState)
    DELETE old_latest
    CREATE (i)-[:LATEST]->(is)
    
    WITH i, is, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(is)
    
    RETURN is.version as version
    """

    CREATE_VLAN_STATE = """
    MATCH (v:VLAN {vlan_id: $vlan_id})
    
    CREATE (vs:VLANState {
        version: $version,
        timestamp: datetime(),
        name: $name,
        status: $status,
        stp_priority: $stp_priority
    })
    
    CREATE (v)-[:HAS_STATE]->(vs)
    
    WITH v, vs
    OPTIONAL MATCH (v)-[old_latest:LATEST]->(old_state:VLANState)
    DELETE old_latest
    CREATE (v)-[:LATEST]->(vs)
    
    WITH v, vs, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(vs)
    
    RETURN vs.version as version
    """

    # Network and IP Operations
    CREATE_IPNETWORK_IDENTITY = """
    MERGE (n:IPNetwork {network_id: $network_id})
    ON CREATE SET n.network_address = $network_address,
                 n.prefix_length = $prefix_length,
                 n.created_at = datetime()
    RETURN n.network_id as network_id
    """

    CREATE_IPNETWORK_STATE = """
    MATCH (n:IPNetwork {network_id: $network_id})
    
    CREATE (ns:IPNetworkState {
        version: $version,
        timestamp: datetime(),
        description: $description,
        vlan_number: $vlan_number,
        gateway_ip: $gateway_ip
    })
    
    CREATE (n)-[:HAS_STATE]->(ns)
    
    WITH n, ns
    OPTIONAL MATCH (n)-[old_latest:LATEST]->(old_state:IPNetworkState)
    DELETE old_latest
    CREATE (n)-[:LATEST]->(ns)
    
    WITH n, ns, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(ns)
    
    RETURN ns.version as version
    """

    # Relationship Operations
    CREATE_VLAN_MEMBERSHIP = """
    MATCH (i:Interface {interface_id: $interface_id})
    MATCH (v:VLAN {vlan_id: $vlan_id})
    
    MERGE (i)-[r:MEMBER_OF_VLAN]->(v)
    SET r.membership_type = $membership_type,
        r.native_vlan = $native_vlan
    
    RETURN r
    """

    CREATE_ACL_APPLICATION = """
    MATCH (i:Interface {interface_id: $interface_id})
    MATCH (a:ACL {acl_id: $acl_id})
    
    MERGE (i)-[r:APPLIED_ACL]->(a)
    SET r.direction = $direction,
        r.position = $position
    
    RETURN r
    """

    CREATE_NETWORK_MEMBERSHIP = """
    MATCH (i:Interface {interface_id: $interface_id})
    MATCH (n:IPNetwork {network_id: $network_id})
    
    MERGE (i)-[r:IN_NETWORK]->(n)
    
    RETURN r
    """

    # BGP Operations
    CREATE_BGP_PEER_IDENTITY = """
    MERGE (b:BGPPeer {peer_id: $peer_id})
    ON CREATE SET b.local_hostname = $local_hostname,
                 b.peer_ip = $peer_ip,
                 b.created_at = datetime()
    RETURN b.peer_id as peer_id
    """

    CREATE_BGP_PEER_STATE = """
    MATCH (b:BGPPeer {peer_id: $peer_id})
    
    CREATE (bs:BGPPeerState {
        version: $version,
        timestamp: datetime(),
        peer_asn: $peer_asn,
        session_state: $session_state,
        description: $description
    })
    
    CREATE (b)-[:HAS_STATE]->(bs)
    
    WITH b, bs
    OPTIONAL MATCH (b)-[old_latest:LATEST]->(old_state:BGPPeerState)
    DELETE old_latest
    CREATE (b)-[:LATEST]->(bs)
    
    WITH b, bs, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(bs)
    
    RETURN bs.version as version
    """

    CREATE_BGP_PEERING = """
    MATCH (d1:Device {hostname: $local_hostname})
    MATCH (d2:Device {hostname: $remote_hostname})
    MATCH (b:BGPPeer {peer_id: $peer_id})
    
    MERGE (d1)-[r1:BGP_PEER_WITH]->(b)
    SET r1.local_ip = $local_ip,
        r1.peer_ip = $peer_ip
    
    MERGE (b)<-[r2:BGP_PEER_WITH]-(d2)
    SET r2.local_ip = $peer_ip,
        r2.peer_ip = $local_ip
    
    RETURN r1, r2
    """

    # Topology Visualization Operations
    CREATE_SITE_IDENTITY = """
    MERGE (s:Site {site_id: $site_id})
    ON CREATE SET s.name = $name,
                 s.type = $type,
                 s.address = $address,
                 s.coordinates = $coordinates,
                 s.created_at = datetime()
    RETURN s.site_id as site_id
    """

    CREATE_DEVICE_LAYOUT = """
    MATCH (d:Device {hostname: $hostname})
    
    CREATE (dl:DeviceLayout {
        version: $version,
        timestamp: datetime(),
        x_position: $x_position,
        y_position: $y_position,
        layer: $layer,
        icon_type: $icon_type,
        rack_unit: $rack_unit,
        status_color: $status_color
    })
    
    CREATE (d)-[:HAS_STATE]->(dl)
    
    WITH d, dl
    OPTIONAL MATCH (d)-[old_latest:LATEST]->(old_layout:DeviceLayout)
    DELETE old_latest
    CREATE (d)-[:LATEST]->(dl)
    
    WITH d, dl, old_layout
    WHERE old_layout IS NOT NULL
    CREATE (old_layout)-[:PREVIOUS_STATE]->(dl)
    
    RETURN dl.version as version
    """

    CREATE_DEVICE_LOCATION = """
    MATCH (d:Device {hostname: $hostname})
    MATCH (s:Site {site_id: $site_id})
    
    MERGE (d)-[r:LOCATED_AT]->(s)
    SET r.installation_date = $installation_date,
        r.rack_name = $rack_name
    
    RETURN r
    """

    CREATE_OSPF_NEIGHBOR_IDENTITY = """
    MERGE (o:OSPFNeighbor {neighbor_id: $neighbor_id})
    ON CREATE SET o.local_device = $local_device,
                 o.remote_device = $remote_device,
                 o.ospf_area = $ospf_area,
                 o.created_at = datetime()
    RETURN o.neighbor_id as neighbor_id
    """

    CREATE_OSPF_NEIGHBOR_STATE = """
    MATCH (o:OSPFNeighbor {neighbor_id: $neighbor_id})
    
    CREATE (os:OSPFNeighborState {
        version: $version,
        timestamp: datetime(),
        neighbor_state: $neighbor_state,
        cost: $cost,
        hello_timer: $hello_timer,
        dead_timer: $dead_timer
    })
    
    CREATE (o)-[:HAS_STATE]->(os)
    
    WITH o, os
    OPTIONAL MATCH (o)-[old_latest:LATEST]->(old_state:OSPFNeighborState)
    DELETE old_latest
    CREATE (o)-[:LATEST]->(os)
    
    WITH o, os, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(os)
    
    RETURN os.version as version
    """

    CREATE_OSPF_PEERING = """
    MATCH (d1:Device {hostname: $local_hostname})
    MATCH (d2:Device {hostname: $remote_hostname})
    MATCH (o:OSPFNeighbor {neighbor_id: $neighbor_id})
    
    MERGE (d1)-[r1:OSPF_NEIGHBOR_WITH]->(o)
    SET r1.local_interface = $local_interface,
        r1.remote_interface = $remote_interface,
        r1.area = $area
    
    MERGE (o)<-[r2:OSPF_NEIGHBOR_WITH]-(d2)
    SET r2.local_interface = $remote_interface,
        r2.remote_interface = $local_interface,
        r2.area = $area
    
    RETURN r1, r2
    """

    # Link Aggregation Operations
    CREATE_LAG_IDENTITY = """
    MATCH (d:Device {hostname: $hostname})
    MERGE (l:LinkAggregation {lag_id: $lag_id})
    ON CREATE SET l.name = $name,
                 l.device_hostname = $hostname,
                 l.created_at = datetime()
    RETURN l.lag_id as lag_id
    """

    CREATE_LAG_STATE = """
    MATCH (l:LinkAggregation {lag_id: $lag_id})
    
    CREATE (ls:LinkAggregationState {
        version: $version,
        timestamp: datetime(),
        protocol: $protocol,
        member_count: $member_count,
        active_members: $active_members,
        aggregate_bandwidth: $aggregate_bandwidth
    })
    
    CREATE (l)-[:HAS_STATE]->(ls)
    
    WITH l, ls
    OPTIONAL MATCH (l)-[old_latest:LATEST]->(old_state:LinkAggregationState)
    DELETE old_latest
    CREATE (l)-[:LATEST]->(ls)
    
    WITH l, ls, old_state
    WHERE old_state IS NOT NULL
    CREATE (old_state)-[:PREVIOUS_STATE]->(ls)
    
    RETURN ls.version as version
    """

    CREATE_LAG_MEMBERSHIP = """
    MATCH (i:Interface {interface_id: $interface_id})
    MATCH (l:LinkAggregation {lag_id: $lag_id})
    
    MERGE (i)-[r:MEMBER_OF_LAG]->(l)
    SET r.member_priority = $member_priority,
        r.active = $active
    
    RETURN r
    """

    # Utility Queries
    GET_NEXT_VERSION = """
    MATCH (identity)-[:HAS_STATE]->(state)
    WHERE identity.{identity_property} = $identity_value
    RETURN COALESCE(MAX(state.version), 0) + 1 as next_version
    """

    GET_DEVICE_SUMMARY = """
    MATCH (d:Device {hostname: $hostname})
    OPTIONAL MATCH (d)-[:LATEST]->(ds:DeviceState)
    OPTIONAL MATCH (d)-[:HAS_INTERFACE]->(i:Interface)
    OPTIONAL MATCH (d)-[:HAS_INTERFACE]->(i)-[:MEMBER_OF_VLAN]->(v:VLAN)
    
    RETURN d.hostname,
           ds.vendor, ds.os_type, ds.os_version,
           count(DISTINCT i) as interface_count,
           count(DISTINCT v) as vlan_count
    """

    # Topology Queries for Visualization
    GET_NETWORK_TOPOLOGY = """
    MATCH (device:Device)-[:LATEST]->(device_state:DeviceState)
    OPTIONAL MATCH (device)-[:LATEST]->(layout:DeviceLayout)
    OPTIONAL MATCH (device)-[:LOCATED_AT]->(site:Site)
    
    OPTIONAL MATCH (device)-[:HAS_INTERFACE]->(interface:Interface)
                            -[conn:CONNECTED_TO]->
                            (remote_interface:Interface)
                            <-[:HAS_INTERFACE]-
                            (remote_device:Device)
    
    RETURN device.hostname, device_state, layout, site,
           collect(DISTINCT {
             remote_device: remote_device.hostname,
             local_interface: interface.name,
             remote_interface: remote_interface.name,
             connection_type: conn.connection_type,
             relationship_type: 'physical'
           }) as connections
    """

    # Batch Operations for Performance
    BATCH_CREATE_INTERFACES = """
    UNWIND $interfaces as interface_data
    MATCH (d:Device {hostname: interface_data.hostname})
    MERGE (i:Interface {interface_id: interface_data.interface_id})
    ON CREATE SET i.name = interface_data.name,
                 i.device_hostname = interface_data.hostname,
                 i.created_at = datetime()
    
    MERGE (d)-[:HAS_INTERFACE]->(i)
    
    RETURN count(i) as interfaces_created
    """

    BATCH_CREATE_VLANS = """
    UNWIND $vlans as vlan_data
    MATCH (d:Device {hostname: vlan_data.hostname})
    MERGE (v:VLAN {vlan_id: vlan_data.vlan_id})
    ON CREATE SET v.vlan_number = vlan_data.vlan_number,
                 v.device_hostname = vlan_data.hostname,
                 v.created_at = datetime()
    
    RETURN count(v) as vlans_created
    """