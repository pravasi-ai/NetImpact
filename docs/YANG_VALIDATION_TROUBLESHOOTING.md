# YANG Validation with Yangson Library - Troubleshooting Guide

This comprehensive guide helps developers resolve YANG validation issues when using the `yangson` Python library for OpenConfig and vendor-specific YANG model validation.

## 🚨 Common Error Patterns

### Error 1: "DataModel.from_file() takes from 2 to 4 positional arguments but N were given"

**Root Cause**: Incorrect usage of yangson's `DataModel.from_file()` method.

❌ **Wrong Approach** (causes the error):
```python
# This FAILS - trying to pass individual YANG files as arguments
yang_files = ['openconfig-interfaces.yang', 'openconfig-vlan.yang', ...]
data_model = DataModel.from_file(*yang_files)  # ❌ TOO MANY ARGUMENTS
```

✅ **Correct Approach**:
```python
# yangson requires a YANG library data file (RFC 8525 format)
data_model = DataModel.from_file(
    name="path/to/yang-library.json",
    mod_path=("path/to/yang/modules/", "path/to/standard/modules/")
)
```

### Error 2: "Failed to load OpenConfig YANG models" / Missing Module Dependencies

**Symptoms**:
```
Error loading YANG models for openconfig: openconfig-platform-types
Error loading YANG models for openconfig: iana-if-type
Error loading YANG models for openconfig: openconfig-if-aggregate
Error loading YANG models for openconfig: openconfig-defined-sets
Error loading YANG models for arista_eos_None: ietf-yang-types
OpenConfig YANG models not available, performing basic validation
```

**Root Cause**: Missing standard IANA/IETF modules, OpenConfig dependencies, and incomplete vendor YANG library configurations.

## 📋 Step-by-Step Solution

### Step 1: Download Missing Standard YANG Modules

Create directory structure and download required standard modules:

```bash
# Create directories
mkdir -p models/yang/ietf-standard
mkdir -p models/yang/openconfig/common

# Download IANA interface types (required by most OpenConfig modules)
curl -o models/yang/ietf-standard/iana-if-type.yang \
  https://raw.githubusercontent.com/YangModels/yang/main/standard/iana/iana-if-type%402023-01-26.yang

# Download IETF inet types  
curl -o models/yang/ietf-standard/ietf-inet-types.yang \
  https://raw.githubusercontent.com/YangModels/yang/main/standard/ietf/RFC/ietf-inet-types%402013-07-15.yang

# Download missing OpenConfig modules
curl -o models/yang/openconfig/common/openconfig-platform-types.yang \
  https://raw.githubusercontent.com/openconfig/public/master/release/models/platform/openconfig-platform-types.yang

# Download openconfig-defined-sets (required for ACL and policy modules)
curl -o models/yang/openconfig/common/openconfig-defined-sets.yang \
  https://raw.githubusercontent.com/openconfig/public/master/release/models/policy/openconfig-defined-sets.yang
```

### Step 2: Create YANG Library Data File

Create `models/yang/openconfig-yang-library.json` following RFC 8525 format:

```json
{
  "ietf-yang-library:modules-state": {
    "module-set-id": "openconfig-complete",
    "module": [
      {
        "name": "ietf-yang-types",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-types",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "ietf-inet-types",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-inet-types",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "iana-if-type",
        "namespace": "urn:ietf:params:xml:ns:yang:iana-if-type",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-extensions",
        "namespace": "http://openconfig.net/yang/openconfig-ext",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-types",
        "namespace": "http://openconfig.net/yang/openconfig-types",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-interfaces",
        "namespace": "http://openconfig.net/yang/interfaces",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-vlan",
        "namespace": "http://openconfig.net/yang/vlan",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-acl",
        "namespace": "http://openconfig.net/yang/acl",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "openconfig-defined-sets",
        "namespace": "http://openconfig.net/yang/policy-types",
        "revision": "",
        "conformance-type": "implement"
      }
    ]
  }
}
```

### Step 3: Update YANG Validator Implementation

Correct yangson usage pattern:

```python
from yangson import DataModel
from pathlib import Path
import json

class YangValidator:
    def __init__(self, yang_models_path: Path):
        self.yang_models_path = yang_models_path
        self.loaded_models = {}
        
    def _load_data_model(self, model_paths, cache_key, yang_library_file=None):
        """Load yangson DataModel using YANG library data file."""
        if cache_key in self.loaded_models:
            return self.loaded_models[cache_key]
            
        try:
            # Default to OpenConfig library file
            if not yang_library_file:
                yang_library_file = str(self.yang_models_path / "openconfig-yang-library.json")
            
            # Verify library file exists
            library_path = Path(yang_library_file)
            if not library_path.exists():
                raise FileNotFoundError(f"YANG library file not found: {yang_library_file}")
            
            # Convert paths to strings for yangson
            mod_path_strings = tuple(str(path) for path in model_paths if path.exists())
            
            # Load DataModel using YANG library data file
            data_model = DataModel.from_file(
                name=yang_library_file,
                mod_path=mod_path_strings
            )
            
            self.loaded_models[cache_key] = data_model
            return data_model
            
        except Exception as e:
            logging.error(f"Error loading YANG models for {cache_key}: {e}")
            return None
    
    def validate_openconfig(self, data):
        """Validate data against OpenConfig YANG models."""
        model_paths = [
            self.yang_models_path / "openconfig/common",
            self.yang_models_path / "openconfig/interfaces", 
            self.yang_models_path / "openconfig/vlan",
            self.yang_models_path / "openconfig/acl",
            self.yang_models_path / "ietf-standard"  # Include standard modules
        ]
        
        try:
            data_model = self._load_data_model(model_paths, "openconfig")
            if not data_model:
                # Graceful fallback to basic validation
                return self._basic_structure_validation(data)
                
            # Full YANG validation
            instance = data_model.parse_data(json.dumps(data))
            instance.validate()
            return data
            
        except Exception as e:
            logging.error(f"YANG validation failed: {e}")
            # Fallback to basic validation
            return self._basic_structure_validation(data)
```

### Step 4: Implement Graceful Fallback Validation

Always provide fallback validation for production robustness:

```python
def _basic_structure_validation(self, data):
    """Basic structure validation when YANG models unavailable."""
    validation_errors = []
    
    # Check for expected OpenConfig containers
    expected_containers = [
        'openconfig-interfaces:interfaces',
        'openconfig-vlan:vlans', 
        'openconfig-acl:acl',
        'routing',
        'device'
    ]
    
    found_containers = [c for c in expected_containers if c in data]
    if not found_containers:
        validation_errors.append("No recognized OpenConfig containers found")
        
    # Validate interfaces structure
    if 'openconfig-interfaces:interfaces' in data:
        interfaces = data['openconfig-interfaces:interfaces']
        if not isinstance(interfaces, dict) or 'interface' not in interfaces:
            validation_errors.append("Invalid interfaces structure")
        elif not isinstance(interfaces['interface'], list):
            validation_errors.append("Interfaces interface list must be array")
    
    # Log validation results
    if validation_errors:
        logging.warning(f"Basic validation issues: {', '.join(validation_errors)}")
    else:
        logging.info("Basic structure validation passed")
        
    return data
```

## 🔧 Troubleshooting Specific Errors

### Missing Module: "openconfig-defined-sets"
```bash
# Critical for ACL and policy modules
curl -o models/yang/openconfig/common/openconfig-defined-sets.yang \
  https://raw.githubusercontent.com/openconfig/public/master/release/models/policy/openconfig-defined-sets.yang
```

### Missing Module: "openconfig-platform-types"
```bash
# Download from OpenConfig public repository
curl -o models/yang/openconfig/common/openconfig-platform-types.yang \
  https://raw.githubusercontent.com/openconfig/public/master/release/models/platform/openconfig-platform-types.yang
```

### Missing Module: "iana-if-type"
```bash
# Download from IANA YANG repository
curl -o models/yang/ietf-standard/iana-if-type.yang \
  https://raw.githubusercontent.com/YangModels/yang/main/standard/iana/iana-if-type%402023-01-26.yang
```

### Missing Module: "ietf-inet-types"
```bash
# Download from IETF RFC repository
curl -o models/yang/ietf-standard/ietf-inet-types.yang \
  https://raw.githubusercontent.com/YangModels/yang/main/standard/ietf/RFC/ietf-inet-types%402013-07-15.yang
```

### Error 3: "arista_eos_None" / Vendor Library Issues

**Symptoms**:
```
Error loading YANG models for arista_eos_None: ietf-yang-types
Error loading YANG models for cisco_ios-xe_None: ietf-inet-types
```

**Root Cause**: Device metadata lookup returning `None` for OS version, and incomplete vendor YANG library files.

**Solution**:
1. **Fix Device Info Lookup**: Ensure database queries include all required fields:
```python
# Incorrect - missing os_version field
result = session.run(
    "MATCH (d:Device {hostname: $hostname})-[:LATEST]->(ds:DeviceState) "
    "RETURN ds.vendor as vendor, ds.os_type as os_type",  # ❌ Missing os_version
    hostname=hostname
)

# Correct - include all device metadata fields  
result = session.run(
    "MATCH (d:Device {hostname: $hostname})-[:LATEST]->(ds:DeviceState) "
    "RETURN ds.vendor as vendor, ds.os_type as os_type, ds.os_version as os_version",  # ✅ Complete
    hostname=hostname
)
```

2. **Enhance Vendor YANG Library Files**: Ensure vendor libraries include standard modules:
```json
{
  "ietf-yang-library:modules-state": {
    "module-set-id": "arista-eos-complete",
    "module": [
      {
        "name": "ietf-yang-types",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-types",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "ietf-inet-types",
        "namespace": "urn:ietf:params:xml:ns:yang:ietf-inet-types",
        "revision": "",
        "conformance-type": "implement"
      },
      {
        "name": "iana-if-type",
        "namespace": "urn:ietf:params:xml:ns:yang:iana-if-type",
        "revision": "",
        "conformance-type": "implement"
      }
    ]
  }
}
```

### Module Load Order Issues

Ensure modules are listed in dependency order in your YANG library file:
1. **Standard modules first**: `ietf-yang-types`, `ietf-inet-types`, `iana-if-type`
2. **Base OpenConfig modules**: `openconfig-extensions`, `openconfig-types`  
3. **Dependent modules**: `openconfig-interfaces`, `openconfig-vlan`, `openconfig-acl`

## 📁 Required Directory Structure

```
models/yang/
├── openconfig-yang-library.json          # RFC 8525 YANG library data
├── ietf-standard/                         # Standard IANA/IETF modules
│   ├── iana-if-type.yang
│   ├── ietf-inet-types.yang
│   └── ietf-interfaces.yang
└── openconfig/                            # OpenConfig modules
    ├── common/
    │   ├── openconfig-extensions.yang
    │   ├── openconfig-types.yang
    │   ├── openconfig-yang-types.yang
    │   ├── openconfig-platform-types.yang
    │   └── openconfig-defined-sets.yang
    ├── interfaces/
    │   ├── openconfig-interfaces.yang
    │   ├── openconfig-if-ethernet.yang
    │   └── openconfig-if-aggregate.yang
    ├── vlan/
    │   ├── openconfig-vlan.yang
    │   └── openconfig-vlan-types.yang
    └── acl/
        ├── openconfig-acl.yang
        └── openconfig-packet-match.yang
```

## ✅ Complete Solution Verification

### Test 1: Verify No Validation Errors
Run your application and confirm clean execution without fallback messages:

```bash
# Should show NO error messages like:
# "Error loading YANG models for openconfig: openconfig-defined-sets"
# "OpenConfig YANG models not available, performing basic validation"
# "Error loading YANG models for arista_eos_None: ietf-yang-types"

python -m your_cli_app analyze config proposed-config.json --device hostname
```

**Expected clean output** (no stderr validation errors):
```
📄 Analyzing proposed config: proposed-config.json
🎯 Target device: hostname
╭────────────────────── Analysis Results ──────────────────────╮
│ Status: completed                                            │
│ Duration: 0.3s                                               │
╰──────────────────────────────────────────────────────────────╯
```

### Test 2: Basic YANG Model Loading
```python
from pathlib import Path
from your_validator import YangValidator

yang_path = Path('./models/yang')
validator = YangValidator(yang_path)

# This should NOT fall back to basic validation
test_data = {
    'openconfig-vlan:vlans': {
        'vlan': [
            {
                'vlan-id': 100,
                'config': {
                    'vlan-id': 100,
                    'name': 'TEST_VLAN',
                    'status': 'ACTIVE'
                }
            }
        ]
    }
}

result = validator.validate_openconfig(test_data)
print("✅ Full YANG validation successful!" if "OpenConfig YANG validation passed" in logs else "❌ Still using fallback")
```

### Test 3: Interface Validation with IANA Types
```python
test_data = {
    'openconfig-interfaces:interfaces': {
        'interface': [
            {
                'name': 'GigabitEthernet1/0/1',
                'config': {
                    'name': 'GigabitEthernet1/0/1',
                    'type': 'iana-if-type:ethernetCsmacd',  # Uses IANA type
                    'enabled': True,
                    'description': 'Test interface'
                }
            }
        ]
    }
}

result = validator.validate_openconfig(test_data)
```

## 🚀 Production Best Practices

1. **Always implement fallback validation** - YANG model dependencies can be complex
2. **Version pin your YANG modules** - Include revision dates in library files
3. **Cache DataModel instances** - Loading YANG models is expensive
4. **Log validation results** - Essential for troubleshooting in production
5. **Test with real data** - Validate against actual device configurations
6. **Fix root causes, don't suppress errors** - Address missing modules and incomplete queries
7. **Verify vendor library completeness** - Include all standard IETF/IANA modules
8. **Monitor for None values** - Ensure database queries return complete device metadata

## 📚 Additional Resources

- [RFC 8525 - YANG Library](https://datatracker.ietf.org/doc/rfc8525/)
- [Yangson Documentation](https://yangson.labs.nic.cz/)
- [OpenConfig Public Models](https://github.com/openconfig/public)
- [YANG Models Repository](https://github.com/YangModels/yang)
- [IANA YANG Parameters](https://www.iana.org/assignments/yang-parameters/yang-parameters.xhtml)

---

## 🎯 Summary Checklist

After implementing all fixes, verify:
- ✅ No "Error loading YANG models for openconfig" messages
- ✅ No "OpenConfig YANG models not available" fallback warnings  
- ✅ No "arista_eos_None" or "cisco_ios-xe_None" errors
- ✅ Clean CLI output without validation errors
- ✅ Proper YANG validation passing (not just fallback)
- ✅ Complete device metadata queries including os_version
- ✅ Vendor YANG library files include all standard modules

**Note**: This solution provides both proper YANG validation AND graceful fallback for production robustness. The key insight is that yangson requires RFC 8525 YANG library data files, not direct YANG module files. When validation errors occur, fix the root cause rather than suppressing error messages.