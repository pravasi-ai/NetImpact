# YANG Validation Quick Setup

⚡ **Quick fix for yangson "too many arguments" and missing dependency errors.**

## 🚨 If You're Seeing This Error:
```
DataModel.from_file() takes from 2 to 4 positional arguments but 35 were given
Error loading YANG models for openconfig: iana-if-type
Error loading YANG models for openconfig: openconfig-platform-types
```

## ⚡ 5-Minute Fix:

### 1. Download Missing Dependencies
```bash
# Create directories
mkdir -p models/yang/ietf-standard

# Download required standard modules (2 commands)
curl -o models/yang/ietf-standard/iana-if-type.yang \
  https://raw.githubusercontent.com/YangModels/yang/main/standard/iana/iana-if-type%402023-01-26.yang

curl -o models/yang/openconfig/common/openconfig-platform-types.yang \
  https://raw.githubusercontent.com/openconfig/public/master/release/models/platform/openconfig-platform-types.yang
```

### 2. Fix Your YANG Validator Code

❌ **Wrong** (causes "too many arguments" error):
```python
# DON'T DO THIS
yang_files = list_all_yang_files()
data_model = DataModel.from_file(*yang_files)  # FAILS
```

✅ **Correct**:
```python  
# DO THIS INSTEAD
data_model = DataModel.from_file(
    name="models/yang/openconfig-yang-library.json",  # Library file
    mod_path=("models/yang/openconfig/common", "models/yang/ietf-standard")  # Module directories
)
```

### 3. Create YANG Library File

Save as `models/yang/openconfig-yang-library.json`:
```json
{
  "ietf-yang-library:modules-state": {
    "module-set-id": "openconfig-working",
    "module": [
      {"name": "iana-if-type", "namespace": "urn:ietf:params:xml:ns:yang:iana-if-type", "revision": "", "conformance-type": "implement"},
      {"name": "openconfig-extensions", "namespace": "http://openconfig.net/yang/openconfig-ext", "revision": "", "conformance-type": "implement"},
      {"name": "openconfig-types", "namespace": "http://openconfig.net/yang/openconfig-types", "revision": "", "conformance-type": "implement"},
      {"name": "openconfig-platform-types", "namespace": "http://openconfig.net/yang/platform-types", "revision": "", "conformance-type": "implement"},
      {"name": "openconfig-interfaces", "namespace": "http://openconfig.net/yang/interfaces", "revision": "", "conformance-type": "implement"},
      {"name": "openconfig-vlan", "namespace": "http://openconfig.net/yang/vlan", "revision": "", "conformance-type": "implement"}
    ]
  }
}
```

## ✅ Test Your Fix

Run this quick test:
```python
from yangson import DataModel

# This should work now
data_model = DataModel.from_file(
    name="models/yang/openconfig-yang-library.json",
    mod_path=("models/yang/openconfig/common", "models/yang/ietf-standard")
)
print("✅ YANG validation fixed!")
```

---

**Need more details?** See the full troubleshooting guide: `docs/YANG_VALIDATION_TROUBLESHOOTING.md`