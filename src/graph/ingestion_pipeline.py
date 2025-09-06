"""
Graph ingestion pipeline orchestrator for complete data flow management.
Coordinates device configuration loading, topology ingestion, and graph population.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
from datetime import datetime
import concurrent.futures
import sys

# Add project root to Python path for proper imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.config import config
from src.loaders import ConfigFileScanner, LoaderFactory
from .graph_schema import GraphSchema
from .graph_modeler import GraphModeler
from .topology_loader import TopologyLoader


class GraphIngestionPipeline:
    """
    Orchestrates complete data ingestion pipeline from files to Neo4j.
    Manages device configurations, topology data, and graph relationships.
    """

    def __init__(self):
        """
        Initialize pipeline with all required components.
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize graph components
        self.graph_schema = GraphSchema.from_config()
        self.graph_modeler = GraphModeler(self.graph_schema)
        self.topology_loader = TopologyLoader(self.graph_schema)
        
        # Initialize data loading components
        self.file_scanner = ConfigFileScanner(
            config.DATA_CONFIGS_PATH,
            config.DATA_INVENTORY_PATH
        )
        self.loader_factory = LoaderFactory(config.YANG_MODELS_PATH)
        
        # Pipeline state
        self.pipeline_stats = {
            'started_at': None,
            'completed_at': None,
            'devices_processed': 0,
            'topology_files_processed': 0,
            'total_nodes_created': 0,
            'errors': []
        }

    def run_complete_ingestion(self) -> Dict[str, Any]:
        """
        Execute complete ingestion pipeline from configuration files to graph.
        Returns: Comprehensive results summary of entire pipeline execution.
        """
        self.pipeline_stats['started_at'] = datetime.now()
        self.logger.info("🚀 Starting complete graph ingestion pipeline")
        
        try:
            # Step 1: Initialize graph schema
            schema_results = self._initialize_graph_schema()
            
            # Step 2: Ingest device configurations
            device_results = self._ingest_device_configurations()
            
            # Step 3: Load topology data
            topology_results = self._ingest_topology_data()
            
            # Step 4: Generate visualization layout (sample data)
            layout_results = self._create_sample_layout()
            
            # Compile final results
            final_results = self._compile_pipeline_results(
                schema_results, device_results, topology_results, layout_results
            )
            
            self.pipeline_stats['completed_at'] = datetime.now()
            self.logger.info("✅ Graph ingestion pipeline completed successfully")
            
            return final_results
            
        except Exception as e:
            self.pipeline_stats['errors'].append(str(e))
            self.logger.error(f"❌ Pipeline failed: {e}")
            raise

    def _initialize_graph_schema(self) -> Dict[str, Any]:
        """
        Initialize Neo4j graph schema with constraints and indexes.
        Returns: Schema initialization results.
        """
        self.logger.info("Initializing graph schema...")
        
        try:
            self.graph_schema.initialize_schema()
            
            return {
                'status': 'success',
                'constraints_created': True,
                'indexes_created': True
            }
        except Exception as e:
            self.logger.error(f"Schema initialization failed: {e}")
            raise

    def _ingest_device_configurations(self) -> Dict[str, Any]:
        """
        Ingest all device configurations using Phase 1 loaders.
        Returns: Device ingestion results with statistics.
        """
        self.logger.info("Ingesting device configurations...")
        
        # Discover configuration files
        discovered_files = self.file_scanner.discover_config_files()
        self.logger.info(f"Found {len(discovered_files)} device configurations")
        
        device_results = []
        total_nodes_created = 0
        
        # Process configurations sequentially for now (can be parallelized later)
        for file_mapping in discovered_files:
            try:
                device_result = self._process_single_device(file_mapping)
                device_results.append(device_result)
                total_nodes_created += device_result.get('total_nodes_created', 0)
                self.pipeline_stats['devices_processed'] += 1
                
            except Exception as e:
                error_msg = f"Failed to process {file_mapping['hostname']}: {e}"
                self.logger.error(error_msg)
                self.pipeline_stats['errors'].append(error_msg)
        
        return {
            'devices_processed': len(device_results),
            'total_nodes_created': total_nodes_created,
            'device_results': device_results,
            'errors': [e for e in self.pipeline_stats['errors'] if 'Failed to process' in e]
        }

    def _process_single_device(self, file_mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single device configuration through loader and modeler.
        Args: file_mapping from ConfigFileScanner with device details.
        Returns: Device processing results.
        """
        hostname = file_mapping['hostname']
        file_path = file_mapping['file_path']
        device_info = file_mapping['device_info']
        
        self.logger.info(f"Processing device: {hostname}")
        
        # Create appropriate loader for device
        loader = self.loader_factory.create_loader(device_info)
        
        # Load and validate configuration
        validated_data = loader.load_and_validate(file_path)
        
        # Transform to graph nodes
        ingestion_summary = self.graph_modeler.ingest_device_configuration(validated_data)
        
        self.logger.info(f"✅ Processed {hostname}: {ingestion_summary.get('total_nodes_created', 0)} nodes")
        return ingestion_summary

    def _ingest_topology_data(self) -> Dict[str, Any]:
        """
        Ingest topology data from LLDP and BGP neighbor files.
        Returns: Topology ingestion results.
        """
        self.logger.info("Ingesting network topology data...")
        
        try:
            topology_results = self.topology_loader.load_all_topology_files(config.DATA_TOPOLOGY_PATH)
            self.pipeline_stats['topology_files_processed'] = topology_results.get('files_processed', 0)
            
            self.logger.info(f"✅ Topology ingestion: {topology_results.get('total_connections', 0)} connections")
            return topology_results
            
        except Exception as e:
            self.logger.error(f"Topology ingestion failed: {e}")
            return {
                'files_processed': 0,
                'total_connections': 0,
                'errors': [str(e)]
            }

    def _create_sample_layout(self) -> Dict[str, Any]:
        """
        Create sample site and device layout data for visualization.
        Returns: Layout creation results.
        """
        self.logger.info("Creating sample network layout...")
        
        # Sample site data for our 5 devices
        sample_sites = [
            {
                'site_id': 'site_hq_datacenter',
                'name': 'HQ Datacenter',
                'type': 'datacenter',
                'address': '123 Main St, Tech City',
                'coordinates': '37.7749,-122.4194',
                'devices': [
                    {
                        'hostname': 'core-sw-01',
                        'x_position': 200.0,
                        'y_position': 100.0,
                        'layer': 'core',
                        'icon_type': 'switch',
                        'rack_name': 'Rack-A1',
                        'status_color': 'green'
                    },
                    {
                        'hostname': 'core-sw-02',
                        'x_position': 400.0,
                        'y_position': 100.0,
                        'layer': 'core',
                        'icon_type': 'switch',
                        'rack_name': 'Rack-A2',
                        'status_color': 'green'
                    },
                    {
                        'hostname': 'dist-rtr-01',
                        'x_position': 150.0,
                        'y_position': 250.0,
                        'layer': 'distribution',
                        'icon_type': 'router',
                        'rack_name': 'Rack-B1',
                        'status_color': 'green'
                    },
                    {
                        'hostname': 'dist-sw-02',
                        'x_position': 450.0,
                        'y_position': 250.0,
                        'layer': 'distribution',
                        'icon_type': 'switch',
                        'rack_name': 'Rack-B2',
                        'status_color': 'green'
                    },
                    {
                        'hostname': 'acc-sw-01',
                        'x_position': 300.0,
                        'y_position': 400.0,
                        'layer': 'access',
                        'icon_type': 'switch',
                        'rack_name': 'Rack-C1',
                        'status_color': 'green'
                    }
                ]
            }
        ]
        
        try:
            layout_results = self.topology_loader.create_site_topology(sample_sites)
            self.logger.info(f"✅ Layout creation: {layout_results.get('sites_created', 0)} sites, {layout_results.get('device_locations_created', 0)} device locations")
            return layout_results
            
        except Exception as e:
            self.logger.error(f"Layout creation failed: {e}")
            return {
                'sites_created': 0,
                'device_locations_created': 0,
                'errors': [str(e)]
            }

    def _compile_pipeline_results(self, schema_results: Dict, device_results: Dict, 
                                topology_results: Dict, layout_results: Dict) -> Dict[str, Any]:
        """
        Compile final pipeline results with comprehensive statistics.
        Args: Results from each pipeline stage.
        Returns: Complete pipeline execution summary.
        """
        duration = 0.0
        if self.pipeline_stats['started_at'] and self.pipeline_stats['completed_at']:
            duration = (self.pipeline_stats['completed_at'] - self.pipeline_stats['started_at']).total_seconds()
        elif self.pipeline_stats['started_at']:
            duration = (datetime.now() - self.pipeline_stats['started_at']).total_seconds()
        
        # Get final graph statistics
        graph_summary = self.graph_schema.get_schema_summary()
        topology_summary = self.topology_loader.get_topology_summary()
        
        return {
            'pipeline_execution': {
                'started_at': self.pipeline_stats['started_at'].isoformat() if self.pipeline_stats['started_at'] else None,
                'completed_at': self.pipeline_stats['completed_at'].isoformat() if self.pipeline_stats['completed_at'] else None,
                'duration_seconds': duration,
                'status': 'success' if not self.pipeline_stats['errors'] else 'partial_success'
            },
            'ingestion_summary': {
                'devices_processed': device_results.get('devices_processed', 0),
                'topology_files_processed': topology_results.get('files_processed', 0),
                'total_nodes_created': device_results.get('total_nodes_created', 0),
                'total_connections_created': topology_results.get('total_connections', 0),
                'sites_created': layout_results.get('sites_created', 0)
            },
            'graph_statistics': graph_summary,
            'topology_statistics': topology_summary,
            'stage_results': {
                'schema_initialization': schema_results,
                'device_ingestion': device_results,
                'topology_ingestion': topology_results,
                'layout_creation': layout_results
            },
            'errors': self.pipeline_stats['errors']
        }

    def run_incremental_update(self, device_hostname: str) -> Dict[str, Any]:
        """
        Run incremental update for single device configuration.
        Args: device_hostname to update in graph.
        Returns: Incremental update results.
        """
        self.logger.info(f"Running incremental update for {device_hostname}")
        
        try:
            # Find device file
            discovered_files = self.file_scanner.discover_config_files()
            device_file = next(
                (f for f in discovered_files if f['hostname'] == device_hostname), 
                None
            )
            
            if not device_file:
                raise ValueError(f"Device {device_hostname} not found in configurations")
            
            # Process single device
            result = self._process_single_device(device_file)
            
            self.logger.info(f"✅ Incremental update completed for {device_hostname}")
            return {
                'device': device_hostname,
                'status': 'success',
                'nodes_created': result.get('total_nodes_created', 0),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Incremental update failed for {device_hostname}: {e}")
            return {
                'device': device_hostname,
                'status': 'failed',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get current pipeline status and statistics.
        Returns: Pipeline status information.
        """
        graph_stats = self.graph_schema.get_schema_summary()
        topology_stats = self.topology_loader.get_topology_summary()
        
        return {
            'pipeline_stats': self.pipeline_stats,
            'graph_statistics': graph_stats,
            'topology_statistics': topology_stats,
            'configuration': {
                'configs_path': str(config.DATA_CONFIGS_PATH),
                'topology_path': str(config.DATA_TOPOLOGY_PATH),
                'yang_models_path': str(config.YANG_MODELS_PATH),
                'neo4j_uri': config.NEO4J_URI
            }
        }

    def cleanup(self):
        """
        Clean up pipeline resources and close connections.
        """
        if self.graph_schema:
            self.graph_schema.close()
        self.logger.info("Pipeline cleanup completed")