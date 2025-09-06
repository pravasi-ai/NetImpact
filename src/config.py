"""
Configuration management for the Network Configuration Impact Analysis Platform.
Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration loaded from environment variables.
    Provides centralized access to all configurable settings.
    """

    def __init__(self):
        """
        Initialize configuration with environment variables and defaults.
        """
        self._load_config()

    def _load_config(self):
        """
        Load all configuration values from environment with defaults.
        """
        # Neo4j Database Configuration
        self.NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7688')
        self.NEO4J_USERNAME = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'netopo123')
        self.NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
        self.NEO4J_WEB_URI = os.getenv('NEO4J_WEB_URI', 'http://localhost:7475')

        # Application Configuration
        self.APP_NAME = os.getenv('APP_NAME', 'netopo-analysis-platform')
        self.APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
        self.APP_ENV = os.getenv('APP_ENV', 'development')

        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'logs/netopo.log')

        # Data Paths
        self.DATA_CONFIGS_PATH = Path(os.getenv('DATA_CONFIGS_PATH', './data/configs'))
        self.DATA_INVENTORY_PATH = Path(os.getenv('DATA_INVENTORY_PATH', './data/inventory/inventory.csv'))
        self.DATA_TOPOLOGY_PATH = Path(os.getenv('DATA_TOPOLOGY_PATH', './data/topology'))
        self.YANG_MODELS_PATH = Path(os.getenv('YANG_MODELS_PATH', './models/yang'))

        # Performance Settings
        self.MAX_CONCURRENT_LOADS = int(os.getenv('MAX_CONCURRENT_LOADS', '5'))
        self.GRAPH_BATCH_SIZE = int(os.getenv('GRAPH_BATCH_SIZE', '100'))
        self.CACHE_TTL_SECONDS = int(os.getenv('CACHE_TTL_SECONDS', '3600'))

        # Development Settings
        self.DEBUG_MODE = os.getenv('DEBUG_MODE', 'true').lower() == 'true'
        self.ENABLE_QUERY_LOGGING = os.getenv('ENABLE_QUERY_LOGGING', 'false').lower() == 'true'

    @property
    def is_development(self) -> bool:
        """
        Check if application is running in development mode.
        Returns: True if in development environment.
        """
        return self.APP_ENV.lower() == 'development'

    @property
    def is_production(self) -> bool:
        """
        Check if application is running in production mode.
        Returns: True if in production environment.
        """
        return self.APP_ENV.lower() == 'production'

    def get_neo4j_config(self) -> dict:
        """
        Get Neo4j connection configuration as dictionary.
        Returns: Dict with Neo4j connection parameters.
        """
        return {
            'uri': self.NEO4J_URI,
            'username': self.NEO4J_USERNAME,
            'password': self.NEO4J_PASSWORD,
            'database': self.NEO4J_DATABASE
        }

    def validate_config(self) -> list:
        """
        Validate configuration and return any errors found.
        Returns: List of validation error messages.
        """
        errors = []

        # Check required paths exist
        if not self.DATA_CONFIGS_PATH.exists():
            errors.append(f"Data configs path does not exist: {self.DATA_CONFIGS_PATH}")
        
        if not self.DATA_INVENTORY_PATH.exists():
            errors.append(f"Inventory file does not exist: {self.DATA_INVENTORY_PATH}")
        
        if not self.YANG_MODELS_PATH.exists():
            errors.append(f"YANG models path does not exist: {self.YANG_MODELS_PATH}")

        # Validate numeric settings
        if self.MAX_CONCURRENT_LOADS <= 0:
            errors.append("MAX_CONCURRENT_LOADS must be positive")
        
        if self.GRAPH_BATCH_SIZE <= 0:
            errors.append("GRAPH_BATCH_SIZE must be positive")

        # Validate Neo4j URI format
        if not (self.NEO4J_URI.startswith('bolt://') or self.NEO4J_URI.startswith('neo4j://')):
            errors.append("NEO4J_URI must start with 'bolt://' or 'neo4j://'")

        return errors

    def create_log_directory(self):
        """
        Create log directory if it doesn't exist.
        """
        log_path = Path(self.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def __str__(self) -> str:
        """
        Return string representation of configuration (excluding sensitive data).
        """
        return f"""Configuration:
  App: {self.APP_NAME} v{self.APP_VERSION} ({self.APP_ENV})
  Neo4j: {self.NEO4J_URI} (user: {self.NEO4J_USERNAME})
  Paths:
    Configs: {self.DATA_CONFIGS_PATH}
    Inventory: {self.DATA_INVENTORY_PATH}
    YANG Models: {self.YANG_MODELS_PATH}
  Performance:
    Max Concurrent: {self.MAX_CONCURRENT_LOADS}
    Batch Size: {self.GRAPH_BATCH_SIZE}
  Debug: {self.DEBUG_MODE}"""


# Global configuration instance
config = Config()