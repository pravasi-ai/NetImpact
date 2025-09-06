import yaml
from pathlib import Path
from ciscoconfparse2 import CiscoConfParse
import logging
import re
from typing import Dict, Any, List, Optional

class ConfigTextParser:
    """
    Parses raw text configurations using a rules-driven engine based on YAML files.
    """
    def __init__(self, os_type: str):
        self.os_type = os_type
        self.logger = logging.getLogger(__name__)
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        """Loads the appropriate YAML rule file based on the OS type."""
        rules_dir = Path(__file__).parent / 'rules'
        rules_file = rules_dir / f"{self.os_type}.yml"
        if not rules_file.exists():
            self.logger.error(f"No parsing rule file found for OS type: {self.os_type}")
            raise FileNotFoundError(f"Rule file not found: {rules_file}")
        
        with open(rules_file, 'r') as f:
            self.logger.info(f"Loading parsing rules from {rules_file}")
            return yaml.safe_load(f)

    def parse_config(self, config_text: str) -> Dict[str, Any]:
        """
        Parses the full configuration text and extracts all features defined in the rules.
        """
        if not self.rules:
            return {}

        syntax_map = {
            'cisco_ios': 'ios',
            'cisco_ios-xe': 'ios',
            'arista_eos': 'ios'
        }
        parser_syntax = syntax_map.get(self.os_type, 'ios')

        parsed_data = {}
        p = CiscoConfParse(config_text.splitlines(), syntax=parser_syntax)

        for feature, rules in self.rules.get('features', {}).items():
            handler = getattr(self, f"_parse_{feature}", self._parse_generic_feature)
            parsed_data[feature] = handler(p, rules)
        
        return parsed_data

    def _parse_generic_feature(self, parser: CiscoConfParse, rules: List[Dict]) -> List[Any]:
        """A generic parser for simple, top-level features."""
        results = []
        for rule in rules:
            pattern = rule.get('pattern')
            if pattern:
                matches = parser.find_objects(pattern)
                for match in matches:
                    re_match = re.search(pattern, match.text)
                    if re_match:
                        if re_match.groupdict():
                            results.append(re_match.groupdict())
                        else:
                            results.append(re_match.groups())
        return results

    def _parse_feature_with_children(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        """A generic parser for parent-child block features like interfaces, vlans, etc."""
        data = {}
        rule = rules[0]
        parent_pattern = rule['parent']
        child_map = rule['child_map']

        parent_blocks = parser.find_objects(parent_pattern)

        for block in parent_blocks:
            try:
                identifier = block.re_match_typed(parent_pattern)
                if isinstance(identifier, tuple):
                    identifier = identifier[0]

                config = {'name': identifier}

                for key, patterns in child_map.items():
                    for pattern_rule in patterns:
                        pattern = pattern_rule['pattern']
                        rule_type = pattern_rule.get('type', 'value_extraction')

                        if rule_type == 'presence':
                            if block.re_search_children(pattern):
                                config[key] = True
                                break
                        else:  # value_extraction
                            values = []
                            for child_line in block.children:
                                match = re.search(pattern, child_line.text)
                                if match:
                                    groups = match.groups()
                                    if len(groups) > 1:
                                        values.append(groups)
                                    elif len(groups) == 1:
                                        values.append(groups[0])
                            
                            if len(values) > 0:
                                    config[key] = values
                data[identifier] = config
            except (ValueError, TypeError) as e:
                self.logger.warning(f"Could not parse block for pattern {parent_pattern}: {e}")
        return data

    def _parse_interfaces(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        return self._parse_feature_with_children(parser, rules)

    def _parse_vlans(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        return self._parse_feature_with_children(parser, rules)

    def _parse_ospf(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        return self._parse_feature_with_children(parser, rules)

    def _parse_bgp(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        return self._parse_feature_with_children(parser, rules)

    def _parse_acls(self, parser: CiscoConfParse, rules: List[Dict]) -> Dict[str, Any]:
        """Custom parser for Access Control Lists."""
        acl_data = {}
        rule = rules[0]
        parent_pattern = rule['parent']
        rule_patterns = rule['child_map']['rule']

        acl_blocks = parser.find_objects(parent_pattern)

        for block in acl_blocks:
            try:
                match = re.search(parent_pattern, block.text)
                if not match:
                    continue
                
                groups = match.groups()
                acl_name = groups[-1]
                acl_config = {}
                if len(groups) > 1:
                    acl_config['type'] = groups[0].upper()

                rules_config = []
                for child_line in block.children: # Iterate through children lines
                    for pattern_rule in rule_patterns:
                        pattern = pattern_rule['pattern']
                        rule_match = re.search(pattern, child_line.text)
                        if rule_match:
                            rules_config.append(rule_match.groups()) # Append all captured groups
                            break # Move to next child_line after first match
                
                acl_config['rules'] = rules_config
                acl_data[acl_name] = acl_config
            except (ValueError, TypeError, IndexError) as e:
                self.logger.warning(f"Could not parse ACL block for pattern {parent_pattern}: {e}")
        return acl_data