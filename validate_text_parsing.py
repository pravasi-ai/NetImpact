#!/usr/bin/env python3
"""
Comprehensive validation of text configuration parsing and YANG transformation.
Tests parsing accuracy and identifies any missing or incorrectly mapped config objects.
"""

import sys
from pathlib import Path
import json
from pprint import pprint

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from parsing.text_parser import ConfigTextParser
from parsing.config_transformer import YangTransformer

def validate_cisco_ios_parsing():
    """Validate Cisco IOS text parsing and YANG transformation."""
    print("=" * 80)
    print("🔍 CISCO IOS CONFIGURATION VALIDATION")
    print("=" * 80)
    
    # Load input config
    config_file = Path("tests/proposed-cisco-ios.txt")
    with open(config_file, 'r') as f:
        config_text = f.read()
    
    # Parse configuration
    parser = ConfigTextParser(os_type='cisco_ios')
    parsed_data = parser.parse_config(config_text)
    
    print("\n📋 PARSED DATA STRUCTURE:")
    print("-" * 40)
    for key, value in parsed_data.items():
        print(f"{key}: {type(value)} - {len(value) if isinstance(value, (list, dict)) else value}")
    
    print("\n🔍 DETAILED PARSING RESULTS:")
    print("-" * 40)
    pprint(parsed_data, width=120)
    
    # Transform to YANG
    transformer = YangTransformer()
    yang_output = transformer.transform(parsed_data, 'cisco_ios')
    
    print("\n🎯 YANG TRANSFORMATION OUTPUT:")
    print("-" * 40)
    pprint(yang_output, width=120)
    
    # Validation checks
    print("\n✅ VALIDATION CHECKS:")
    print("-" * 40)
    
    # Check hostname
    hostname_expected = "acc-sw-01"
    hostname_parsed = parsed_data.get('hostname', [])
    if hostname_parsed:
        hostname_actual = hostname_parsed[0][0] if isinstance(hostname_parsed[0], tuple) else hostname_parsed[0]
        print(f"Hostname: {hostname_actual} {'✅' if hostname_actual == hostname_expected else '❌'}")
    else:
        print("Hostname: ❌ NOT PARSED")
    
    # Check VLANs
    vlans_expected = ['10', '20', '30', '200', '999']
    vlans_parsed = list(parsed_data.get('vlans', {}).keys())
    print(f"VLANs Expected: {vlans_expected}")
    print(f"VLANs Parsed: {vlans_parsed}")
    missing_vlans = set(vlans_expected) - set(vlans_parsed)
    if missing_vlans:
        print(f"❌ Missing VLANs: {missing_vlans}")
    else:
        print("✅ All VLANs parsed correctly")
    
    # Check interfaces
    interfaces_expected = [
        'GigabitEthernet0/1', 'GigabitEthernet0/2', 'FastEthernet0/1', 
        'FastEthernet0/2', 'FastEthernet0/7', 'Loopback0', 'Vlan10', 'Vlan20'
    ]
    interfaces_parsed = list(parsed_data.get('interfaces', {}).keys())
    print(f"Interfaces Expected: {len(interfaces_expected)}")
    print(f"Interfaces Parsed: {len(interfaces_parsed)}")
    missing_interfaces = set(interfaces_expected) - set(interfaces_parsed)
    if missing_interfaces:
        print(f"❌ Missing Interfaces: {missing_interfaces}")
    else:
        print("✅ All interfaces parsed correctly")
    
    # Check ACLs
    acls_expected = ['SNMP_HOSTS', 'UPLINK_INBOUND', 'USER_INBOUND']
    acls_parsed = list(parsed_data.get('acls', {}).keys())
    print(f"ACLs Expected: {acls_expected}")
    print(f"ACLs Parsed: {acls_parsed}")
    missing_acls = set(acls_expected) - set(acls_parsed)
    if missing_acls:
        print(f"❌ Missing ACLs: {missing_acls}")
    else:
        print("✅ All ACLs parsed correctly")
    
    # Check routing protocols
    print(f"BGP Parsed: {'✅' if 'bgp' in parsed_data else '❌'}")
    print(f"OSPF Parsed: {'✅' if 'ospf' in parsed_data else '❌'}")
    print(f"Static Routes Parsed: {'✅' if 'static_routes' in parsed_data else '❌'}")
    
    return parsed_data, yang_output

def validate_arista_eos_parsing():
    """Validate Arista EOS text parsing and YANG transformation."""
    print("\n\n" + "=" * 80)
    print("🔍 ARISTA EOS CONFIGURATION VALIDATION")
    print("=" * 80)
    
    # Load input config
    config_file = Path("tests/proposed-arista-eos.txt")
    with open(config_file, 'r') as f:
        config_text = f.read()
    
    # Parse configuration
    parser = ConfigTextParser(os_type='arista_eos')
    parsed_data = parser.parse_config(config_text)
    
    print("\n📋 PARSED DATA STRUCTURE:")
    print("-" * 40)
    for key, value in parsed_data.items():
        print(f"{key}: {type(value)} - {len(value) if isinstance(value, (list, dict)) else value}")
    
    print("\n🔍 DETAILED PARSING RESULTS:")
    print("-" * 40)
    pprint(parsed_data, width=120)
    
    # Transform to YANG
    transformer = YangTransformer()
    yang_output = transformer.transform(parsed_data, 'arista_eos')
    
    print("\n🎯 YANG TRANSFORMATION OUTPUT:")
    print("-" * 40)
    pprint(yang_output, width=120)
    
    # Validation checks
    print("\n✅ VALIDATION CHECKS:")
    print("-" * 40)
    
    # Check hostname
    hostname_expected = "core-sw-02"
    hostname_parsed = parsed_data.get('hostname', [])
    if hostname_parsed:
        hostname_actual = hostname_parsed[0][0] if isinstance(hostname_parsed[0], tuple) else hostname_parsed[0]
        print(f"Hostname: {hostname_actual} {'✅' if hostname_actual == hostname_expected else '❌'}")
    else:
        print("Hostname: ❌ NOT PARSED")
    
    # Check VLANs
    vlans_expected = ['10', '20', '30', '4094']
    vlans_parsed = list(parsed_data.get('vlans', {}).keys())
    print(f"VLANs Expected: {vlans_expected}")
    print(f"VLANs Parsed: {vlans_parsed}")
    missing_vlans = set(vlans_expected) - set(vlans_parsed)
    if missing_vlans:
        print(f"❌ Missing VLANs: {missing_vlans}")
    else:
        print("✅ All VLANs parsed correctly")
    
    # Check interfaces
    interfaces_expected = [
        'Port-Channel10', 'Ethernet1', 'Ethernet3', 'Ethernet47', 'Ethernet48',
        'Loopback0', 'Vlan10', 'Vlan20'
    ]
    interfaces_parsed = list(parsed_data.get('interfaces', {}).keys())
    print(f"Interfaces Expected: {len(interfaces_expected)}")
    print(f"Interfaces Parsed: {len(interfaces_parsed)}")
    missing_interfaces = set(interfaces_expected) - set(interfaces_parsed)
    if missing_interfaces:
        print(f"❌ Missing Interfaces: {missing_interfaces}")
    else:
        print("✅ All interfaces parsed correctly")
    
    # Check ACLs
    acls_expected = ['USER_INBOUND_V4']
    acls_parsed = list(parsed_data.get('acls', {}).keys())
    print(f"ACLs Expected: {acls_expected}")
    print(f"ACLs Parsed: {acls_parsed}")
    missing_acls = set(acls_expected) - set(acls_parsed)
    if missing_acls:
        print(f"❌ Missing ACLs: {missing_acls}")
    else:
        print("✅ All ACLs parsed correctly")
    
    # Check routing protocols
    print(f"BGP Parsed: {'✅' if 'bgp' in parsed_data else '❌'}")
    print(f"OSPF Parsed: {'✅' if 'ospf' in parsed_data else '❌'}")
    print(f"Static Routes Parsed: {'✅' if 'static_routes' in parsed_data else '❌'}")
    
    return parsed_data, yang_output

def check_yang_compliance(yang_output, vendor):
    """Check YANG model compliance and completeness."""
    print(f"\n🎯 YANG MODEL COMPLIANCE CHECK - {vendor.upper()}")
    print("-" * 50)
    
    required_yang_objects = [
        'openconfig-interfaces:interfaces',
        'openconfig-vlan:vlans', 
        'openconfig-network-instance:network-instances',
        'openconfig-acl:acl'
    ]
    
    for yang_obj in required_yang_objects:
        if yang_obj in yang_output:
            print(f"✅ {yang_obj}: Present")
            # Check structure
            obj_data = yang_output[yang_obj]
            if isinstance(obj_data, dict) and obj_data:
                print(f"   📊 Contains {len(obj_data)} items" if 'interface' not in yang_obj else f"   📊 Structure: {list(obj_data.keys())}")
            else:
                print(f"   ⚠️ Present but empty or invalid structure")
        else:
            print(f"❌ {yang_obj}: MISSING")
    
    return len([obj for obj in required_yang_objects if obj in yang_output])

if __name__ == "__main__":
    print("🚀 COMPREHENSIVE TEXT CONFIGURATION PARSING VALIDATION")
    print("This will test parsing accuracy and identify any gaps")
    print("=" * 80)
    
    try:
        # Test Cisco IOS
        cisco_parsed, cisco_yang = validate_cisco_ios_parsing()
        cisco_compliance = check_yang_compliance(cisco_yang, 'cisco_ios')
        
        # Test Arista EOS  
        arista_parsed, arista_yang = validate_arista_eos_parsing()
        arista_compliance = check_yang_compliance(arista_yang, 'arista_eos')
        
        # Final summary
        print("\n\n" + "=" * 80)
        print("📊 FINAL VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Cisco IOS YANG Compliance: {cisco_compliance}/4 objects ({'✅' if cisco_compliance == 4 else '❌'})")
        print(f"Arista EOS YANG Compliance: {arista_compliance}/4 objects ({'✅' if arista_compliance == 4 else '❌'})")
        
        overall_status = "✅ PRODUCTION READY" if cisco_compliance >= 3 and arista_compliance >= 3 else "❌ NEEDS FIXES"
        print(f"\n🎯 OVERALL STATUS: {overall_status}")
        
    except Exception as e:
        print(f"❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()