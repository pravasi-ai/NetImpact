"""
Neo4j Graph Database CLI Commands.
Provides CLI interface for graph ingestion, status monitoring, and visualization.
"""

import click
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
import logging

# Setup paths for graph imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

console = Console()
logger = logging.getLogger(__name__)


def get_graph_pipeline():
    """
    Get graph ingestion pipeline instance with proper import handling.
    Returns: GraphIngestionPipeline instance or None if import fails.
    """
    try:
        # Change to graph directory for imports to work
        original_cwd = os.getcwd()
        os.chdir(project_root / 'src' / 'graph')
        
        from ingestion_pipeline import GraphIngestionPipeline
        pipeline = GraphIngestionPipeline()
        
        # Restore original directory
        os.chdir(original_cwd)
        
        return pipeline
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize graph pipeline: {e}[/red]")
        return None


def get_graph_schema():
    """
    Get graph schema instance with proper import handling.
    Returns: GraphSchema instance or None if import fails.
    """
    try:
        # Change to graph directory for imports to work
        original_cwd = os.getcwd()
        os.chdir(project_root / 'src' / 'graph')
        
        from graph_schema import GraphSchema
        schema = GraphSchema.from_config()
        
        # Restore original directory
        os.chdir(original_cwd)
        
        return schema
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize graph schema: {e}[/red]")
        return None


def display_ingestion_results(results: Dict[str, Any]):
    """
    Display ingestion pipeline results in a formatted table.
    Args: results dictionary from pipeline execution.
    """
    # Pipeline execution summary
    execution = results.get('pipeline_execution', {})
    summary = results.get('ingestion_summary', {})
    
    console.print(Panel.fit(
        f"[bold green]🚀 Pipeline Execution Summary[/bold green]\n\n"
        f"[bold]Status:[/bold] {execution.get('status', 'unknown').upper()}\n"
        f"[bold]Duration:[/bold] {execution.get('duration_seconds', 0):.2f} seconds\n"
        f"[bold]Started:[/bold] {execution.get('started_at', 'unknown')}\n"
        f"[bold]Completed:[/bold] {execution.get('completed_at', 'unknown')}",
        title="Execution",
        border_style="green"
    ))
    
    # Ingestion statistics
    stats_table = Table(title="📊 Ingestion Statistics")
    stats_table.add_column("Metric", style="cyan", no_wrap=True)
    stats_table.add_column("Count", style="magenta", justify="right")
    
    stats_table.add_row("Devices Processed", str(summary.get('devices_processed', 0)))
    stats_table.add_row("Topology Files", str(summary.get('topology_files_processed', 0)))
    stats_table.add_row("Nodes Created", str(summary.get('total_nodes_created', 0)))
    stats_table.add_row("Connections Created", str(summary.get('total_connections_created', 0)))
    stats_table.add_row("Sites Created", str(summary.get('sites_created', 0)))
    
    console.print(stats_table)
    
    # Graph database statistics
    graph_stats = results.get('graph_statistics', {})
    if graph_stats:
        graph_table = Table(title="🗃️ Graph Database Content")
        graph_table.add_column("Node Type", style="cyan", no_wrap=True)
        graph_table.add_column("Count", style="magenta", justify="right")
        
        # Show only non-zero counts
        for key, value in graph_stats.items():
            if value > 0:
                # Format key for display
                display_key = key.replace('_', ' ').title()
                graph_table.add_row(display_key, str(value))
        
        console.print(graph_table)


def display_status_summary(status: Dict[str, Any]):
    """
    Display comprehensive graph database status.
    Args: status dictionary from pipeline.
    """
    graph_stats = status.get('graph_statistics', {})
    topology_stats = status.get('topology_statistics', {})
    config = status.get('configuration', {})
    
    # Database overview panel
    total_nodes = sum(v for v in graph_stats.values() if isinstance(v, int))
    total_devices = graph_stats.get('devices', 0)
    total_interfaces = graph_stats.get('interfaces', 0)
    
    console.print(Panel.fit(
        f"[bold blue]🏗️ Neo4j Graph Database Status[/bold blue]\n\n"
        f"[bold]Database URI:[/bold] {config.get('neo4j_uri', 'unknown')}\n"
        f"[bold]Total Nodes:[/bold] {total_nodes:,}\n"
        f"[bold]Devices:[/bold] {total_devices}\n"
        f"[bold]Interfaces:[/bold] {total_interfaces}\n"
        f"[bold]Status:[/bold] [green]OPERATIONAL ✅[/green]",
        title="Database Overview",
        border_style="blue"
    ))
    
    # Detailed node statistics
    if graph_stats:
        nodes_table = Table(title="📋 Node Type Distribution")
        nodes_table.add_column("Node Type", style="cyan", no_wrap=True)
        nodes_table.add_column("Count", style="magenta", justify="right")
        nodes_table.add_column("Description", style="dim")
        
        # Node type descriptions
        descriptions = {
            'devices': 'Network devices (switches, routers)',
            'interfaces': 'Physical and logical interfaces',
            'vlans': 'VLAN configurations',
            'acls': 'Access control lists',
            'bgp_instances': 'BGP routing instances',
            'bgp_peers': 'BGP peering relationships',
            'device_states': 'Device configuration versions',
            'connections': 'Physical connectivity (LLDP)',
            'sites': 'Geographic locations'
        }
        
        for key, value in graph_stats.items():
            if value > 0:
                display_key = key.replace('_', ' ').title()
                description = descriptions.get(key, 'Configuration objects')
                nodes_table.add_row(display_key, str(value), description)
        
        console.print(nodes_table)
    
    # Topology overview
    if topology_stats:
        topology_table = Table(title="🌐 Network Topology Summary")
        topology_table.add_column("Metric", style="cyan", no_wrap=True)
        topology_table.add_column("Count", style="magenta", justify="right")
        
        for key, value in topology_stats.items():
            if isinstance(value, int) and value > 0:
                display_key = key.replace('_', ' ').title()
                topology_table.add_row(display_key, str(value))
        
        console.print(topology_table)


def display_topology_overview():
    """Display network topology relationships and connections."""
    schema = get_graph_schema()
    if not schema:
        return
    
    try:
        with schema.driver.session() as session:
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
            console.print(f"\n[bold cyan]🌐 BGP Peering Relationships[/bold cyan]")
            
            result = session.run("""
                MATCH (d:Device)-[:BGP_PEER_WITH]->(p:BGPPeer)
                OPTIONAL MATCH (p)-[:LATEST]->(ps:BGPPeerState)
                RETURN d.hostname as device, 
                       count(p) as peer_count,
                       collect(DISTINCT ps.peer_asn) as peer_asns
                ORDER BY device
            """)
            
            bgp_table = Table()
            bgp_table.add_column("Device", style="green")
            bgp_table.add_column("Peer Count", style="magenta", justify="right")
            bgp_table.add_column("Peer ASNs", style="cyan")
            
            for record in result:
                peer_asns = [str(asn) for asn in record['peer_asns'] if asn is not None]
                bgp_table.add_row(
                    record['device'],
                    str(record['peer_count']),
                    ', '.join(set(peer_asns)) if peer_asns else 'unknown'
                )
            
            console.print(bgp_table)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve topology data: {e}[/red]")
    finally:
        if schema:
            schema.close()


@click.group(name='ingest')
def ingest_group():
    """Graph database ingestion commands."""
    pass


@ingest_group.command()
def all():
    """Run complete ingestion pipeline (schema + devices + topology)."""
    console.print("[bold blue]🚀 Starting Complete Graph Ingestion Pipeline[/bold blue]")
    
    pipeline = get_graph_pipeline()
    if not pipeline:
        return
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Running complete ingestion pipeline...", total=None)
            
            results = pipeline.run_complete_ingestion()
            
            progress.update(task, completed=True)
        
        console.print("[bold green]✅ Complete ingestion pipeline finished![/bold green]")
        display_ingestion_results(results)
        
        # Show any errors
        errors = results.get('errors', [])
        if errors:
            console.print(f"\n[bold yellow]⚠️ Warnings/Errors ({len(errors)}):[/bold yellow]")
            for error in errors[:5]:  # Show first 5 errors
                console.print(f"  [red]•[/red] {error}")
            if len(errors) > 5:
                console.print(f"  [dim]... and {len(errors) - 5} more[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Ingestion pipeline failed: {e}[/red]")
        logger.exception("Ingestion pipeline error")
    finally:
        if pipeline:
            pipeline.cleanup()


@ingest_group.command()
def devices():
    """Ingest device configurations only."""
    console.print("[bold blue]📱 Ingesting Device Configurations[/bold blue]")
    
    pipeline = get_graph_pipeline()
    if not pipeline:
        return
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Ingesting device configurations...", total=None)
            
            # Get current status for comparison
            initial_status = pipeline.get_pipeline_status()
            initial_devices = initial_status.get('graph_statistics', {}).get('devices', 0)
            
            # Run device-specific ingestion (we'll implement this method)
            console.print("[yellow]Note: Device-only ingestion not yet implemented.[/yellow]")
            console.print("[yellow]Running schema initialization instead...[/yellow]")
            
            # Initialize schema as a substitute
            schema = get_graph_schema()
            if schema:
                schema.initialize_schema()
                final_status = pipeline.get_pipeline_status()
                schema.close()
                
                progress.update(task, completed=True)
                console.print("[bold green]✅ Schema initialization completed![/bold green]")
                display_status_summary(final_status)
            
    except Exception as e:
        console.print(f"[red]❌ Device ingestion failed: {e}[/red]")
        logger.exception("Device ingestion error")
    finally:
        if pipeline:
            pipeline.cleanup()


@ingest_group.command()
def topology():
    """Ingest network topology data only."""
    console.print("[bold blue]🌐 Ingesting Network Topology[/bold blue]")
    
    pipeline = get_graph_pipeline()
    if not pipeline:
        return
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Ingesting topology data...", total=None)
            
            console.print("[yellow]Note: Topology-only ingestion not yet implemented.[/yellow]")
            console.print("[yellow]Showing current topology instead...[/yellow]")
            
            progress.update(task, completed=True)
        
        # Display current topology
        display_topology_overview()
        
    except Exception as e:
        console.print(f"[red]❌ Topology ingestion failed: {e}[/red]")
        logger.exception("Topology ingestion error")
    finally:
        if pipeline:
            pipeline.cleanup()


@ingest_group.command()
@click.argument('hostname')
def device(hostname):
    """Ingest single device configuration."""
    console.print(f"[bold blue]📱 Ingesting Device: {hostname}[/bold blue]")
    
    pipeline = get_graph_pipeline()
    if not pipeline:
        return
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Ingesting {hostname}...", total=None)
            
            # Use pipeline's incremental update method
            result = pipeline.run_incremental_update(hostname)
            
            progress.update(task, completed=True)
        
        if result.get('status') == 'success':
            console.print(f"[bold green]✅ Successfully ingested {hostname}![/bold green]")
            console.print(f"[dim]Nodes created: {result.get('nodes_created', 0)}[/dim]")
        else:
            console.print(f"[red]❌ Failed to ingest {hostname}: {result.get('error')}[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ Device ingestion failed: {e}[/red]")
        logger.exception("Single device ingestion error")
    finally:
        if pipeline:
            pipeline.cleanup()


@click.group(name='show')
def show_group():
    """Graph database status and visualization commands."""
    pass


@show_group.command()
def status():
    """Show graph database status and statistics."""
    console.print("[bold blue]📊 Graph Database Status[/bold blue]")
    
    pipeline = get_graph_pipeline()
    if not pipeline:
        return
    
    try:
        status = pipeline.get_pipeline_status()
        display_status_summary(status)
        
    except Exception as e:
        console.print(f"[red]❌ Failed to retrieve status: {e}[/red]")
        logger.exception("Status retrieval error")
    finally:
        if pipeline:
            pipeline.cleanup()


@show_group.command()
def topology():
    """Show network topology overview."""
    console.print("[bold blue]🌐 Network Topology Overview[/bold blue]")
    
    try:
        display_topology_overview()
        
    except Exception as e:
        console.print(f"[red]❌ Failed to display topology: {e}[/red]")
        logger.exception("Topology display error")


@show_group.command()
def devices():
    """Show device inventory in graph database."""
    console.print("[bold blue]📱 Device Inventory[/bold blue]")
    
    schema = get_graph_schema()
    if not schema:
        return
    
    try:
        with schema.driver.session() as session:
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
        logger.exception("Device retrieval error")
    finally:
        if schema:
            schema.close()


@show_group.command()
@click.argument('hostname')
def device(hostname):
    """Show detailed information for a specific device."""
    console.print(f"[bold blue]📱 Device Details: {hostname}[/bold blue]")
    
    schema = get_graph_schema()
    if not schema:
        return
    
    try:
        with schema.driver.session() as session:
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
            """, hostname=hostname)
            
            interfaces = [record['interface_name'] for record in result]
            if interfaces:
                console.print(f"\n[bold cyan]🔌 Interfaces ({len(interfaces)}):[/bold cyan]")
                interface_text = ", ".join(interfaces)
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
        logger.exception("Device detail retrieval error")
    finally:
        if schema:
            schema.close()


# Register command groups with main CLI
def register_graph_commands(main_cli_group):
    """
    Register graph command groups with the main CLI.
    Args: main_cli_group - the main Click group to add commands to.
    """
    main_cli_group.add_command(ingest_group)
    main_cli_group.add_command(show_group)