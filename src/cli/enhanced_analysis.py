"""
Enhanced Multi-Device Configuration Analysis using Neo4j Graph Database.
Combines YANG schema analysis with graph-based cross-device dependency tracking.
"""

import click
import os
from typing import Dict, Any, List, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from dotenv import load_dotenv
from neo4j import GraphDatabase

console = Console()

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7688')
NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j') 
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'netopo123')


def get_neo4j_driver():
    """Get Neo4j driver with error handling."""
    try:
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    except Exception as e:
        console.print(f"[red]❌ Failed to connect to Neo4j: {e}[/red]")
        return None


def analyze_cross_device_impact(device_hostname: str, change_type: str = "bgp") -> Dict[str, Any]:
    """
    Analyze cross-device impact using graph database traversal.
    Args: device_hostname and change_type to focus analysis.
    Returns: Cross-device impact analysis results.
    """
    driver = get_neo4j_driver()
    if not driver:
        return {}
    
    try:
        with driver.session() as session:
            if change_type == "bgp":
                return _analyze_bgp_cross_device_impact(session, device_hostname)
            elif change_type == "interface":
                return _analyze_interface_cross_device_impact(session, device_hostname)
            elif change_type == "vlan":
                return _analyze_vlan_cross_device_impact(session, device_hostname)
            else:
                return _analyze_generic_cross_device_impact(session, device_hostname)
                
    except Exception as e:
        console.print(f"[red]❌ Cross-device analysis failed: {e}[/red]")
        return {}
    finally:
        driver.close()


def _analyze_bgp_cross_device_impact(session, device_hostname: str) -> Dict[str, Any]:
    """Analyze BGP changes across the network topology."""
    
    # Find BGP peers of this device
    bgp_peers_query = """
        MATCH (d:Device {hostname: $hostname})-[:BGP_PEER_WITH]->(p:BGPPeer)
        OPTIONAL MATCH (p)-[:LATEST]->(ps:BGPPeerState)
        OPTIONAL MATCH (peer_device:Device)-[:BGP_PEER_WITH]->(p)
        WHERE peer_device.hostname <> $hostname
        RETURN p.peer_ip as peer_ip,
               ps.peer_asn as peer_asn,
               peer_device.hostname as peer_device,
               count(*) as relationship_count
        ORDER BY relationship_count DESC
        LIMIT 10
    """
    
    result = session.run(bgp_peers_query, hostname=device_hostname)
    bgp_peers = []
    
    for record in result:
        bgp_peers.append({
            'peer_ip': record['peer_ip'],
            'peer_asn': record['peer_asn'],
            'peer_device': record['peer_device'],
            'relationship_count': record['relationship_count']
        })
    
    # Find devices in same AS
    same_as_query = """
        MATCH (d:Device {hostname: $hostname})-[:HAS_BGP_INSTANCE]->(b:BGPInstance)
        MATCH (other_device:Device)-[:HAS_BGP_INSTANCE]->(other_bgp:BGPInstance)
        WHERE other_device.hostname <> $hostname 
        AND b.as_number = other_bgp.as_number
        RETURN other_device.hostname as device,
               other_bgp.as_number as as_number,
               other_bgp.router_id as router_id
    """
    
    result = session.run(same_as_query, hostname=device_hostname)
    same_as_devices = []
    
    for record in result:
        same_as_devices.append({
            'device': record['device'],
            'as_number': record['as_number'],
            'router_id': record['router_id']
        })
    
    # Find physically connected devices
    physical_connections_query = """
        MATCH (d:Device {hostname: $hostname})-[:HAS_INTERFACE]->(i:Interface)
        MATCH (i)-[:CONNECTED_TO]-(remote_i:Interface)
        MATCH (remote_d:Device)-[:HAS_INTERFACE]->(remote_i)
        WHERE remote_d.hostname <> $hostname
        RETURN remote_d.hostname as connected_device,
               i.name as local_interface,
               remote_i.name as remote_interface
        ORDER BY connected_device
    """
    
    result = session.run(physical_connections_query, hostname=device_hostname)
    physical_connections = []
    
    for record in result:
        physical_connections.append({
            'device': record['connected_device'],
            'local_interface': record['local_interface'],
            'remote_interface': record['remote_interface']
        })
    
    return {
        'bgp_peers': bgp_peers,
        'same_as_devices': same_as_devices,
        'physical_connections': physical_connections,
        'analysis_type': 'bgp_cross_device'
    }


def _analyze_interface_cross_device_impact(session, device_hostname: str) -> Dict[str, Any]:
    """Analyze interface changes and their cross-device impacts."""
    
    # Find interfaces with physical connections
    connected_interfaces_query = """
        MATCH (d:Device {hostname: $hostname})-[:HAS_INTERFACE]->(i:Interface)
        MATCH (i)-[:CONNECTED_TO]-(remote_i:Interface)
        MATCH (remote_d:Device)-[:HAS_INTERFACE]->(remote_i)
        OPTIONAL MATCH (i)-[:MEMBER_OF_VLAN]->(v:VLAN)
        RETURN i.name as interface,
               remote_d.hostname as connected_device,
               remote_i.name as remote_interface,
               collect(v.vlan_number) as vlans
        ORDER BY interface
    """
    
    result = session.run(connected_interfaces_query, hostname=device_hostname)
    connected_interfaces = []
    
    for record in result:
        connected_interfaces.append({
            'interface': record['interface'],
            'connected_device': record['connected_device'],
            'remote_interface': record['remote_interface'],
            'vlans': [vlan for vlan in record['vlans'] if vlan is not None]
        })
    
    return {
        'connected_interfaces': connected_interfaces,
        'analysis_type': 'interface_cross_device'
    }


def _analyze_vlan_cross_device_impact(session, device_hostname: str) -> Dict[str, Any]:
    """Analyze VLAN changes and their propagation across devices."""
    
    # Find VLANs on this device
    device_vlans_query = """
        MATCH (v:VLAN {device_hostname: $hostname})
        RETURN v.vlan_number as vlan_id
        ORDER BY vlan_id
    """
    
    result = session.run(device_vlans_query, hostname=device_hostname)
    device_vlans = [record['vlan_id'] for record in result]
    
    # Find same VLANs on other devices (VLAN propagation)
    vlan_propagation = {}
    for vlan_id in device_vlans:
        propagation_query = """
            MATCH (v:VLAN {vlan_number: $vlan_id})
            WHERE v.device_hostname <> $hostname
            RETURN v.device_hostname as device,
                   v.vlan_number as vlan_id
        """
        
        result = session.run(propagation_query, vlan_id=vlan_id, hostname=device_hostname)
        other_devices = [record['device'] for record in result]
        
        if other_devices:
            vlan_propagation[vlan_id] = other_devices
    
    return {
        'device_vlans': device_vlans,
        'vlan_propagation': vlan_propagation,
        'analysis_type': 'vlan_cross_device'
    }


def _analyze_generic_cross_device_impact(session, device_hostname: str) -> Dict[str, Any]:
    """Generic cross-device relationship analysis."""
    
    # Find all relationships to other devices
    relationships_query = """
        MATCH (d:Device {hostname: $hostname})
        MATCH (d)-[r]->(n)
        MATCH (other_d:Device)-[other_r]->(n)
        WHERE other_d.hostname <> $hostname
        RETURN type(r) as relationship_type,
               other_d.hostname as other_device,
               labels(n) as shared_resource_labels,
               count(*) as shared_count
        ORDER BY shared_count DESC
        LIMIT 10
    """
    
    result = session.run(relationships_query, hostname=device_hostname)
    shared_resources = []
    
    for record in result:
        shared_resources.append({
            'relationship_type': record['relationship_type'],
            'other_device': record['other_device'],
            'shared_resource_type': ':'.join(record['shared_resource_labels']),
            'shared_count': record['shared_count']
        })
    
    return {
        'shared_resources': shared_resources,
        'analysis_type': 'generic_cross_device'
    }


def display_cross_device_analysis(hostname: str, analysis: Dict[str, Any]):
    """Display cross-device analysis results in formatted tables."""
    
    analysis_type = analysis.get('analysis_type', 'generic')
    
    console.print(f"\n[bold blue]🌐 Cross-Device Impact Analysis: {hostname}[/bold blue]")
    console.print(f"[dim]Analysis Type: {analysis_type}[/dim]")
    
    if analysis_type == 'bgp_cross_device':
        _display_bgp_cross_device_analysis(analysis)
    elif analysis_type == 'interface_cross_device':
        _display_interface_cross_device_analysis(analysis)
    elif analysis_type == 'vlan_cross_device':
        _display_vlan_cross_device_analysis(analysis)
    else:
        _display_generic_cross_device_analysis(analysis)


def _display_bgp_cross_device_analysis(analysis: Dict[str, Any]):
    """Display BGP-specific cross-device analysis."""
    
    bgp_peers = analysis.get('bgp_peers', [])
    same_as_devices = analysis.get('same_as_devices', [])
    physical_connections = analysis.get('physical_connections', [])
    
    # BGP Peers Impact
    if bgp_peers:
        console.print(f"\n[bold cyan]🔄 BGP Peering Impact[/bold cyan]")
        bgp_table = Table()
        bgp_table.add_column("Peer IP", style="cyan")
        bgp_table.add_column("Peer ASN", style="magenta")
        bgp_table.add_column("Peer Device", style="green")
        bgp_table.add_column("Impact", style="red")
        
        for peer in bgp_peers:
            impact = "Session Reset Required" if peer['peer_device'] else "External Peer"
            bgp_table.add_row(
                peer['peer_ip'] or 'unknown',
                str(peer['peer_asn']) if peer['peer_asn'] else 'unknown',
                peer['peer_device'] or 'external',
                impact
            )
        
        console.print(bgp_table)
    
    # Same AS Devices Impact
    if same_as_devices:
        console.print(f"\n[bold yellow]🏢 Same AS Devices (iBGP Impact)[/bold yellow]")
        as_table = Table()
        as_table.add_column("Device", style="green")
        as_table.add_column("AS Number", style="cyan")
        as_table.add_column("Router ID", style="blue")
        as_table.add_column("Impact", style="red")
        
        for device in same_as_devices:
            as_table.add_row(
                device['device'],
                str(device['as_number']),
                device['router_id'] or 'unknown',
                "iBGP Reconfiguration Required"
            )
        
        console.print(as_table)
    
    # Physical Connections
    if physical_connections:
        console.print(f"\n[bold green]🔗 Physical Connectivity Impact[/bold green]")
        conn_table = Table()
        conn_table.add_column("Connected Device", style="green")
        conn_table.add_column("Local Interface", style="cyan")
        conn_table.add_column("Remote Interface", style="cyan")
        conn_table.add_column("Impact", style="red")
        
        for conn in physical_connections:
            conn_table.add_row(
                conn['device'],
                conn['local_interface'],
                conn['remote_interface'],
                "Routing Update via IGP"
            )
        
        console.print(conn_table)


def _display_interface_cross_device_analysis(analysis: Dict[str, Any]):
    """Display interface-specific cross-device analysis."""
    
    connected_interfaces = analysis.get('connected_interfaces', [])
    
    if connected_interfaces:
        console.print(f"\n[bold green]🔗 Connected Interface Impact[/bold green]")
        intf_table = Table()
        intf_table.add_column("Local Interface", style="cyan")
        intf_table.add_column("Connected Device", style="green")
        intf_table.add_column("Remote Interface", style="cyan")
        intf_table.add_column("VLANs", style="yellow")
        intf_table.add_column("Impact", style="red")
        
        for intf in connected_interfaces:
            vlans_str = ', '.join(map(str, intf['vlans'])) if intf['vlans'] else 'none'
            intf_table.add_row(
                intf['interface'],
                intf['connected_device'],
                intf['remote_interface'],
                vlans_str,
                "Link State Change"
            )
        
        console.print(intf_table)


def _display_vlan_cross_device_analysis(analysis: Dict[str, Any]):
    """Display VLAN-specific cross-device analysis."""
    
    device_vlans = analysis.get('device_vlans', [])
    vlan_propagation = analysis.get('vlan_propagation', {})
    
    if device_vlans:
        console.print(f"\n[bold yellow]🏷️ VLAN Cross-Device Propagation[/bold yellow]")
        vlan_table = Table()
        vlan_table.add_column("VLAN ID", style="yellow")
        vlan_table.add_column("Also Present On", style="green")
        vlan_table.add_column("Impact", style="red")
        
        for vlan_id in device_vlans:
            other_devices = vlan_propagation.get(vlan_id, [])
            devices_str = ', '.join(other_devices) if other_devices else 'none'
            impact = "VLAN Propagation Impact" if other_devices else "Local VLAN Only"
            
            vlan_table.add_row(
                str(vlan_id),
                devices_str,
                impact
            )
        
        console.print(vlan_table)


def _display_generic_cross_device_analysis(analysis: Dict[str, Any]):
    """Display generic cross-device analysis."""
    
    shared_resources = analysis.get('shared_resources', [])
    
    if shared_resources:
        console.print(f"\n[bold magenta]🔄 Shared Resource Impact[/bold magenta]")
        resource_table = Table()
        resource_table.add_column("Relationship Type", style="cyan")
        resource_table.add_column("Other Device", style="green")
        resource_table.add_column("Shared Resource", style="yellow")
        resource_table.add_column("Count", style="magenta")
        
        for resource in shared_resources:
            resource_table.add_row(
                resource['relationship_type'],
                resource['other_device'],
                resource['shared_resource_type'],
                str(resource['shared_count'])
            )
        
        console.print(resource_table)


@click.command('graph')
@click.argument('hostname')
@click.option('--change-type', '-t', 
              type=click.Choice(['bgp', 'interface', 'vlan', 'auto']),
              default='auto',
              help='Type of change to analyze for cross-device impact')
def analyze_graph(hostname: str, change_type: str):
    """Analyze configuration changes with cross-device graph-based impact analysis."""
    
    console.print(f"[bold blue]🌐 Multi-Device Graph Analysis: {hostname}[/bold blue]")
    console.print(f"[dim]Change Type: {change_type}[/dim]")
    
    # Verify device exists in graph
    driver = get_neo4j_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            result = session.run("MATCH (d:Device {hostname: $hostname}) RETURN d.hostname", 
                               hostname=hostname)
            if not result.single():
                console.print(f"[red]❌ Device '{hostname}' not found in graph database[/red]")
                console.print("[yellow]   Run 'ingest all' to populate graph data first[/yellow]")
                return
    except Exception as e:
        console.print(f"[red]❌ Failed to verify device: {e}[/red]")
        return
    finally:
        driver.close()
    
    # Perform cross-device analysis
    if change_type == 'auto':
        # Try BGP analysis first as it's most comprehensive
        change_type = 'bgp'
    
    analysis_result = analyze_cross_device_impact(hostname, change_type)
    
    if analysis_result:
        display_cross_device_analysis(hostname, analysis_result)
        
        # Summary panel
        console.print(Panel.fit(
            f"[bold green]🎯 Graph Analysis Summary[/bold green]\n\n"
            f"[bold]Device:[/bold] {hostname}\n"
            f"[bold]Analysis Type:[/bold] {change_type}\n"
            f"[bold]Graph Database:[/bold] {NEO4J_URI}\n"
            f"[bold]Status:[/bold] [green]Analysis Complete ✅[/green]",
            title="Multi-Device Impact Analysis",
            border_style="green"
        ))
    else:
        console.print("[yellow]⚠️ No cross-device impacts found or analysis failed[/yellow]")


def register_enhanced_analysis_commands(main_cli_group):
    """Register enhanced analysis commands with the main CLI."""
    # Add the graph analysis command to the main analyze group or create analyze group
    try:
        # Try to get existing analyze command group
        analyze_cmd = None
        for cmd in main_cli_group.commands.values():
            if cmd.name == 'analyze':
                if hasattr(cmd, 'add_command'):
                    cmd.add_command(analyze_graph)
                    return
                else:
                    # analyze is a single command, we need to create a group
                    break
        
        # If no analyze group exists, add as standalone command  
        main_cli_group.add_command(analyze_graph)
        
    except Exception as e:
        console.print(f"[yellow]Warning: Could not register graph analysis command: {e}[/yellow]")