# Configuration Format Guide

This guide explains the expected configuration formats for different network device types in the Universal Configuration Impact Analysis Platform.

## Overview

The platform **strongly prefers OpenConfig format** for all modern network devices to achieve **standardized configuration models across vendors**. This unified approach simplifies network automation and ensures consistent structure regardless of the underlying vendor platform.

**OpenConfig-First Philosophy:** The platform uses OpenConfig as the common data model whenever possible, falling back to vendor-native formats only for legacy devices or unsupported features.

**Why this matters:** Using a standardized OpenConfig format enables:
- **Cross-vendor consistency** in configuration structure
- **Simplified automation** with unified data models  
- **Better interoperability** across multi-vendor environments
- **Future-proof configurations** aligned with industry standards

## Format Requirements by Device Type

### Modern Network Devices (OpenConfig Preferred)

All modern network devices should use **OpenConfig format** for standardization:

- **OS Types:** `cisco-ios`, `cisco-ios-xe`, `cisco-nxos`, `arista-eos`
- **Required Format:** **OpenConfig** 
- **Description:** Standardized YANG-modeled configuration structure for cross-vendor compatibility

#### BGP Configuration Example (OpenConfig - All Modern Devices)
```json
{
  "device": {
    "hostname": "core-sw-01"
  },
  "routing": {
    "bgp": {
      "global": {
        "config": {
          "as": 65001,
          "router-id": "10.0.0.1"
        }
      },
      "neighbors": []
    }
  }
}
```

#### OSPF Configuration Example (OpenConfig - All Modern Devices)
```json
{
  "device": {
    "hostname": "core-sw-01"
  },
  "routing": {
    "ospf": {
      "global": {
        "config": {
          "router-id": "10.0.0.1"
        }
      },
      "areas": {
        "area": [
          {
            "identifier": "0.0.0.0",
            "config": {
              "identifier": "0.0.0.0"
            }
          }
        ]
      }
    }
  }
}
```

#### Interface Configuration Example (OpenConfig - All Modern Devices)
```json
{
  "device": {
    "hostname": "core-sw-01"
  },
  "openconfig-interfaces:interfaces": {
    "interface": [
      {
        "name": "GigabitEthernet1/0/1",
        "config": {
          "name": "GigabitEthernet1/0/1",
          "description": "Connection to distribution",
          "enabled": true,
          "mtu": 1500
        },
        "subinterfaces": {
          "subinterface": [
            {
              "index": 0,
              "config": {
                "index": 0,
                "enabled": true
              },
              "ipv4": {
                "addresses": {
                  "address": [
                    {
                      "ip": "10.0.2.1",
                      "config": {
                        "ip": "10.0.2.1",
                        "prefix-length": 30
                      }
                    }
                  ]
                }
              }
            }
          ]
        }
      }
    ]
  }
}
```

#### Access List Configuration Example (OpenConfig - All Modern Devices)
```json
{
  "device": {
    "hostname": "core-sw-01"
  },
  "openconfig-acl:acl": {
    "acl-sets": {
      "acl-set": [
        {
          "name": "WEB_TRAFFIC_ACL",
          "type": "ACL_IPV4",
          "config": {
            "name": "WEB_TRAFFIC_ACL",
            "type": "ACL_IPV4"
          },
          "acl-entries": {
            "acl-entry": [
              {
                "sequence-id": 10,
                "config": {
                  "sequence-id": 10
                },
                "ipv4": {
                  "config": {
                    "source-address": "any",
                    "destination-address": "192.168.10.0/24",
                    "protocol": "tcp",
                    "destination-port": "80"
                  }
                },
                "actions": {
                  "config": {
                    "forwarding-action": "ACCEPT"
                  }
                }
              }
            ]
          }
        }
      ]
    }
  }
}
```

#### VLAN Configuration Example (OpenConfig - All Modern Devices)
```json
{
  "device": {
    "hostname": "core-sw-02"
  },
  "openconfig-vlan:vlans": {
    "vlan": [
      {
        "vlan-id": 100,
        "config": {
          "vlan-id": 100,
          "name": "PRODUCTION_VLAN",
          "status": "ACTIVE"
        }
      }
    ]
  }
}
```

### Juniper JunOS Devices (OpenConfig Native)
- **OS Type:** `juniper-junos`
- **Required Format:** **OpenConfig**
- **Description:** JunOS has native OpenConfig support and expects standard OpenConfig format

#### BGP Configuration Example (Juniper JunOS)
```json
{
  "device": {
    "hostname": "edge-rtr-01"
  },
  "routing": {
    "bgp": {
      "global": {
        "config": {
          "as": 65001,
          "router-id": "10.0.0.1"
        }
      },
      "neighbors": []
    }
  }
}
```

#### Interface Configuration Example (Juniper JunOS)
```json
{
  "device": {
    "hostname": "edge-rtr-01"
  },
  "openconfig-interfaces:interfaces": {
    "interface": [
      {
        "name": "ge-0/0/0",
        "config": {
          "name": "ge-0/0/0",
          "description": "Uplink interface",
          "enabled": true
        }
      }
    ]
  }
}
```

## Key Structural Patterns

### OpenConfig Structure Characteristics

| Configuration Object | OpenConfig Pattern | Key Features |
|----------------------|-------------------|--------------|
| **BGP AS Number** | `routing.bgp.global.config.as` | Nested under global config |
| **BGP Router-ID** | `routing.bgp.global.config.router-id` | Hyphenated key names |
| **OSPF Router-ID** | `routing.ospf.global.config.router-id` | Consistent global config pattern |
| **Interfaces** | `openconfig-interfaces:interfaces.interface[]` | Namespace prefix, array structure |
| **VLANs** | `openconfig-vlan:vlans.vlan[]` | Namespace prefix, array of VLAN objects |
| **ACLs** | `openconfig-acl:acl.acl-sets.acl-set[]` | Complex nested structure with entries |

### Common Validation Errors and Fixes

#### ❌ Wrong: Vendor-native structure (now discouraged)
```json
{
  "routing": {
    "bgp": {
      "as_number": 65001,
      "router_id": "10.0.0.1"
    }
  }
}
```

#### ✅ Correct: OpenConfig structure (preferred)
```json
{
  "routing": {
    "bgp": {
      "global": {
        "config": {
          "as": 65001,
          "router-id": "10.0.0.1"
        }
      }
    }
  }
}
```

#### ❌ Wrong: Simple interface structure
```json
{
  "interfaces": {
    "GigabitEthernet1/0/1": {
      "description": "Connection",
      "ip_address": "10.0.1.1/24"
    }
  }
}
```

#### ✅ Correct: OpenConfig interface structure
```json
{
  "openconfig-interfaces:interfaces": {
    "interface": [
      {
        "name": "GigabitEthernet1/0/1",
        "config": {
          "name": "GigabitEthernet1/0/1",
          "description": "Connection",
          "enabled": true
        },
        "subinterfaces": {
          "subinterface": [
            {
              "index": 0,
              "ipv4": {
                "addresses": {
                  "address": [
                    {
                      "ip": "10.0.1.1",
                      "config": {
                        "ip": "10.0.1.1",
                        "prefix-length": 24
                      }
                    }
                  ]
                }
              }
            }
          ]
        }
      }
    ]
  }
}
```

## Validation Process

The platform automatically validates your proposed configuration format:

1. **Format Detection**: Checks for OpenConfig vs vendor-native patterns
2. **Structure Validation**: Compares against expected OpenConfig format for the device OS type
3. **Detailed Error Messages**: Provides specific guidance when format is incorrect
4. **Format Examples**: Shows correct OpenConfig structure for your device type

### Sample Validation Error (Vendor-Native Rejected)
```
Proposed configuration structure validation failed:
• Device OS type 'arista-eos' expects OpenConfig format, but proposed config appears to use vendor-native structure
• BGP configuration uses vendor-native structure (as_number) but OpenConfig nested format expected (global.config.as)

Expected Format Help:
OS Type: arista-eos
Preferred Format: openconfig
Guidance: For arista-eos devices, use openconfig format. See structure_examples for proper format.
```

## Benefits of OpenConfig Standardization

### 1. **Vendor Agnostic**
- Same configuration structure works across Cisco, Arista, Juniper, and other vendors
- No need to learn different formats for different platforms

### 2. **Future Proof**
- Based on industry-standard YANG models
- Aligned with network automation trends and tooling

### 3. **Tool Compatibility** 
- Works with modern network automation frameworks
- Compatible with Ansible, Terraform, and other Infrastructure as Code tools

### 4. **Consistency**
- Uniform path structures (`global.config.*`)
- Standardized namespace prefixes (`openconfig-*:`)
- Predictable array and object patterns

## Best Practices

### 1. **Always Use OpenConfig**
- Start with OpenConfig format for all modern devices
- Only use vendor-native for legacy systems that don't support OpenConfig

### 2. **Follow Namespace Conventions**
- Use `openconfig-interfaces:interfaces` for interface configuration
- Use `openconfig-vlan:vlans` for VLAN configuration  
- Use `openconfig-acl:acl` for access control lists

### 3. **Understand Nested Structures**
- Most configuration goes under `global.config` objects
- Interface configuration uses `interface[].config` pattern
- List objects use array syntax with proper identifiers

### 4. **Validate Early**
- The platform will catch format errors before processing
- Fix format issues to get accurate before/after analysis

### 5. **Reference Current Examples**
- Check existing test files in `./tests/` for format examples
- Use configuration format validation to guide proper structure

## Troubleshooting Format Issues

### Issue: "Vendor-native structure detected but OpenConfig expected"
**Solution:** Convert to OpenConfig nested structure with proper config objects and namespace prefixes.

### Issue: "Missing namespace prefixes"
**Solution:** Add proper OpenConfig namespace prefixes like `openconfig-interfaces:`, `openconfig-vlan:`, etc.

### Issue: "Incorrect nested structure"
**Solution:** Use proper `global.config` nesting for routing protocols and `config` objects for interfaces.

### Issue: "Unknown OS type"
**Solution:** Ensure your device is properly defined in the inventory file with a supported OS type.

## Getting Device Information

To check your device's expected format:

```bash
# Check device inventory
cat data/inventory/inventory.csv | grep your-hostname

# Run analysis to see format validation
uv run python src/cli/main.py analyze config ./your-proposed-config.json --device your-hostname --mode partial
```

## Supported Configuration Objects

The platform validates and analyzes these configuration object types in OpenConfig format:

- **Routing Protocols**: BGP (`routing.bgp.global.config.*`), OSPF (`routing.ospf.global.config.*`)
- **Interfaces**: Physical, logical, VLAN interfaces (`openconfig-interfaces:interfaces.interface[]`)
- **Access Control**: ACLs (`openconfig-acl:acl.acl-sets.acl-set[]`)
- **VLANs**: VLAN configuration (`openconfig-vlan:vlans.vlan[]`)
- **QoS**: Quality of service policies (`openconfig-qos:qos`)
- **System**: Management settings using appropriate OpenConfig models

Each object type follows standardized OpenConfig YANG model structure regardless of the underlying vendor platform.

---

For additional help or to report format validation issues, please refer to the main project documentation or create an issue in the project repository.