#!/usr/bin/env python3
"""
Detailed analysis of text configuration parsing to identify any missing or incorrectly mapped config objects.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from parsing.text_parser import ConfigTextParser
from parsing.config_transformer import YangTransformer

def analyze_cisco_ios_gaps():
    """Analyze Cisco IOS configuration for parsing gaps."""
    print("🔍 DETAILED CISCO IOS ANALYSIS")
    print("=" * 60)
    
    # Load config
    with open("tests/proposed-cisco-ios.txt", 'r') as f:
        config_lines = f.read().splitlines()
    
    parser = ConfigTextParser(os_type='cisco_ios')
    with open("tests/proposed-cisco-ios.txt", 'r') as f:
        parsed_data = parser.parse_config(f.read())
    
    # Check for unparsed important configurations
    print("\n❌ POTENTIAL PARSING GAPS:")
    
    # Check for helper-address (line 83, 59)
    helper_lines = [line for line in config_lines if 'ip helper-address' in line]
    if helper_lines:
        print(f"⚠️  IP helper-address commands found but not fully parsed: {len(helper_lines)} instances")
        for line in helper_lines:
            print(f"   - {line.strip()}")
    
    # Check for switchport configurations not captured
    switchport_lines = [line for line in config_lines if 'switchport' in line and 'trunk' not in line and 'access' not in line]
    if switchport_lines:
        print(f"⚠️  Additional switchport configs: {len(switchport_lines)} instances")
        for line in switchport_lines:
            print(f"   - {line.strip()}")
    
    # Check BGP (should be empty in this config)
    bgp_lines = [line for line in config_lines if line.strip().startswith('router bgp')]
    if bgp_lines and not parsed_data.get('bgp'):
        print(f"❌ BGP configuration exists but not parsed: {len(bgp_lines)} instances")
    elif not bgp_lines and parsed_data.get('bgp'):
        print("✅ BGP parsing correct (empty as expected)")
    else:
        print("✅ BGP parsing correct")
    
    # Check SNMP configuration
    snmp_lines = [line for line in config_lines if 'snmp-server' in line]
    if snmp_lines:
        print(f"⚠️  SNMP configurations found but may not be parsed: {len(snmp_lines)} instances")
        for line in snmp_lines:
            print(f"   - {line.strip()}")
    
    # Check line configurations
    line_configs = [line for line in config_lines if line.strip().startswith('line ')]
    if line_configs:
        print(f"⚠️  Line configurations found but may not be parsed: {len(line_configs)} instances")
    
    print("\n✅ SUCCESSFULLY PARSED SECTIONS:")
    for section, data in parsed_data.items():
        if data:  # Only show non-empty sections
            if isinstance(data, dict):
                print(f"   - {section}: {len(data)} items")
            elif isinstance(data, list):
                print(f"   - {section}: {len(data)} items")
            else:
                print(f"   - {section}: {data}")

def analyze_arista_eos_gaps():
    """Analyze Arista EOS configuration for parsing gaps."""
    print("\n\n🔍 DETAILED ARISTA EOS ANALYSIS")
    print("=" * 60)
    
    # Load config
    with open("tests/proposed-arista-eos.txt", 'r') as f:
        config_lines = f.read().splitlines()
    
    parser = ConfigTextParser(os_type='arista_eos')
    with open("tests/proposed-arista-eos.txt", 'r') as f:
        parsed_data = parser.parse_config(f.read())
    
    print("\n❌ POTENTIAL PARSING GAPS:")
    
    # Check for LAG/channel-group configurations
    channel_lines = [line for line in config_lines if 'channel-group' in line]
    if channel_lines:
        interfaces_with_channel = parsed_data.get('interfaces', {})
        parsed_channel_count = sum(1 for intf in interfaces_with_channel.values() if 'channel_group' in intf)
        print(f"⚠️  Channel-group configs found: {len(channel_lines)} in text, {parsed_channel_count} parsed")
    
    # Check for helper-address
    helper_lines = [line for line in config_lines if 'ip helper-address' in line]
    if helper_lines:
        print(f"⚠️  IP helper-address commands found but not fully parsed: {len(helper_lines)} instances")
        for line in helper_lines:
            print(f"   - {line.strip()}")
    
    # Check MTU configurations
    mtu_lines = [line for line in config_lines if 'mtu' in line]
    if mtu_lines:
        interfaces_with_mtu = parsed_data.get('interfaces', {})
        parsed_mtu_count = sum(1 for intf in interfaces_with_mtu.values() if 'mtu' in intf)
        print(f"⚠️  MTU configs found: {len(mtu_lines)} in text, {parsed_mtu_count} parsed")
    
    # Check BGP detailed configuration
    bgp_neighbor_lines = [line for line in config_lines if 'neighbor' in line and ('remote-as' in line or 'description' in line)]
    bgp_parsed = parsed_data.get('bgp', {})
    if bgp_neighbor_lines and bgp_parsed:
        print(f"⚠️  BGP neighbor details: {len(bgp_neighbor_lines)} lines in config")
        if '65001' in bgp_parsed:
            neighbor_count = len(bgp_parsed['65001'].get('neighbor_remote_as', []))
            print(f"   - Parsed neighbors: {neighbor_count}")
    
    # Check address-family configurations
    af_lines = [line for line in config_lines if 'address-family' in line]
    if af_lines:
        print(f"⚠️  Address-family configurations found but may not be fully parsed: {len(af_lines)} instances")
    
    # Check management API
    mgmt_lines = [line for line in config_lines if 'management api' in line]
    if mgmt_lines:
        print(f"⚠️  Management API configurations found but may not be parsed: {len(mgmt_lines)} instances")
    
    print("\n✅ SUCCESSFULLY PARSED SECTIONS:")
    for section, data in parsed_data.items():
        if data:  # Only show non-empty sections
            if isinstance(data, dict):
                print(f"   - {section}: {len(data)} items")
            elif isinstance(data, list):
                print(f"   - {section}: {len(data)} items")
            else:
                print(f"   - {section}: {data}")

def check_yang_model_accuracy():
    """Check YANG model transformation accuracy against expected structure."""
    print("\n\n🎯 YANG MODEL ACCURACY CHECK")
    print("=" * 60)
    
    # Test both parsers
    for os_type, config_file in [('cisco_ios', 'tests/proposed-cisco-ios.txt'), 
                                  ('arista_eos', 'tests/proposed-arista-eos.txt')]:
        print(f"\n📋 {os_type.upper()} YANG Transformation:")
        
        parser = ConfigTextParser(os_type=os_type)
        transformer = YangTransformer()
        
        with open(config_file, 'r') as f:
            parsed_data = parser.parse_config(f.read())
        
        yang_output = transformer.transform(parsed_data, os_type)
        
        # Check interface structure
        interfaces = yang_output.get('openconfig-interfaces:interfaces', {}).get('interface', [])
        print(f"   - Interfaces in YANG: {len(interfaces)}")
        
        # Check if IP addresses are properly converted to prefix-length
        ip_interfaces = [intf for intf in interfaces if 'subinterfaces' in intf]
        print(f"   - Interfaces with IP config: {len(ip_interfaces)}")
        
        # Check VLAN structure
        vlans = yang_output.get('openconfig-vlan:vlans', {}).get('vlan', [])
        print(f"   - VLANs in YANG: {len(vlans)}")
        
        # Check network instance structure
        ni = yang_output.get('openconfig-network-instance:network-instances', {})
        protocols = ni.get('network-instance', [{}])[0].get('protocols', {}).get('protocol', [])
        print(f"   - Routing protocols in YANG: {len(protocols)}")
        
        # Check ACL structure
        acls = yang_output.get('openconfig-acl:acl', {}).get('acl-sets', {}).get('acl-set', [])
        print(f"   - ACLs in YANG: {len(acls)}")
        
        # Check for proper action mapping
        for acl in acls:
            entries = acl.get('acl-entries', {}).get('acl-entry', [])
            actions = [entry.get('actions', {}).get('config', {}).get('forwarding-action') for entry in entries]
            unique_actions = set(filter(None, actions))
            print(f"   - ACL {acl.get('name')} actions: {unique_actions}")

if __name__ == "__main__":
    print("🔍 COMPREHENSIVE TEXT PARSING GAP ANALYSIS")
    print("Identifying missing or incorrectly mapped configuration objects")
    print("=" * 80)
    
    analyze_cisco_ios_gaps()
    analyze_arista_eos_gaps() 
    check_yang_model_accuracy()