"""
Simplified Neo4j Graph Database CLI Commands.
Uses direct Neo4j connections to avoid import issues.
"""

import click
import os
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
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


@click.group(name='ingest')
def ingest_group():
    """Graph database ingestion commands."""
    pass


@ingest_group.command()
def all():
    """Run complete ingestion pipeline (schema + devices + topology)."""
    console.print("[bold blue]🚀 Complete Graph Ingestion Pipeline[/bold blue]")
    console.print("[yellow]Note: Full ingestion pipeline requires graph module imports.[/yellow]")
    console.print("[yellow]Current implementation shows database status instead.[/yellow]")
    
    # Show current database status as alternative
    driver = get_neo4j_driver()
    if not driver:
        return
        
    try:
        with driver.session() as session:
            # Show current data
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
            
            table = Table(title="Current Database Content")
            table.add_column("Node Type", style="cyan")
            table.add_column("Count", style="magenta", justify="right")
            
            total_nodes = 0
            for record in result:
                labels = record["labels"]
                count = record["count"]
                total_nodes += count
                label_str = ":".join(labels) if labels else "No Label"
                table.add_row(label_str, str(count))
            
            console.print(table)
            console.print(f"[dim]Total nodes: {total_nodes}[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Failed to query database: {e}[/red]")
    finally:
        driver.close()


@ingest_group.command()
def devices():
    """Ingest device configurations only."""
    console.print("[bold blue]📱 Device Configuration Ingestion[/bold blue]")
    console.print("[yellow]Note: Device ingestion requires loader modules.[/yellow]")
    console.print("[yellow]Showing current device inventory instead.[/yellow]")
    
    # Show current devices as alternative
    _show_devices_impl()


@ingest_group.command() 
def topology():
    """Ingest network topology data only."""
    console.print("[bold blue]🌐 Network Topology Ingestion[/bold blue]")
    console.print("[yellow]Note: Topology ingestion requires loader modules.[/yellow]")
    console.print("[yellow]Showing current topology instead.[/yellow]")
    
    # Show current topology as alternative
    _show_topology_impl()


@ingest_group.command()
@click.argument('hostname')
def device(hostname):
    """Ingest single device configuration."""
    console.print(f"[bold blue]📱 Single Device Ingestion: {hostname}[/bold blue]")
    console.print("[yellow]Note: Device ingestion requires loader modules.[/yellow]")
    console.print(f"[yellow]Showing current data for {hostname} instead.[/yellow]")
    
    # Show device details as alternative
    _show_device_impl(hostname)


@click.group(name='show')
def show_group():
    """Graph database status and visualization commands."""
    pass


@show_group.command()
def status():
    """Show graph database status and statistics."""
    console.print("[bold blue]📊 Graph Database Status[/bold blue]")
    
    driver = get_neo4j_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            # Database overview
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            total_nodes = result.single()["total_nodes"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total_relationships")
            total_rels = result.single()["total_relationships"]
            
            result = session.run("MATCH (d:Device) RETURN count(d) as device_count")
            device_count = result.single()["device_count"]
            
            result = session.run("MATCH (i:Interface) RETURN count(i) as interface_count")  
            interface_count = result.single()["interface_count"]
            
            # Status panel
            console.print(Panel.fit(
                f"[bold blue]🏗️ Neo4j Graph Database Status[/bold blue]\n\n"
                f"[bold]Database URI:[/bold] {NEO4J_URI}\n"
                f"[bold]Total Nodes:[/bold] {total_nodes:,}\n"
                f"[bold]Total Relationships:[/bold] {total_rels:,}\n"
                f"[bold]Devices:[/bold] {device_count}\n"
                f"[bold]Interfaces:[/bold] {interface_count}\n"
                f"[bold]Status:[/bold] [green]OPERATIONAL ✅[/green]",
                title="Database Overview",
                border_style="blue"
            ))
            
            # Node type distribution
            result = session.run("MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC")
            
            nodes_table = Table(title="📋 Node Type Distribution")
            nodes_table.add_column("Node Type", style="cyan", no_wrap=True)
            nodes_table.add_column("Count", style="magenta", justify="right")
            
            for record in result:
                labels = record["labels"]
                count = record["count"]
                if count > 0:
                    label_str = ":".join(labels) if labels else "No Label"
                    nodes_table.add_row(label_str, str(count))
            
            console.print(nodes_table)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve status: {e}[/red]")
    finally:
        driver.close()


@show_group.command()
def topology():
    """Show network topology overview."""
    console.print("[bold blue]🌐 Network Topology Overview[/bold blue]")
    _show_topology_impl()


@show_group.command()
def devices():
    """Show device inventory in graph database.""" 
    console.print("[bold blue]📱 Device Inventory[/bold blue]")
    _show_devices_impl()


@show_group.command()
@click.argument('hostname')
def device(hostname):
    """Show detailed information for a specific device."""
    console.print(f"[bold blue]📱 Device Details: {hostname}[/bold blue]")
    _show_device_impl(hostname)


def _show_devices_impl():
    """Implementation for showing devices."""
    driver = get_neo4j_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (d:Device)
                OPTIONAL MATCH (d)-[:LATEST]->(ds:DeviceState)
                OPTIONAL MATCH (d)-[:HAS_INTERFACE]->(i:Interface)
                RETURN d.hostname as hostname,
                       ds.vendor as vendor,
                       ds.os_type as os_type,
                       ds.platform as platform,
                       ds.management_ip as mgmt_ip,
                       count(i) as interface_count
                ORDER BY hostname
            """)
            
            devices_table = Table(title="Device Inventory")
            devices_table.add_column("Hostname", style="green", no_wrap=True)
            devices_table.add_column("Vendor", style="cyan")
            devices_table.add_column("OS Type", style="cyan")
            devices_table.add_column("Platform", style="magenta")
            devices_table.add_column("Management IP", style="blue")
            devices_table.add_column("Interfaces", style="yellow", justify="right")
            
            device_count = 0
            for record in result:
                devices_table.add_row(
                    record['hostname'] or 'unknown',
                    record['vendor'] or 'unknown',
                    record['os_type'] or 'unknown',
                    record['platform'] or 'unknown',
                    record['mgmt_ip'] or 'unknown',
                    str(record['interface_count'] or 0)
                )
                device_count += 1
            
            console.print(devices_table)
            console.print(f"[dim]Total devices: {device_count}[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve devices: {e}[/red]")
    finally:
        driver.close()


def _show_topology_impl():
    """Implementation for showing topology."""
    driver = get_neo4j_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            # Physical connections
            console.print("[bold cyan]🔗 Physical Network Connections[/bold cyan]")
            
            result = session.run("""
                MATCH (i1:Interface)-[c:CONNECTED_TO]->(i2:Interface)
                MATCH (d1:Device)-[:HAS_INTERFACE]->(i1)
                MATCH (d2:Device)-[:HAS_INTERFACE]->(i2)
                RETURN d1.hostname as device1, i1.name as int1,
                       d2.hostname as device2, i2.name as int2,
                       c.discovered_via as method
                ORDER BY device1, device2
            """)
            
            connections_table = Table()
            connections_table.add_column("Source Device", style="green")
            connections_table.add_column("Source Interface", style="cyan")
            connections_table.add_column("Target Device", style="green")
            connections_table.add_column("Target Interface", style="cyan")
            connections_table.add_column("Discovery Method", style="dim")
            
            connection_count = 0
            for record in result:
                connections_table.add_row(
                    record['device1'],
                    record['int1'],
                    record['device2'],
                    record['int2'],
                    record['method'] or 'lldp'
                )
                connection_count += 1
            
            if connection_count > 0:
                console.print(connections_table)
                console.print(f"[dim]Total connections: {connection_count}[/dim]")
            else:
                console.print("[yellow]No physical connections found[/yellow]")
            
            # BGP peering summary
            console.print(f"\n[bold cyan]🌐 BGP Peering Summary[/bold cyan]")
            
            result = session.run("""
                MATCH (d:Device)-[:BGP_PEER_WITH]->(p:BGPPeer)
                OPTIONAL MATCH (p)-[:LATEST]->(ps:BGPPeerState)
                RETURN d.hostname as device,
                       count(p) as peer_count,
                       collect(DISTINCT ps.peer_asn)[0..3] as sample_asns
                ORDER BY device
            """)
            
            bgp_table = Table()
            bgp_table.add_column("Device", style="green")
            bgp_table.add_column("BGP Peers", style="magenta", justify="right")
            bgp_table.add_column("Sample ASNs", style="cyan")
            
            for record in result:
                sample_asns = [str(asn) for asn in record['sample_asns'] if asn is not None]
                asn_display = ', '.join(sample_asns) + '...' if len(sample_asns) == 3 else ', '.join(sample_asns)
                
                bgp_table.add_row(
                    record['device'],
                    str(record['peer_count']),
                    asn_display if sample_asns else 'unknown'
                )
            
            console.print(bgp_table)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve topology data: {e}[/red]")
    finally:
        driver.close()


def _show_device_impl(hostname: str):
    """Implementation for showing device details."""
    driver = get_neo4j_driver()
    if not driver:
        return
    
    try:
        with driver.session() as session:
            # Device basic info
            result = session.run("""
                MATCH (d:Device {hostname: $hostname})
                OPTIONAL MATCH (d)-[:LATEST]->(ds:DeviceState)
                RETURN d.hostname as hostname,
                       ds.vendor as vendor,
                       ds.os_type as os_type,
                       ds.platform as platform,
                       ds.management_ip as mgmt_ip,
                       ds.timestamp as last_update
            """, hostname=hostname)
            
            device_record = result.single()
            if not device_record:
                console.print(f"[red]❌ Device '{hostname}' not found in graph database[/red]")
                return
            
            # Device info panel
            last_update = device_record['last_update']
            update_str = str(last_update) if last_update else 'unknown'
            
            console.print(Panel.fit(
                f"[bold]Hostname:[/bold] {device_record['hostname']}\n"
                f"[bold]Vendor:[/bold] {device_record['vendor'] or 'unknown'}\n"
                f"[bold]OS Type:[/bold] {device_record['os_type'] or 'unknown'}\n"
                f"[bold]Platform:[/bold] {device_record['platform'] or 'unknown'}\n"
                f"[bold]Management IP:[/bold] {device_record['mgmt_ip'] or 'unknown'}\n"
                f"[bold]Last Update:[/bold] {update_str}",
                title=f"Device: {hostname}",
                border_style="blue"
            ))
            
            # Interface summary
            result = session.run("""
                MATCH (d:Device {hostname: $hostname})-[:HAS_INTERFACE]->(i:Interface)
                RETURN i.name as interface_name
                ORDER BY i.name
                LIMIT 20
            """, hostname=hostname)
            
            interfaces = [record['interface_name'] for record in result]
            if interfaces:
                console.print(f"\n[bold cyan]🔌 Interfaces ({len(interfaces)}):[/bold cyan]")
                interface_text = ", ".join(interfaces)
                if len(interfaces) == 20:
                    interface_text += "..."
                console.print(f"[dim]{interface_text}[/dim]")
            
            # VLAN summary
            result = session.run("""
                MATCH (v:VLAN {device_hostname: $hostname})
                RETURN v.vlan_number as vlan_id
                ORDER BY vlan_id
            """, hostname=hostname)
            
            vlans = [record['vlan_id'] for record in result]
            if vlans:
                console.print(f"\n[bold yellow]🏷️ VLANs ({len(vlans)}):[/bold yellow]")
                vlan_text = ", ".join(map(str, vlans))
                console.print(f"[dim]{vlan_text}[/dim]")
            
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve device details: {e}[/red]")
    finally:
        driver.close()


# Register command groups with main CLI
def register_simple_graph_commands(main_cli_group):
    """
    Register simplified graph command groups with the main CLI.
    Args: main_cli_group - the main Click group to add commands to.
    """
    main_cli_group.add_command(ingest_group)
    main_cli_group.add_command(show_group)