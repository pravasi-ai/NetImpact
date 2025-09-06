"""
Network Configuration Impact Analysis CLI - Production Version.
Integrates POC's proven generic diff and TRUE schema-driven dependency analysis.
"""

import click
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# Add project root to Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import production components (migrated from POC)
from src.loaders.config_loader import ConfigLoader
from src.diff.generic_diff_engine import GenericDiffEngine, ConfigChange

# Import TRUE schema-driven analyzer
from src.analysis.schema_analyzer.true_schema_analyzer import TrueSchemaDrivenAnalyzer, TrueSchemaDependency, ConfigurationChange

# Import text configuration processing modules (new modular components)
from src.loaders.format_detector import FormatDetector, ConfigFormat
from src.loaders.text_to_yang_converter import TextToYangConverter


@dataclass
class Dependency:
    """Compatibility wrapper for TRUE schema dependencies."""
    source_path: str
    target_path: str
    dependency_type: str
    source_value: Any = None
    target_object: Any = None
    description: str = ""
    display_source: str = "" # New field for human-readable source
    display_target: str = "" # New field for human-readable target
    config_object_type: str = "" # New field for config object type


class TrueSchemaAnalyzerBridge:
    """
    Bridge between TRUE schema-driven analyzer and CLI interface.
    Adapts TRUE schema analyzer for production use.
    """
    
    def __init__(self, project_root: Path):
        self.analyzer = TrueSchemaDrivenAnalyzer()
        self.project_root = project_root
        
    def find_dependencies(self, current_config: Dict, changed_paths: List[str]) -> List[Dependency]:
        """
        Find dependencies using TRUE schema-driven analysis.
        Adapts to CLI interface expectations.
        """
        # Save current config to temp file for TRUE analyzer
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(current_config, f)
            current_file = f.name
        
        try:
            # Create a minimal proposed config with just the changed paths
            proposed_config = self._create_minimal_proposed_config(current_config, changed_paths)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(proposed_config, f)
                proposed_file = f.name
            
            try:
                # Run TRUE schema-driven analysis
                result = self.analyzer.analyze_configuration_file(current_file, proposed_file)
                
                if result.get('success') and result.get('dependencies'):
                    # Convert TrueSchemaDependency to Dependency objects
                    dependencies = []
                    for true_dep in result['dependencies']:
                        dep = Dependency(
                            source_path=true_dep.config_change_path,
                            target_path=true_dep.affected_leafref_target,
                            dependency_type="schema_leafref",
                            source_value=true_dep.affected_leafref_source,
                            target_object=true_dep.affected_leafref_target,
                            description=true_dep.leafref_description
                        )
                        dependencies.append(dep)
                    
                    return dependencies
                
                return []
                
            finally:
                os.unlink(proposed_file)
                
        finally:
            os.unlink(current_file)
    
    def _create_minimal_proposed_config(self, current_config: Dict, changed_paths: List[str]) -> Dict:
        """Create minimal proposed config for TRUE analyzer to detect changes."""
        # For now, return the current config - the TRUE analyzer will detect no changes
        # This is a simplified approach; in a real implementation, you'd construct 
        # the proposed config based on the changed paths
        return current_config.copy()
    
    def get_dependency_summary(self, dependencies: List[Dependency]) -> Dict[str, Any]:
        """Generate dependency summary compatible with existing interface."""
        summary = {
            'total_dependencies': len(dependencies),
            'by_type': {},
            'by_source_section': {},
            'by_target_section': {}
        }
        
        for dep in dependencies:
            # Count by type
            if dep.dependency_type not in summary['by_type']:
                summary['by_type'][dep.dependency_type] = 0
            summary['by_type'][dep.dependency_type] += 1
            
            # Count by source section
            source_section = dep.source_path.split('/')[0] if '/' in dep.source_path else dep.source_path
            if source_section not in summary['by_source_section']:
                summary['by_source_section'][source_section] = []
            summary['by_source_section'][source_section].append(dep)
            
            # Count by target section
            target_section = dep.target_path.split('/')[0] if '/' in dep.target_path else dep.target_path
            if target_section not in summary['by_target_section']:
                summary['by_target_section'][target_section] = []
            summary['by_target_section'][target_section].append(dep)
        
        return summary


# Setup rich console for output
console = Console()

# Project root path
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Load impact resolution rules
IMPACT_RULES_FILE = PROJECT_ROOT / "config" / "config_impact_rules.json"
IMPACT_RESOLUTION_RULES = []
if IMPACT_RULES_FILE.exists():
    with open(IMPACT_RULES_FILE, 'r') as f:
        IMPACT_RESOLUTION_RULES = json.load(f)
    console.print(f"[dim]Loaded {len(IMPACT_RESOLUTION_RULES)} impact resolution rules.[/dim]")
else:
    console.print(f"[yellow]Warning: Impact resolution rules file not found at {IMPACT_RULES_FILE}[/yellow]")


def _process_config_file(file_path: str, analysis_mode: str = "partial") -> Dict[str, Any]:
    """
    Process configuration file, automatically detecting format and converting text to YANG if needed.
    Maintains backward compatibility with existing YANG-based workflow.
    
    Args:
        file_path: Path to configuration file (text or YANG format)
        
    Returns:
        Processed configuration as dictionary (always in YANG format)
        
    Raises:
        Exception: If file format cannot be detected or conversion fails
    """
    try:
        # Validate file exists and is readable
        if not os.path.exists(file_path):
            raise Exception(f"Configuration file not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise Exception(f"Path is not a file: {file_path}")
        
        # Detect configuration format
        console.print(f"[dim]Analyzing configuration format: {Path(file_path).name}[/dim]")
        format_detector = FormatDetector()
        detected_format, format_error, format_metadata = format_detector.detect_format(file_path)
        
        if detected_format == ConfigFormat.UNKNOWN:
            # Provide helpful error message with format hints
            error_msg = f"Could not detect configuration format"
            if format_error:
                error_msg += f": {format_error}"
            error_msg += f"\n\nSupported formats:"
            error_msg += f"\n  • JSON YANG configurations (*.json)"
            error_msg += f"\n  • XML YANG configurations (*.xml)"
            error_msg += f"\n  • Text device configurations (Cisco IOS, Arista EOS)"
            error_msg += f"\n\nPlease ensure the file contains valid network configuration data."
            raise Exception(error_msg)
        
        # Handle JSON/XML YANG formats (existing production workflow)
        if detected_format in [ConfigFormat.JSON, ConfigFormat.XML]:
            console.print(f"[dim]Detected YANG format: {detected_format.value} - using existing workflow[/dim]")
            
            try:
                # Load directly using existing config loader
                config_loader = ConfigLoader(PROJECT_ROOT)
                config = config_loader.load_proposed_config(file_path)
                if not config:
                    raise Exception(f"YANG configuration file appears to be empty or invalid")
                return config
                
            except Exception as e:
                error_msg = f"Failed to load YANG configuration from {Path(file_path).name}"
                if "JSON" in str(e) or "json" in str(e):
                    error_msg += f"\nJSON parsing error: {str(e)}"
                elif "XML" in str(e) or "xml" in str(e):
                    error_msg += f"\nXML parsing error: {str(e)}"
                else:
                    error_msg += f"\nError: {str(e)}"
                raise Exception(error_msg)
        
        # Handle text format (new workflow with conversion)
        elif detected_format == ConfigFormat.TEXT:
            console.print(f"[blue]Detected text configuration format[/blue]")
            console.print(f"[dim]Analysis mode: {analysis_mode}[/dim]")
            
            # Display format metadata for user feedback
            vendor = format_metadata.get('detected_vendor', 'unknown')
            if vendor == 'unknown':
                console.print(f"[yellow]Warning: Could not determine device vendor - proceeding with generic parsing[/yellow]")
            else:
                console.print(f"[dim]Vendor: {vendor} | "
                             f"Config lines: {format_metadata.get('total_config_lines', 0)}[/dim]")
            
            # Convert text to YANG with analysis mode
            console.print("[blue]Converting text configuration to YANG format...[/blue]")
            
            try:
                text_converter = TextToYangConverter()
                success, yang_data, error_message, conversion_metadata = text_converter.convert(
                    file_path, 
                    vendor if vendor != 'unknown' else None
                )
                
                if not success:
                    # Provide detailed conversion error with helpful suggestions
                    detailed_error = f"Text-to-YANG conversion failed: {error_message}"
                    
                    # Add specific suggestions based on error type
                    if "vendor" in error_message.lower():
                        detailed_error += f"\n\nSuggestions:"
                        detailed_error += f"\n  • Specify vendor manually using --vendor parameter"
                        detailed_error += f"\n  • Supported vendors: cisco_ios, arista_eos"
                    elif "parsing" in error_message.lower():
                        detailed_error += f"\n\nSuggestions:"
                        detailed_error += f"\n  • Verify configuration syntax is valid"
                        detailed_error += f"\n  • Check for unsupported configuration commands"
                    elif "yang" in error_message.lower():
                        detailed_error += f"\n\nSuggestions:"
                        detailed_error += f"\n  • Some configuration sections may not have YANG equivalents"
                        detailed_error += f"\n  • Try with a simpler configuration subset"
                    
                    raise Exception(detailed_error)
                
                # No filtering needed - YANG transformer only includes configured sections
                
                # Display conversion feedback
                console.print("[green]✓ Text-to-YANG conversion successful[/green]")
                
                # Display conversion statistics
                stats = conversion_metadata.get('transformation_stats', {})
                parsing_stats = conversion_metadata.get('parsing_stats', {})
                
                if stats or parsing_stats:
                    console.print(f"[dim]Generated {stats.get('yang_objects', 0)} YANG objects | "
                                 f"Interfaces: {stats.get('interfaces_count', 0)} | "
                                 f"VLANs: {stats.get('vlans_count', 0)} | "
                                 f"Parsed sections: {parsing_stats.get('total_sections', 0)}[/dim]")
                
                # Display warnings with helpful context
                warnings = conversion_metadata.get('warnings', [])
                if warnings:
                    console.print("[yellow]Conversion notices:[/yellow]")
                    for warning in warnings[:5]:  # Show up to 5 warnings
                        console.print(f"[yellow]  • {warning}[/yellow]")
                    
                    if len(warnings) > 5:
                        console.print(f"[dim]  ... and {len(warnings) - 5} more notices[/dim]")
                
                return yang_data
                
            except Exception as e:
                if "Text-to-YANG conversion failed:" in str(e):
                    # Re-raise our detailed error message
                    raise
                else:
                    # Wrap unexpected errors
                    raise Exception(f"Unexpected error during text configuration processing: {str(e)}")
        
        else:
            raise Exception(f"Unsupported configuration format: {detected_format}")
            
    except Exception as e:
        # Ensure all errors are properly formatted for CLI display
        if not str(e).startswith("Configuration processing failed"):
            error_msg = f"Configuration processing failed: {str(e)}"
            raise Exception(error_msg)
        else:
            raise


@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
def cli(verbose):
    """Network Configuration Impact Analysis Platform - Production Version."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger('yangson').setLevel(logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)


@cli.command()
@click.option('--device', '-d', required=True, help='Device name (e.g., core-sw-02)')
@click.option('--proposed', '-p', required=True, help='Proposed config file path')
@click.option('--replace', is_flag=True, help='Full configuration replacement mode (default: partial mode)')
@click.option('--detailed', is_flag=True, help='Show detailed analysis')
@click.option('--verbose', is_flag=True, help='Show verbose analysis output')
@click.option('--format', '-f', type=click.Choice(['table', 'json']), default='table', help='Output format')
def analyze(device: str, proposed: str, replace: bool, detailed: bool, verbose: bool, format: str):
    """Analyze configuration changes and dependencies using TRUE schema-driven analysis."""
    
    # Set verbose environment variable for schema analysis
    if verbose:
        os.environ['TRUE_SCHEMA_VERBOSE'] = '1'
    else:
        os.environ.pop('TRUE_SCHEMA_VERBOSE', None)
    
    # Initialize components
    config_loader = ConfigLoader(PROJECT_ROOT)
    diff_engine = GenericDiffEngine(PROJECT_ROOT / "models" / "yang")
    
    # Use TRUE schema-driven analyzer instead of old heuristic-based one
    true_analyzer = TrueSchemaDrivenAnalyzer()
    dependency_analyzer = TrueSchemaAnalyzerBridge(PROJECT_ROOT)
    
    try:
        # Load configurations
        console.print(f"[blue]Loading configurations for device: {device}[/blue]")
        
        current_config = config_loader.load_current_config(device)
        if not current_config:
            console.print(f"[red]Error: Could not load current config for device {device}[/red]")
            return
            
        # Use new modular config processing (handles both text and YANG formats)
        analysis_mode = "full" if replace else "partial"
        try:
            proposed_config = _process_config_file(proposed, analysis_mode)
            if not proposed_config:
                console.print(f"[red]Error: Could not process proposed config from {proposed}[/red]")
                return
        except Exception as config_error:
            console.print(f"[red]{config_error}[/red]")
            return
        
        console.print("[green]✓ Configurations loaded successfully[/green]")
        
        # Generate diff using existing working diff engine
        console.print("[blue]Analyzing configuration differences...[/blue]")
        changes = diff_engine.compare_configs(current_config, proposed_config)
        change_summary = diff_engine.get_change_summary(changes)
        
        # Use TRUE schema-driven dependency analysis
        console.print("[blue]Analyzing dependencies with TRUE schema-driven approach...[/blue]")
        
        # Save configs to temp files for TRUE analyzer
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(current_config, f)
            current_file = f.name
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(proposed_config, f)
                proposed_file = f.name
            
            try:
                # Run TRUE schema-driven analysis
                schema_result = true_analyzer.analyze_configuration_file(current_file, proposed_file)
                
                if schema_result.get('success'):
                    # Convert TRUE dependencies to CLI-compatible format
                    dependencies = []
                    if schema_result.get('dependencies'):
                        for true_dep in schema_result['dependencies']:
                            # Try to find matching detailed change path from GenericDiffEngine
                            detailed_path = true_dep.config_change_path
                            for change in changes:
                                if change.path and true_dep.config_change_path in change.path:
                                    detailed_path = change.path
                                    break
                            
                            # Extract identifier from the detailed path
                            actual_identifier = _extract_identifier_from_path(detailed_path)
                            
                            # Get the actual value of the leafref target (e.g., the ACL name)
                            actual_source_value_for_dep = _get_object_at_path(current_config, true_dep.affected_leafref_target)
                            if actual_source_value_for_dep is None:
                                actual_source_value_for_dep = _get_object_at_path(proposed_config, true_dep.affected_leafref_target)

                            # If it's still None, fallback to the original affected_leafref_source (the path itself)
                            # This fallback might not be ideal, but keeps the code from breaking.
                            if actual_source_value_for_dep is None:
                                actual_source_value_for_dep = true_dep.affected_leafref_source

                            dep = Dependency(
                                source_path=true_dep.config_change_path,
                                target_path=true_dep.affected_leafref_target,
                                dependency_type="schema_leafref",
                                source_value=actual_identifier, # Use the already extracted actual_identifier
                                target_object=true_dep.affected_leafref_target,
                                description=true_dep.leafref_description
                            )
                            # Add the actual object identifier as an attribute
                            dep.actual_object_identifier = actual_identifier

                            # Populate display fields for intuitive output
                            dep.display_source = str(dep.source_value) # ACL name is already in source_value
                            dep.config_object_type = _extract_config_object_name(dep.source_path) # Populate config object type
                            
                            # Resolve impacted identifiers for display_target
                            resolved_impacted_identifiers = _resolve_dependency_target_identifiers_from_current_config(dep, current_config)
                            if resolved_impacted_identifiers:
                                dep.display_target = ", ".join(resolved_impacted_identifiers)
                            else:
                                # Fallback to raw target_path if no specific identifier found
                                dep.display_target = dep.target_path 

                            dependencies.append(dep)
                    
                    # Create a set of source identifiers that already have dependencies
                    sources_with_dependencies = {dep.display_source for dep in dependencies}

                    # Add changed objects that have no detected dependencies
                    for change in changes:
                        change_identifier = _extract_identifier_from_path(change.path)
                        if change_identifier and change_identifier not in sources_with_dependencies:
                            # Create a dummy dependency entry for changed objects with no detected dependencies
                            no_dep_entry = Dependency(
                                source_path=change.path,
                                target_path="", # No specific target path
                                dependency_type="no_dependency",
                                source_value=change_identifier,
                                target_object=None,
                                description="No direct schema-driven dependencies found.",
                                display_source=change_identifier,
                                display_target="", # Blank target for no dependency
                                config_object_type=_extract_config_object_name(change.path) # Populate config object type
                            )
                            dependencies.append(no_dep_entry)
                    
                    # Expand dependencies with multiple targets into separate entries
                    expanded_dependencies = []
                    for dep in dependencies:
                        if "," in dep.display_target:
                            targets = [t.strip() for t in dep.display_target.split(',')]
                            for target in targets:
                                new_dep = Dependency(
                                    source_path=dep.source_path,
                                    target_path=dep.target_path, # Keep original raw target path
                                    dependency_type=dep.dependency_type,
                                    source_value=dep.source_value,
                                    target_object=dep.target_object,
                                    description=dep.description,
                                    display_source=dep.display_source,
                                    display_target=target, # Single target per expanded entry
                                    config_object_type=dep.config_object_type
                                )
                                expanded_dependencies.append(new_dep)
                        else:
                            expanded_dependencies.append(dep) # Add as is if single target

                    # Deduplicate the comprehensive list of dependencies (now including expanded ones)
                    deduplicated_dependencies = []
                    seen_keys = set()
                    # Sort dependencies to ensure consistent order for deduplication
                    # Prioritize dependencies with actual targets over 'no_dependency' entries
                    expanded_dependencies.sort(key=lambda d: (d.display_source, d.display_target != ""))

                    for dep in expanded_dependencies:
                        key = (dep.display_source, dep.display_target)
                        if key not in seen_keys:
                            seen_keys.add(key)
                            deduplicated_dependencies.append(dep)
                    
                    dependencies = deduplicated_dependencies # Use deduplicated list for summary and display

                    # Generate summary using bridge
                    dependency_summary = dependency_analyzer.get_dependency_summary(dependencies)
                    
                    console.print(f"[green]✓ TRUE schema-driven analysis completed[/green]")
                    console.print(f"[dim]Found {len(schema_result.get('schema_leafrefs', []))} YANG leafrefs loaded[/dim]")
                    
                else:
                    console.print(f"[red]Error in TRUE schema analysis: {schema_result.get('error', 'Unknown error')}[/red]")
                    dependencies = []
                    dependency_summary = {'total_dependencies': 0, 'by_type': {}, 'by_source_section': {}, 'by_target_section': {}}
                    
            finally:
                os.unlink(proposed_file)
        finally:
            os.unlink(current_file)
        
        # Analyze per-object impact with change context
        impact_analysis = _analyze_per_object_impact(changes, dependencies, current_config)
        
        # Display results
        if format == 'json':
            _display_json_results(changes, dependencies, change_summary, dependency_summary, impact_analysis)
        else:
            _display_table_results(device, proposed, changes, dependencies, change_summary, dependency_summary, detailed, impact_analysis, current_config, proposed_config)
            
    except Exception as e:
        console.print(f"[red]Error during analysis: {e}[/red]")
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            import traceback
            console.print(traceback.format_exc())


@cli.command()
def list_devices():
    """List available devices and proposed configurations."""
    config_loader = ConfigLoader(PROJECT_ROOT)
    available = config_loader.list_available_devices()
    
    # Display current devices
    if available['current_devices']:
        console.print("\n[bold blue]Available Devices (./data/configs/):[/bold blue]")
        for device in sorted(available['current_devices']):
            console.print(f"  • {device}")
    else:
        console.print("[yellow]No current device configurations found[/yellow]")
    
    # Display proposed configs
    if available['proposed_configs']:
        console.print("\n[bold blue]Available Proposed Configs (./tests/):[/bold blue]")
        for config in sorted(available['proposed_configs']):
            console.print(f"  • {config}")
    else:
        console.print("[yellow]No proposed configurations found[/yellow]")


def _display_table_results(device: str, proposed_file: str, changes: List[ConfigChange], 
                          dependencies: List[Dependency], change_summary: Dict[str, Any],
                          dependency_summary: Dict[str, Any], detailed: bool, impact_analysis: Dict[str, Any],
                          current_config: Dict, proposed_config: Dict):
    """Display results in rich table format."""
    
    # Header panel
    console.print(Panel(
        f"[bold]Configuration Analysis Results[/bold]\n"
        f"Device: {device} | Proposed: {proposed_file}",
        style="blue"
    ))
    
    # Summary stats
    console.print(f"\n[bold green]Summary:[/bold green]")
    console.print(f"  Changes: {change_summary['total_changes']} "
                 f"(+{change_summary['added']} ~{change_summary['modified']} -{change_summary['deleted']})")
    console.print(f"  Dependencies: {dependency_summary['total_dependencies']}")
    
    # Changes in Unix diff style
    if changes:
        console.print(f"\n[bold blue]Configuration Changes:[/bold blue]")
        
        # Group changes by configuration object
        changes_by_object = {}
        for change in changes:
            # Extract config object name from path
            config_object = _extract_config_object_name(change.path)
            if config_object not in changes_by_object:
                changes_by_object[config_object] = []
            changes_by_object[config_object].append(change)
        
        # Display each config object's changes in diff style
        for config_object, object_changes in changes_by_object.items():
            console.print(f"\n[cyan]--- {config_object}[/cyan]")
            console.print(f"[cyan]+++ {config_object} (proposed)[/cyan]")
            
            for change in object_changes:
                if change.change_type == "modified":
                    console.print(f"[red]- {change.path}: {change.old_value}[/red]")
                    console.print(f"[green]+ {change.path}: {change.new_value}[/green]")
                elif change.change_type == "added":
                    console.print(f"[green]+ {change.path}: {change.new_value}[/green]")
                elif change.change_type == "deleted":
                    console.print(f"[red]- {change.path}: {change.old_value}[/red]")
    
    # Dependencies table with meaningful object names
    if dependencies:
        console.print(f"\n[bold blue]Configuration Dependencies:[/bold blue]")
        deps_table = Table(show_header=True, header_style="bold magenta")
        deps_table.add_column("Config Type", style="magenta") # New column
        deps_table.add_column("Source", style="cyan")
        deps_table.add_column("Target", style="green") 
        deps_table.add_column("Type", style="yellow")
        
        if detailed:
            deps_table.add_column("Description", style="white")
        
        for dep in dependencies:
            if detailed:
                deps_table.add_row(
                    dep.config_object_type, # New field
                    dep.display_source, # Use new display field
                    dep.display_target, # Use new display field
                    dep.dependency_type,
                    dep.description or "No description"
                )
            else:
                deps_table.add_row(
                    dep.config_object_type, # New field
                    dep.display_source, # Use new display field
                    dep.display_target, # Use new display field
                    dep.dependency_type
                )
        
        console.print(deps_table)
    
    # Impact Analysis per changed config object
    if impact_analysis and impact_analysis['object_impacts']:
        console.print(f"\n[bold blue]Configuration Impact Analysis:[/bold blue]")
        console.print("[dim]For each changed configuration object → impacted components:[/dim]")
        
        for config_object, impacts in impact_analysis['object_impacts'].items():
            if impacts:
                console.print(f"\n[bold cyan]{config_object}[/bold cyan]")
                console.print(f"  [yellow]Changes:[/yellow] {impacts['change_count']} modifications")
                
                if impacts['dependencies'] or impacts.get('all_identifiers'):
                    console.print(f"  [red]Impacts:[/red]")
                    
                    # Use the combined identifiers from impact analysis
                    all_identifiers = impacts.get('all_identifiers', [])
                    
                    # Display all meaningful identifiers
                    if all_identifiers:
                        for identifier in all_identifiers:
                            console.print(f"    • {identifier}")
                    else:
                        console.print(f"    • Schema references detected but no specific identifiers extracted")
                else:
                    console.print(f"  [green]No downstream dependencies found[/green]")
    
    # Section summaries if detailed
    if detailed:
        if change_summary['changes_by_section']:
            console.print(f"\n[bold blue]Changes by Section:[/bold blue]")
            for section, section_changes in change_summary['changes_by_section'].items():
                console.print(f"  [cyan]{section}:[/cyan] {len(section_changes)} changes")
        
        if dependency_summary['by_source_section']:
            console.print(f"\n[bold blue]Dependencies by Section:[/bold blue]")
            for section, deps in dependency_summary['by_source_section'].items():
                console.print(f"  [cyan]{section}:[/cyan] {len(deps)} dependencies")


def _extract_config_object_name(path: str) -> str:
    """
    Extract meaningful configuration object name from path.
    Args: path string to extract object name from.
    Returns: Human-readable configuration object name.
    """
    # Handle special case for device info
    if path == "device":
        return "Device Information"
    
    # Extract the main configuration section
    parts = path.split('/')
    if len(parts) >= 1:
        main_section = parts[0]
        
        # Clean up OpenConfig module prefixes
        if ':' in main_section:
            main_section = main_section.split(':')[1]
        
        # Handle specific patterns
        if 'network-instance' in main_section:
            return "BGP Configuration"
        elif 'acl' in main_section:
            return "Access Control Lists"
        elif 'vlan' in main_section:
            return "VLAN Configuration"  
        elif 'interface' in main_section:
            return "Interface Configuration"
        else:
            # Capitalize and clean up
            return main_section.replace('-', ' ').title()
    
    return "Configuration"


def _analyze_per_object_impact(changes: List[ConfigChange], dependencies: List[Dependency], current_config: Dict) -> Dict[str, Any]:
    """
    Analyze the impact of each changed configuration object on other components.
    Args: changes list, dependencies list, and current_config for resolving impacts.
    Returns: Dictionary with per-object impact analysis.
    """
    # Group changes by configuration object
    changes_by_object = {}
    for change in changes:
        config_object = _extract_config_object_name(change.path)
        if config_object not in changes_by_object:
            changes_by_object[config_object] = []
        changes_by_object[config_object].append(change)
    
    # Map dependencies to their source configuration objects
    object_impacts = {}
    for config_object, object_changes in changes_by_object.items():
        # Find dependencies that originate from this config object's changes
        object_dependencies = []
        for change in object_changes:
            for dep in dependencies:
                # Check if this dependency relates to the changed path
                if _path_relates_to_change(dep.source_path, change.path):
                    object_dependencies.append(dep)
        
        # Extract ALL identifiers from configuration changes (what's being changed)
        changed_identifiers = []
        for change in object_changes:
            # Extract ALL bracketed identifiers from change path
            parts = change.path.split('/')
            for part in parts:
                if '[' in part and ']' in part:
                    start = part.find('[') + 1
                    end = part.find(']')
                    if start < end:
                        identifier = part[start:end]
                        if identifier not in changed_identifiers and not identifier.isdigit():
                            changed_identifiers.append(identifier)
        
        # Resolve impacted identifiers from schema dependencies (what's being impacted)
        impacted_identifiers = []
        for dep in object_dependencies:
            # Use the display_target which has resolved interface names
            if hasattr(dep, 'display_target') and dep.display_target and dep.display_target != dep.target_path:
                # If we have a resolved display_target, use it
                target_names = [name.strip() for name in dep.display_target.split(',')]
                for name in target_names:
                    if name and name not in changed_identifiers and name not in impacted_identifiers:
                        impacted_identifiers.append(name)
            else:
                # Fallback to old method
                resolved_identifiers = _resolve_dependency_target_identifiers(dep, current_config)
                for identifier in resolved_identifiers:
                    if identifier not in changed_identifiers and identifier not in impacted_identifiers:
                        impacted_identifiers.append(identifier)
        
        # Combine all identifiers
        all_identifiers = changed_identifiers + impacted_identifiers
        
        # Deduplicate dependencies by target_path + source_value combination
        unique_dependencies = []
        seen = set()
        for dep in object_dependencies:
            key = (dep.target_path, dep.source_value)
            if key not in seen:
                seen.add(key)
                unique_dependencies.append(dep)
        
        object_impacts[config_object] = {
            'change_count': len(object_changes),
            'dependencies': unique_dependencies,
            'all_identifiers': all_identifiers
        }
    
    return {
        'object_impacts': object_impacts,
        'total_objects_changed': len(changes_by_object),
        'total_objects_with_impacts': sum(1 for impacts in object_impacts.values() if impacts['dependencies'])
    }


def _path_relates_to_change(dependency_path: str, change_path: str) -> bool:
    """
    Check if a dependency path relates to a configuration change path.
    Since the schema analyzer now does semantic matching, we can use simpler logic.
    Args: dependency_path and change_path to compare.
    Returns: True if paths are related.
    """
    # Extract the main configuration object identifiers from both paths
    dep_object = _extract_config_object_identifier(dependency_path)
    change_object = _extract_config_object_identifier(change_path)
    
    # If we can identify the objects and they match, they're related
    if dep_object and change_object:
        return dep_object == change_object
    
    # Fallback to simpler path matching
    dep_parts = dependency_path.split('/')
    change_parts = change_path.split('/')
    
    # Check if change path is a subset or parent of dependency path
    for i in range(min(len(change_parts), len(dep_parts))):
        if change_parts[i] in dep_parts[i]:
            return True
    
    return False


def _extract_config_object_identifier(path: str) -> Optional[str]:
    """
    Extract configuration object identifier from path for relationship matching.
    Args: path to extract identifier from.
    Returns: Object identifier or None.
    """
    path_parts = path.split('/')
    
    # Look for list keys in brackets
    for part in path_parts:
        if '[' in part and ']' in part:
            start = part.find('[') + 1
            end = part.find(']')
            if start < end:
                return part[start:end]
    
    return None


def _get_object_at_path(config: Dict, path: str):
    """
    Generically retrieves an object from a config dictionary given a YANG-like path.
    Handles lists with keys in brackets (e.g., interface[name='Ethernet1']).
    """
    current_obj = config
    path_parts = path.strip('/').split('/')

    for part in path_parts:
        if not current_obj:
            return None

        # Handle module prefixes (e.g., openconfig-interfaces:interfaces)
        if ':' in part:
            part = part.split(':')[-1]

        # Handle list keys (e.g., interface[name='Ethernet1'])
        if '[' in part and ']' in part:
            list_name = part.split('[')[0]
            key_part = part[part.find('[') + 1 : part.find(']')]
            
            key_field = None
            key_value = None
            if '=' in key_part:
                key_field, key_value = key_part.split('=', 1)
                key_value = key_value.strip("'\"") # Remove quotes
            else:
                key_field = 'name' # Common default for list keys
                key_value = key_part

            if list_name in current_obj and isinstance(current_obj[list_name], list):
                found_item = None
                for item in current_obj[list_name]:
                    if isinstance(item, dict) and key_field in item and str(item[key_field]) == key_value:
                        found_item = item
                        break
                current_obj = found_item
            else:
                return None # List not found or not a list
        else:
            # Regular dictionary key
            if part in current_obj:
                current_obj = current_obj[part]
            else:
                return None # Part not found

    return current_obj


def _extract_identifiers_from_object(obj):
    """
    Helper to extract common identifiers from a single dictionary object.
    """
    obj_identifiers = []
    if isinstance(obj, dict):
        for field in ['name', 'id', 'vlan-id', 'sequence-id', 'interface-id', 'set-name']:
            if field in obj and obj[field]:
                identifier = str(obj[field])
                if not identifier.isdigit(): # Skip numeric identifiers
                    obj_identifiers.append(identifier)
    return obj_identifiers


def _resolve_dependency_target_identifiers_from_current_config(dep: Dependency, current_config: Dict) -> List[str]:
    """
    Resolve actual impacted identifiers from dependency target paths.
    Uses generic path resolution and config searching to find actual object names.
    """
    identifiers = []

    # 1. Try to extract identifiers directly from the target_path (most generic and direct)
    extracted_from_path = _extract_identifier_from_path(dep.target_path)
    if extracted_from_path and extracted_from_path not in identifiers:
        identifiers.append(extracted_from_path)

    # 2. If no identifier found from path, try to resolve the target_path in current_config
    #    and then extract identifiers from the resolved object.
    if not identifiers:
        target_object = _get_object_at_path(current_config, dep.target_path)
        if target_object:
            resolved_obj_identifiers = _extract_identifiers_from_object(target_object)
            for identifier in resolved_obj_identifiers:
                if identifier not in identifiers:
                    identifiers.append(identifier)
    
    # 3. As fallback, search for interfaces that reference this ACL (generic pattern matching)
    if not identifiers and "acl" in dep.source_path.lower():
        acl_name = dep.source_value
        if acl_name and "openconfig-interfaces:interfaces" in current_config:
            interfaces = current_config["openconfig-interfaces:interfaces"].get("interface", [])
            for iface in interfaces:
                if "name" in iface:
                    # Check if interface has ACL applied (generic pattern)
                    if _interface_references_acl(iface, acl_name):
                        if iface["name"] not in identifiers:
                            identifiers.append(iface["name"])
    
    return identifiers


def _interface_references_acl(interface_config: Dict, acl_name: str) -> bool:
    """
    Generic check if interface configuration references an ACL.
    Searches through interface structure for ACL references.
    """
    # Look for ACL references in interface config
    if "openconfig-acl:acl" in interface_config:
        acl_config = interface_config["openconfig-acl:acl"]
        
        # Check ingress ACL sets
        if "ingress-acl-sets" in acl_config:
            ingress_sets = acl_config["ingress-acl-sets"].get("ingress-acl-set", [])
            for acl_set in ingress_sets:
                if acl_set.get("set-name") == acl_name:
                    return True
        
        # Check egress ACL sets
        if "egress-acl-sets" in acl_config:
            egress_sets = acl_config["egress-acl-sets"].get("egress-acl-set", [])
            for acl_set in egress_sets:
                if acl_set.get("set-name") == acl_name:
                    return True
                    
    return False


def _resolve_dependency_target_identifiers(dep: Dependency, current_config: Dict) -> List[str]:
    """
    Resolve actual impacted identifiers from dependency target paths.
    Only returns identifiers that are truly referenced by the dependency relationship.
    Generic approach that validates actual references rather than blanket searching.
    """
    identifiers = []
    
    # For schema leafref dependencies, we need to find what actually references the changed object
    if dep.dependency_type == "schema_leafref":
        # Get the object that was changed (source)
        changed_identifier = _extract_identifier_from_path(dep.source_path)
        if changed_identifier:
            # Always include the changed object itself
            identifiers.append(changed_identifier)
    
    # Include the source object identifier  
    source_identifier = _extract_identifier_from_path(dep.source_path)
    if source_identifier and source_identifier not in identifiers:
        identifiers.append(source_identifier)
    
    return identifiers


def _extract_identifier_from_path(path: str) -> str:
    """
    Extract actual object identifier from path.
    Args: path like "openconfig-acl:acl/acl-sets/acl-set[USER_INBOUND_V4]/config/name"
    Returns: Object name like "USER_INBOUND_V4"
    """
    # Look for bracketed identifiers in the path
    parts = path.split('/')
    for part in parts:
        if '[' in part and ']' in part:
            start = part.find('[') + 1
            end = part.find(']')
            if start < end:
                identifier = part[start:end]
                # Skip numeric identifiers (sequence numbers)
                return identifier
    return ""


def _display_json_results(changes: List[ConfigChange], dependencies: List[Dependency],
                         change_summary: Dict[str, Any], dependency_summary: Dict[str, Any],
                         impact_analysis: Dict[str, Any]):
    """Display results in JSON format."""
    result = {
        "summary": {
            "changes": change_summary,
            "dependencies": dependency_summary,
            "impact_analysis": impact_analysis
        },
        "changes": [
            {
                "path": change.path,
                "type": change.change_type,
                "old_value": change.old_value,
                "new_value": change.new_value,
                "description": change.description
            }
            for change in changes
        ],
        "dependencies": [
            {
                "source_path": dep.source_path,
                "target_path": dep.target_path,
                "dependency_type": dep.dependency_type,
                "source_value": dep.source_value,
                "target_object": dep.target_object,
                "description": dep.description
            }
            for dep in dependencies
        ]
    }
    
    console.print(json.dumps(result, indent=2))


# ==================== NEO4J GRAPH DATABASE INTEGRATION ====================

try:
    # Handle both relative and absolute imports for simplified graph commands
    try:
        from .simple_graph_commands import register_simple_graph_commands
    except ImportError:
        from simple_graph_commands import register_simple_graph_commands
    
    # Register Neo4j graph database commands
    register_simple_graph_commands(cli)
    
    # Register enhanced multi-device analysis
    try:
        try:
            from .enhanced_analysis import register_enhanced_analysis_commands
        except ImportError:
            from enhanced_analysis import register_enhanced_analysis_commands
        
        register_enhanced_analysis_commands(cli)
        print("✅ Enhanced multi-device analysis commands loaded", file=sys.stderr)
        
    except ImportError as e:
        print(f"⚠️ Warning: Enhanced analysis not available: {e}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Error loading enhanced analysis: {e}", file=sys.stderr)
    
    import sys
    print("✅ Neo4j graph database commands loaded successfully", file=sys.stderr)
    
except ImportError as e:
    import sys
    print(f"⚠️ Warning: Neo4j graph commands not available: {e}", file=sys.stderr)
    print("   Run with --verbose for more details", file=sys.stderr)
except Exception as e:
    import sys
    print(f"❌ Error loading graph commands: {e}", file=sys.stderr)


if __name__ == '__main__':
    cli()