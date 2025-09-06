from .base_loader import BaseLoader
from parsing.text_parser import ConfigTextParser
from parsing.config_transformer import YangTransformer
import logging

class TextLoader(BaseLoader):
    """
    Loads configuration from a raw text file by parsing it and transforming it
    to a YANG-modeled JSON structure.
    """

    def __init__(self, yang_validator, device_info: dict):
        super().__init__(yang_validator, device_info)
        self.logger = logging.getLogger(__name__)
        self.os_type = self.device_info.get('os_type', 'cisco_ios')
        self.parser = ConfigTextParser(os_type=self.os_type)
        self.transformer = YangTransformer()

    def load_structured_data(self, file_path: str) -> dict:
        """
        Loads and parses a raw text configuration file.
        """
        self.logger.info(f"Loading text config file: {file_path} for OS: {self.os_type}")
        with open(file_path, 'r') as f:
            config_text = f.read()

        self.logger.info("Parsing text configuration...")
        parsed_data = self.parser.parse_config(config_text)
        if not parsed_data:
            self.logger.error("Parsing failed to produce data.")
            raise ValueError("Configuration parsing resulted in empty data.")
        return parsed_data

    def build_composite_model(self, structured_data: dict) -> dict:
        """
        Transforms the parsed data into the target YANG model (OpenConfig).
        """
        self.logger.info("Transforming parsed data to YANG model...")
        yang_data = self.transformer.transform(structured_data, self.os_type)
        if not yang_data:
            self.logger.error("Transformation failed to produce data.")
            raise ValueError("YANG transformation resulted in empty data.")
        return yang_data
