#!/usr/bin/env python3
"""
Working example demonstrating proper YANG validation without fallback.
This example shows the complete solution for yangson YANG validation issues.

Run this script to verify your YANG validation setup is working correctly.
"""

from pathlib import Path
import json
import sys
import logging

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def test_yang_validation():
    """Test YANG validation with complete dependencies."""
    
    # Add src to path for imports (adjust as needed for your project structure)
    project_root = Path(__file__).parent.parent
    sys.path.append(str(project_root / "src"))
    
    try:
        from validation.yang_validator import YangValidator
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure your project structure includes the YangValidator class")
        return False
    
    # Initialize validator
    yang_path = project_root / "models" / "yang"
    validator = YangValidator(yang_path)
    
    print("🧪 Testing YANG Validation Setup")
    print("=" * 50)
    
    # Test 1: Basic VLAN validation
    print("\n1️⃣ Testing VLAN validation...")
    vlan_data = {
        'openconfig-vlan:vlans': {
            'vlan': [
                {
                    'vlan-id': 100,
                    'config': {
                        'vlan-id': 100,
                        'name': 'PRODUCTION',
                        'status': 'ACTIVE'
                    }
                },
                {
                    'vlan-id': 200,
                    'config': {
                        'vlan-id': 200,
                        'name': 'DEVELOPMENT',
                        'status': 'ACTIVE'
                    }
                }
            ]
        }
    }
    
    try:
        result = validator.validate_openconfig(vlan_data)
        if 'openconfig-vlan:vlans' in result:
            print("   ✅ VLAN validation successful!")
            vlan_success = True
        else:
            print("   ❌ VLAN validation returned unexpected result")
            vlan_success = False
    except Exception as e:
        print(f"   ❌ VLAN validation failed: {e}")
        vlan_success = False
    
    # Test 2: Interface validation with IANA types
    print("\n2️⃣ Testing Interface validation with IANA types...")
    interface_data = {
        'openconfig-interfaces:interfaces': {
            'interface': [
                {
                    'name': 'GigabitEthernet1/0/1',
                    'config': {
                        'name': 'GigabitEthernet1/0/1',
                        'type': 'iana-if-type:ethernetCsmacd',  # Uses IANA type
                        'enabled': True,
                        'description': 'Test interface with IANA type'
                    }
                }
            ]
        }
    }
    
    try:
        result = validator.validate_openconfig(interface_data)
        if 'openconfig-interfaces:interfaces' in result:
            print("   ✅ Interface validation with IANA types successful!")
            interface_success = True
        else:
            print("   ❌ Interface validation returned unexpected result")
            interface_success = False
    except Exception as e:
        print(f"   ❌ Interface validation failed: {e}")
        interface_success = False
    
    # Test 3: Combined validation
    print("\n3️⃣ Testing combined interface + VLAN validation...")
    combined_data = {
        'openconfig-interfaces:interfaces': {
            'interface': [
                {
                    'name': 'GigabitEthernet1/0/2',
                    'config': {
                        'name': 'GigabitEthernet1/0/2',
                        'type': 'iana-if-type:ethernetCsmacd',
                        'enabled': True,
                        'description': 'Combined test interface'
                    }
                }
            ]
        },
        'openconfig-vlan:vlans': {
            'vlan': [
                {
                    'vlan-id': 300,
                    'config': {
                        'vlan-id': 300,
                        'name': 'COMBINED_TEST',
                        'status': 'ACTIVE'
                    }
                }
            ]
        }
    }
    
    try:
        result = validator.validate_openconfig(combined_data)
        if ('openconfig-interfaces:interfaces' in result and 
            'openconfig-vlan:vlans' in result):
            print("   ✅ Combined validation successful!")
            combined_success = True
        else:
            print("   ❌ Combined validation returned unexpected result")
            combined_success = False
    except Exception as e:
        print(f"   ❌ Combined validation failed: {e}")
        combined_success = False
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    print(f"VLAN Validation:      {'✅ PASS' if vlan_success else '❌ FAIL'}")
    print(f"Interface Validation: {'✅ PASS' if interface_success else '❌ FAIL'}")
    print(f"Combined Validation:  {'✅ PASS' if combined_success else '❌ FAIL'}")
    
    overall_success = vlan_success and interface_success and combined_success
    
    if overall_success:
        print("\n🎉 SUCCESS: YANG validation is working correctly without fallback!")
        print("Your yangson setup is properly configured.")
    else:
        print("\n❌ ISSUES DETECTED: Some validations failed.")
        print("Check the troubleshooting guide in docs/YANG_VALIDATION_TROUBLESHOOTING.md")
    
    return overall_success

def check_prerequisites():
    """Check if all required files are present."""
    project_root = Path(__file__).parent.parent
    
    required_files = [
        "models/yang/openconfig-yang-library.json",
        "models/yang/ietf-standard/iana-if-type.yang",
        "models/yang/ietf-standard/ietf-inet-types.yang",
        "models/yang/openconfig/common/openconfig-platform-types.yang",
        "models/yang/openconfig/vlan/openconfig-vlan.yang",
        "models/yang/openconfig/interfaces/openconfig-interfaces.yang",
    ]
    
    print("🔍 Checking Prerequisites")
    print("=" * 30)
    
    missing_files = []
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} required files!")
        print("Follow the setup instructions in docs/YANG_VALIDATION_TROUBLESHOOTING.md")
        return False
    else:
        print("\n✅ All prerequisite files present!")
        return True

if __name__ == "__main__":
    print("🚀 YANG Validation Test Suite")
    print("Testing yangson YANG validation setup")
    print("=" * 60)
    
    # Check prerequisites first
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please complete setup first.")
        sys.exit(1)
    
    # Run validation tests
    if test_yang_validation():
        print("\n🎯 RESULT: Your YANG validation setup is working perfectly!")
        sys.exit(0)
    else:
        print("\n🔧 RESULT: Setup needs adjustment. Check the troubleshooting guide.")
        sys.exit(1)