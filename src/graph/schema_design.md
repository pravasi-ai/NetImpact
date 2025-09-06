# Temporal Graph Schema Design

## Overview
Network Configuration Impact Analysis Platform uses a temporal graph pattern with immutable identity nodes and versioned state nodes. This design enables configuration change tracking and impact analysis over time.

## Core Design Pattern: Temporal Versioning

### Identity vs State Node Separation
- **Identity Nodes**: Immutable entities representing network objects (devices, interfaces, etc.)
- **State Nodes**: Versioned configuration data linked to identity nodes
- **Relationships**: `:HAS_STATE` (identity→state) and `:LATEST` (identity→current state)

### Example Structure
```
(:Device {hostname: "core-sw-01"})
  ├── :HAS_STATE → (:DeviceState {version: 1, timestamp: "2024-01-01"})
  ├── :HAS_STATE → (:DeviceState {version: 2, timestamp: "2024-01-15"}) 
  └── :LATEST    → (:DeviceState {version: 2})  // Current state
```

## Node Types

### Core Network Entities

#### :Device (Identity)
- **Purpose**: Represents physical/virtual network devices
- **Properties**: 
  - `hostname` (string, unique): Device hostname
  - `device_id` (string, unique): UUID for device identity
  - `created_at` (datetime): Initial discovery time
- **Examples**: Switches, routers, firewalls

#### :DeviceState (Versioned State)
- **Purpose**: Device configuration and metadata at specific point in time
- **Properties**:
  - `version` (integer): Incremental version number
  - `timestamp` (datetime): When this state was created
  - `vendor` (string): cisco, arista, etc.
  - `os_type` (string): ios-xe, eos, etc.
  - `os_version` (string): 16.7.1, 4.21.0F, etc.
  - `platform` (string): Hardware platform model
  - `management_ip` (string): Management IP address
  - `serial_number` (string): Hardware serial
  - `config_hash` (string): Hash of configuration for change detection

#### :Interface (Identity)
- **Purpose**: Physical and logical network interfaces
- **Properties**:
  - `interface_id` (string, unique): UUID for interface identity
  - `name` (string): Interface name (GigabitEthernet1/0/1)
  - `device_hostname` (string): Parent device reference
  - `created_at` (datetime): Discovery time

#### :InterfaceState (Versioned State)
- **Purpose**: Interface configuration at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `description` (string): Interface description
  - `type` (string): routed, switched, management
  - `enabled` (boolean): Administrative status
  - `ip_address` (string): IP configuration
  - `speed` (string): Interface speed
  - `duplex` (string): Full/half duplex
  - `mtu` (integer): Maximum transmission unit

#### :VLAN (Identity)
- **Purpose**: Virtual LAN definitions
- **Properties**:
  - `vlan_id` (string, unique): Composite key: device_hostname:vlan_number
  - `vlan_number` (integer): VLAN ID (1-4094)
  - `device_hostname` (string): Owning device
  - `created_at` (datetime): Discovery time

#### :VLANState (Versioned State)
- **Purpose**: VLAN configuration at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `name` (string): VLAN name
  - `status` (string): active, suspend
  - `stp_priority` (integer): Spanning tree priority

#### :ACL (Identity)
- **Purpose**: Access Control List definitions
- **Properties**:
  - `acl_id` (string, unique): Composite key: device_hostname:acl_name
  - `name` (string): ACL name
  - `device_hostname` (string): Owning device
  - `created_at` (datetime): Discovery time

#### :ACLState (Versioned State)
- **Purpose**: ACL configuration and rules at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `type` (string): standard, extended, named
  - `rule_count` (integer): Number of rules
  - `rules_json` (string): JSON serialized rules

#### :IPNetwork (Identity)
- **Purpose**: IP subnets and network segments
- **Properties**:
  - `network_id` (string, unique): Network CIDR (192.168.1.0/24)
  - `network_address` (string): Network address
  - `prefix_length` (integer): Subnet mask length
  - `created_at` (datetime): Discovery time

#### :IPNetworkState (Versioned State)
- **Purpose**: Network segment information at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `description` (string): Network description
  - `vlan_number` (integer): Associated VLAN
  - `gateway_ip` (string): Default gateway

#### :BGPPeer (Identity)
- **Purpose**: BGP peering relationships
- **Properties**:
  - `peer_id` (string, unique): Composite key: local_hostname:peer_ip
  - `local_hostname` (string): Local device
  - `peer_ip` (string): Peer IP address
  - `created_at` (datetime): Discovery time

#### :BGPPeerState (Versioned State)
- **Purpose**: BGP peer configuration at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `peer_asn` (integer): Peer AS number
  - `session_state` (string): established, idle, active
  - `description` (string): Peer description

### Topology Visualization Nodes

#### :Site (Identity)
- **Purpose**: Physical locations and geographic hierarchy
- **Properties**:
  - `site_id` (string, unique): Site identifier
  - `name` (string): Site name (HQ, DC1, Branch-NY)
  - `type` (string): datacenter, branch, cloud, colo
  - `address` (string): Physical address
  - `coordinates` (string): Latitude,longitude for mapping
  - `created_at` (datetime): Discovery time

#### :DeviceLayout (Versioned State)
- **Purpose**: Device positioning and visual metadata for topology display
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `x_position` (float): X coordinate for layout
  - `y_position` (float): Y coordinate for layout
  - `layer` (string): core, distribution, access, wan
  - `icon_type` (string): switch, router, firewall, server
  - `rack_unit` (integer): Physical rack position
  - `status_color` (string): green, yellow, red for health

#### :OSPFNeighbor (Identity)
- **Purpose**: OSPF neighbor relationships for routing topology
- **Properties**:
  - `neighbor_id` (string, unique): Composite: device1:device2:area
  - `local_device` (string): Local device hostname
  - `remote_device` (string): Remote device hostname
  - `ospf_area` (string): OSPF area identifier
  - `created_at` (datetime): Discovery time

#### :OSPFNeighborState (Versioned State)
- **Purpose**: OSPF neighbor state at specific point in time
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `neighbor_state` (string): full, 2-way, down, init
  - `cost` (integer): OSPF link cost
  - `hello_timer` (integer): Hello interval
  - `dead_timer` (integer): Dead interval

#### :LinkAggregation (Identity)
- **Purpose**: Port-channel/LAG grouping for visualization
- **Properties**:
  - `lag_id` (string, unique): Composite: device:lag_name
  - `name` (string): PortChannel1, ae0, etc.
  - `device_hostname` (string): Owning device
  - `created_at` (datetime): Discovery time

#### :LinkAggregationState (Versioned State)
- **Purpose**: LAG configuration and member interfaces
- **Properties**:
  - `version` (integer): Version number
  - `timestamp` (datetime): State timestamp
  - `protocol` (string): lacp, static
  - `member_count` (integer): Number of member interfaces
  - `active_members` (integer): Currently active members
  - `aggregate_bandwidth` (string): Total bandwidth

## Relationship Types

### Structural Relationships

#### :HAS_INTERFACE
- **Direction**: (:Device) → (:Interface)
- **Purpose**: Device owns interface
- **Properties**: None (structural only)

#### :MEMBER_OF_VLAN
- **Direction**: (:Interface) → (:VLAN)  
- **Purpose**: Interface is member of VLAN
- **Properties**:
  - `membership_type` (string): access, trunk
  - `native_vlan` (boolean): For trunk interfaces

#### :APPLIED_ACL
- **Direction**: (:Interface) → (:ACL)
- **Purpose**: ACL applied to interface
- **Properties**:
  - `direction` (string): in, out
  - `position` (integer): Application order

#### :IN_NETWORK
- **Direction**: (:Interface) → (:IPNetwork)
- **Purpose**: Interface belongs to IP network
- **Properties**: None

#### :CONNECTED_TO
- **Direction**: (:Interface) ↔ (:Interface)
- **Purpose**: Physical connectivity between interfaces
- **Properties**:
  - `connection_type` (string): copper, fiber, wireless
  - `discovered_via` (string): lldp, cdp, manual
  - `confirmed_at` (datetime): Last confirmation

#### :BGP_PEER_WITH
- **Direction**: (:Device) → (:BGPPeer) ← (:Device)
- **Purpose**: BGP peering relationship
- **Properties**:
  - `local_ip` (string): Local BGP address
  - `peer_ip` (string): Remote BGP address

### Topology Visualization Relationships

#### :LOCATED_AT
- **Direction**: (:Device) → (:Site)
- **Purpose**: Device physical location
- **Properties**:
  - `installation_date` (datetime): When device was installed
  - `rack_name` (string): Specific rack identifier

#### :OSPF_NEIGHBOR_WITH
- **Direction**: (:Device) → (:OSPFNeighbor) ← (:Device)
- **Purpose**: OSPF adjacency for routing topology visualization
- **Properties**:
  - `local_interface` (string): Local interface name
  - `remote_interface` (string): Remote interface name
  - `area` (string): OSPF area

#### :MEMBER_OF_LAG
- **Direction**: (:Interface) → (:LinkAggregation)
- **Purpose**: Interface is member of link aggregation group
- **Properties**:
  - `member_priority` (integer): LACP priority
  - `active` (boolean): Currently active in bundle

#### :SPANS_SITES
- **Direction**: (:Interface) → (:Site), (:Interface) → (:Site)
- **Purpose**: WAN links that span multiple sites
- **Properties**:
  - `circuit_id` (string): Provider circuit identifier
  - `bandwidth` (string): Link capacity
  - `provider` (string): Service provider name

### Temporal Relationships

#### :HAS_STATE
- **Direction**: (Identity) → (State)
- **Purpose**: Links identity nodes to all their state versions
- **Properties**: None

#### :LATEST
- **Direction**: (Identity) → (State)
- **Purpose**: Points to current/latest state version
- **Properties**: None

#### :PREVIOUS_STATE
- **Direction**: (State) → (State)
- **Purpose**: Links state versions in chronological order
- **Properties**: None

## Schema Constraints and Indexes

### Unique Constraints
```cypher
// Identity node uniqueness
CREATE CONSTRAINT device_hostname_unique FOR (d:Device) REQUIRE d.hostname IS UNIQUE;
CREATE CONSTRAINT interface_id_unique FOR (i:Interface) REQUIRE i.interface_id IS UNIQUE;
CREATE CONSTRAINT vlan_id_unique FOR (v:VLAN) REQUIRE v.vlan_id IS UNIQUE;
CREATE CONSTRAINT acl_id_unique FOR (a:ACL) REQUIRE a.acl_id IS UNIQUE;
CREATE CONSTRAINT network_id_unique FOR (n:IPNetwork) REQUIRE n.network_id IS UNIQUE;
CREATE CONSTRAINT bgppeer_id_unique FOR (b:BGPPeer) REQUIRE b.peer_id IS UNIQUE;
```

### Performance Indexes
```cypher
// Query performance indexes
CREATE INDEX device_hostname_idx FOR (d:Device) ON (d.hostname);
CREATE INDEX interface_device_idx FOR (i:Interface) ON (i.device_hostname);
CREATE INDEX state_timestamp_idx FOR (s:DeviceState) ON (s.timestamp);
CREATE INDEX state_version_idx FOR (s:DeviceState) ON (s.version);
```

## Impact Analysis Queries

### Find Dependencies of Interface Change
```cypher
// Given interface change, find all affected components
MATCH (device:Device {hostname: $hostname})
      -[:HAS_INTERFACE]->
      (interface:Interface {name: $interface_name})
      -[:LATEST]->
      (if_state:InterfaceState)
      
// Find VLAN dependencies
OPTIONAL MATCH (interface)-[:MEMBER_OF_VLAN]->(vlan:VLAN)
                         -[:HAS_INTERFACE]<-
                         (other_device:Device)
                         -[:HAS_INTERFACE]->
                         (other_interface:Interface)
                         -[:MEMBER_OF_VLAN]->
                         (vlan)

// Find ACL dependencies  
OPTIONAL MATCH (interface)-[:APPLIED_ACL]->(acl:ACL)
                         <-[:APPLIED_ACL]-
                         (other_interface2:Interface)

// Find physical connectivity
OPTIONAL MATCH (interface)-[:CONNECTED_TO]-(connected_interface:Interface)

RETURN device, interface, vlan, acl, 
       other_interface, other_interface2, connected_interface
```

## Topology Visualization Queries

### Get Network Topology for Visualization
```cypher
// Get all devices with their locations and layout info
MATCH (device:Device)-[:LATEST]->(device_state:DeviceState)
OPTIONAL MATCH (device)-[:LATEST]->(layout:DeviceLayout)
OPTIONAL MATCH (device)-[:LOCATED_AT]->(site:Site)

// Get physical connections
OPTIONAL MATCH (device)-[:HAS_INTERFACE]->(interface:Interface)
                        -[conn:CONNECTED_TO]->
                        (remote_interface:Interface)
                        <-[:HAS_INTERFACE]-
                        (remote_device:Device)

// Get OSPF topology
OPTIONAL MATCH (device)-[ospf:OSPF_NEIGHBOR_WITH]->(neighbor:OSPFNeighbor)
                       <-[:OSPF_NEIGHBOR_WITH]-
                       (ospf_peer:Device)

RETURN device.hostname, device_state, layout, site,
       collect(DISTINCT {
         remote_device: remote_device.hostname,
         local_interface: interface.name,
         remote_interface: remote_interface.name,
         connection_type: conn.connection_type,
         relationship_type: 'physical'
       }) as physical_connections,
       collect(DISTINCT {
         ospf_peer: ospf_peer.hostname,
         area: ospf.area,
         local_interface: ospf.local_interface,
         remote_interface: ospf.remote_interface,
         relationship_type: 'ospf'
       }) as ospf_neighbors
```

### Get Site-based Topology View
```cypher
// Get devices grouped by site for hierarchical visualization
MATCH (site:Site)<-[:LOCATED_AT]-(device:Device)
      -[:LATEST]->(device_state:DeviceState)
OPTIONAL MATCH (device)-[:LATEST]->(layout:DeviceLayout)

// Get inter-site connections
OPTIONAL MATCH (device)-[:HAS_INTERFACE]->(interface:Interface)
                        -[:SPANS_SITES]->
                        (remote_site:Site)

RETURN site.name, site.type, site.coordinates,
       collect({
         hostname: device.hostname,
         vendor: device_state.vendor,
         layer: layout.layer,
         icon_type: layout.icon_type,
         status_color: layout.status_color,
         x_position: layout.x_position,
         y_position: layout.y_position
       }) as devices,
       collect(DISTINCT remote_site.name) as connected_sites
```

### Get Layer-based Network View
```cypher
// Get devices organized by network layer for structured topology
MATCH (device:Device)-[:LATEST]->(device_state:DeviceState)
OPTIONAL MATCH (device)-[:LATEST]->(layout:DeviceLayout)

// Get connections between layers
MATCH (device)-[:HAS_INTERFACE]->(interface:Interface)
              -[:CONNECTED_TO]->
              (remote_interface:Interface)
              <-[:HAS_INTERFACE]-
              (remote_device:Device)
              -[:LATEST]->
              (remote_layout:DeviceLayout)

RETURN layout.layer,
       collect(DISTINCT {
         hostname: device.hostname,
         vendor: device_state.vendor,
         platform: device_state.platform,
         icon_type: layout.icon_type,
         status_color: layout.status_color
       }) as layer_devices,
       collect(DISTINCT {
         from_layer: layout.layer,
         to_layer: remote_layout.layer,
         from_device: device.hostname,
         to_device: remote_device.hostname
       }) as cross_layer_connections

ORDER BY 
  CASE layout.layer 
    WHEN 'core' THEN 1
    WHEN 'distribution' THEN 2  
    WHEN 'access' THEN 3
    WHEN 'wan' THEN 4
    ELSE 5
  END
```

This enhanced temporal graph schema now provides comprehensive support for network topology visualization including physical layout, site hierarchy, routing relationships, and visual metadata for rendering network diagrams.