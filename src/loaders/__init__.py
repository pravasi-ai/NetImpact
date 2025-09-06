"""
Loader package for vendor-specific configuration parsing.
Implements pluggable architecture with 4-step loading process.
"""

from .base_loader import BaseLoader
from .cisco_ios import CiscoIosLoader
from .arista_eos import AristaEosLoader
from .file_scanner import ConfigFileScanner
from .loader_factory import LoaderFactory

__all__ = [
    'BaseLoader',
    'CiscoIosLoader', 
    'AristaEosLoader',
    'ConfigFileScanner',
    'LoaderFactory'
]