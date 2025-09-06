"""
Working yangson leafref extractor using successfully loading modules.
Focus on extracting leafrefs from modules that actually load, rather than trying to load everything.
"""
import os
import json
from yangson import DataModel
from yangson.datatype import LeafrefType
from typing import List, Dict

def _verbose_print(*args, **kwargs):
    """Print only if TRUE_SCHEMA_VERBOSE environment variable is set."""
    if os.environ.get('TRUE_SCHEMA_VERBOSE'):
        print(*args, **kwargs)

class WorkingYangsonLeafrefExtractor:
    """
    Working yangson leafref extractor using modules that successfully load.
    """
    
    def __init__(self):
        self.data_model = None
        
    def load_working_yang_model(self) -> bool:
        """Load yangson DataModel with working module set."""
        
        _verbose_print("🔧 Loading WORKING yangson DataModel...")
        _verbose_print("   Testing with OpenConfig ACL and interfaces modules (fixed openconfig-defined-sets)")
        
        # Working set optimized for comprehensive protocol leafref detection
        working_library = {
            "ietf-yang-library:modules-state": {
                "module-set-id": "comprehensive-working-set",
                "module": [
                    {
                        "name": "ietf-yang-types",
                        "namespace": "urn:ietf:params:xml:ns:yang:ietf-yang-types",
                        "revision": "2013-07-15",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "ietf-inet-types",
                        "namespace": "urn:ietf:params:xml:ns:yang:ietf-inet-types",
                        "revision": "2013-07-15",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "ietf-interfaces",
                        "namespace": "urn:ietf:params:xml:ns:yang:ietf-interfaces",
                        "revision": "2014-05-08",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-extensions",
                        "namespace": "http://openconfig.net/yang/openconfig-ext",
                        "revision": "2024-09-19",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-types",
                        "namespace": "http://openconfig.net/yang/openconfig-types",
                        "revision": "2024-01-31",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-yang-types",
                        "namespace": "http://openconfig.net/yang/types/yang",
                        "revision": "2024-05-30",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-inet-types",
                        "namespace": "http://openconfig.net/yang/types/inet",
                        "revision": "2024-01-05",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-mpls-types",
                        "namespace": "http://openconfig.net/yang/mpls-types",
                        "revision": "2023-12-14",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-transport-types",
                        "namespace": "http://openconfig.net/yang/transport-types",
                        "revision": "2019-06-27",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-platform-types",
                        "namespace": "http://openconfig.net/yang/platform-types",
                        "revision": "2025-07-09",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-interfaces",
                        "namespace": "http://openconfig.net/yang/interfaces",
                        "revision": "2024-12-05",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-defined-sets",
                        "namespace": "http://openconfig.net/yang/routing-policy/defined-sets",
                        "revision": "2024-01-01",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-icmpv4-types",
                        "namespace": "http://openconfig.net/yang/openconfig-icmpv4-types",
                        "revision": "2023-01-26",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-icmpv6-types",
                        "namespace": "http://openconfig.net/yang/openconfig-icmpv6-types",
                        "revision": "2023-05-02",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-packet-match-types",
                        "namespace": "http://openconfig.net/yang/packet-match-types",
                        "revision": "2023-01-29",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-packet-match",
                        "namespace": "http://openconfig.net/yang/header-fields",
                        "revision": "2023-03-01",
                        "conformance-type": "implement"
                    },
                    {
                        "name": "openconfig-acl",
                        "namespace": "http://openconfig.net/yang/acl",
                        "revision": "2023-02-06",
                        "conformance-type": "implement"
                    }
                ]
            }
        }
        
        library_json = json.dumps(working_library)
        
        # Use absolute paths relative to script location to fix yangson "404: Not Found" error
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up from src/analysis/schema_analyzer/ to project root
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        
        mod_paths = (
            os.path.join(project_root, "models", "yang", "openconfig", "common"),
            os.path.join(project_root, "models", "yang", "ietf-standard"),
            os.path.join(project_root, "models", "yang", "openconfig", "acl"),
            os.path.join(project_root, "models", "yang", "openconfig", "bgp"),
            os.path.join(project_root, "models", "yang", "openconfig", "interfaces"),
            os.path.join(project_root, "models", "yang", "openconfig", "ospf"),
            os.path.join(project_root, "models", "yang", "openconfig", "policy"),
            os.path.join(project_root, "models", "yang", "openconfig", "vlan")
        )
        
        try:
            _verbose_print(f"   🔍 Loading {len(working_library['ietf-yang-library:modules-state']['module'])} modules...")
            self.data_model = DataModel(library_json, mod_path=mod_paths)
            
            _verbose_print(f"   ✅ SUCCESS: Working yangson DataModel loaded")
            return True
            
        except Exception as e:
            _verbose_print(f"   ❌ FAILED: {e}")
            return False
    
    def extract_all_leafrefs(self) -> List[Dict]:
        """Extract ALL leafrefs from the working yangson model."""
        
        if not self.data_model:
            _verbose_print("❌ No yangson DataModel loaded")
            return []
        
        _verbose_print(f"\n🔍 Extracting ALL leafrefs from working yangson model...")
        
        leafrefs = []
        
        try:
            schema_root = self.data_model.schema
            self._comprehensive_leafref_search(schema_root, "", leafrefs)
            
        except Exception as e:
            _verbose_print(f"❌ Error during leafref extraction: {e}")
            import traceback
            traceback.print_exc()
        
        _verbose_print(f"📊 Extracted {len(leafrefs)} leafrefs from working model")
        return leafrefs
    
    def _comprehensive_leafref_search(self, node, path: str, leafrefs: List[Dict]):
        """Comprehensive search for leafrefs in yangson schema."""
        
        try:
            # Check if this node has leafref type
            if hasattr(node, 'type') and node.type is not None:
                if isinstance(node.type, LeafrefType):
                    
                    # Extract target path from LeafrefType
                    target_path = str(node.type.path) if hasattr(node.type, 'path') else "unknown"
                    description = getattr(node, 'description', '')
                    
                    leafref_info = {
                        'source_path': path,
                        'target_path': target_path,
                        'description': description,
                        'node_type': str(type(node)),
                        'yang_type': str(type(node.type))
                    }
                    
                    leafrefs.append(leafref_info)
                    _verbose_print(f"   ✅ LEAFREF: {path}")
                    _verbose_print(f"      → Target: {target_path}")
                    if description:
                        _verbose_print(f"      → Description: {description[:60]}...")
            
            # Traverse all children recursively
            if hasattr(node, 'data_children'):
                try:
                    for child in node.data_children():
                        child_name = getattr(child, 'name', '') or getattr(child, 'qual_name', '')
                        if child_name:
                            child_path = f"{path}/{child_name}" if path else child_name
                            self._comprehensive_leafref_search(child, child_path, leafrefs)
                except Exception as e:
                    _verbose_print(f"      Error traversing children of {path}: {e}")
                    pass
                    
        except Exception as e:
            _verbose_print(f"   Error processing node {path}: {e}")
            pass
    
    def analyze_leafref_relationships(self, leafrefs: List[Dict]) -> Dict:
        """Analyze the leafref relationships found."""
        
        if not leafrefs:
            return {}
        
        _verbose_print(f"\n📊 ANALYZING {len(leafrefs)} leafref relationships...")
        
        analysis = {
            'total_leafrefs': len(leafrefs),
            'by_module': {},
            'relationship_types': {},
            'target_patterns': {}
        }
        
        for leafref in leafrefs:
            source = leafref['source_path']
            target = leafref['target_path']
            
            # Analyze by module (extract from path)
            source_module = source.split('/')[0] if '/' in source else source
            if source_module not in analysis['by_module']:
                analysis['by_module'][source_module] = 0
            analysis['by_module'][source_module] += 1
            
            # Analyze relationship types
            if target.startswith('../'):
                rel_type = 'relative_parent'
            elif target.startswith('/'):
                rel_type = 'absolute_path'
            else:
                rel_type = 'other'
                
            if rel_type not in analysis['relationship_types']:
                analysis['relationship_types'][rel_type] = 0
            analysis['relationship_types'][rel_type] += 1
            
            # Analyze target patterns
            target_key = target.replace('../', '').replace('/', '_')
            if target_key not in analysis['target_patterns']:
                analysis['target_patterns'][target_key] = 0
            analysis['target_patterns'][target_key] += 1
        
        _verbose_print(f"   📋 Analysis summary:")
        _verbose_print(f"      Total leafrefs: {analysis['total_leafrefs']}")
        _verbose_print(f"      By module: {analysis['by_module']}")
        _verbose_print(f"      Relationship types: {analysis['relationship_types']}")
        _verbose_print(f"      Target patterns: {list(analysis['target_patterns'].keys())}")
        
        return analysis

def test_working_yangson_leafref_extraction():
    """Test working yangson leafref extraction."""
    
    _verbose_print("🚀 WORKING YANGSON LEAFREF EXTRACTION")
    _verbose_print("=" * 60)
    _verbose_print("Focus on successfully loading modules and extracting their leafrefs")
    
    extractor = WorkingYangsonLeafrefExtractor()
    
    # Load working model
    if not extractor.load_working_yang_model():
        _verbose_print("❌ Cannot proceed - working model loading failed")
        return
    
    # Extract leafrefs
    leafrefs = extractor.extract_all_leafrefs()
    
    if leafrefs:
        _verbose_print(f"\n🎉 SUCCESS: Extracted {len(leafrefs)} leafrefs!")
        
        # Show detailed leafref information
        for i, leafref in enumerate(leafrefs, 1):
            _verbose_print(f"\n   Leafref {i}:")
            _verbose_print(f"      Source: {leafref['source_path']}")
            _verbose_print(f"      Target: {leafref['target_path']}")
            _verbose_print(f"      Node Type: {leafref['node_type']}")
            _verbose_print(f"      YANG Type: {leafref['yang_type']}")
            if leafref['description']:
                _verbose_print(f"      Description: {leafref['description']}")
        
        # Analyze relationships
        analysis = extractor.analyze_leafref_relationships(leafrefs)
        
        _verbose_print(f"\n🎯 WORKING YANGSON LEAFREF EXTRACTION SUCCESS!")
        _verbose_print(f"   ✅ yangson DataModel loading: WORKING")
        _verbose_print(f"   ✅ yangson schema traversal: WORKING") 
        _verbose_print(f"   ✅ LeafrefType detection: WORKING")
        _verbose_print(f"   ✅ Leafref relationship extraction: WORKING")
        _verbose_print(f"   📊 Found {len(leafrefs)} TRUE schema-driven leafref relationships")
        
        return leafrefs
        
    else:
        _verbose_print(f"\n❌ No leafrefs extracted from working model")
        _verbose_print(f"   Model loaded successfully but leafref extraction failed")
        return []

def demonstrate_schema_driven_config_analysis(leafrefs: List[Dict]):
    """Demonstrate how these leafrefs could be used for config analysis."""
    
    if not leafrefs:
        return
    
    _verbose_print(f"\n🎯 DEMONSTRATION: Schema-Driven Configuration Analysis")
    _verbose_print("-" * 60)
    
    _verbose_print(f"With {len(leafrefs)} TRUE yangson leafrefs, we can now build:")
    _verbose_print(f"   • TRUE schema-driven dependency detection")
    _verbose_print(f"   • Configuration change impact analysis")
    _verbose_print(f"   • YANG model-based validation")
    
    _verbose_print(f"\nExample schema-driven analysis:")
    for leafref in leafrefs:
        source = leafref['source_path']
        target = leafref['target_path']
        
        _verbose_print(f"\n   If configuration changes: {source}")
        _verbose_print(f"   Then it affects: {target}")
        _verbose_print(f"   Dependency type: YANG leafref (schema-driven)")
        _verbose_print(f"   Analysis method: yangson schema introspection")

if __name__ == "__main__":
    leafrefs = test_working_yangson_leafref_extraction()
    
    if leafrefs:
        demonstrate_schema_driven_config_analysis(leafrefs)
        _verbose_print(f"\n✅ MISSION ACCOMPLISHED: Working yangson leafref extraction ACHIEVED!")
        _verbose_print(f"🎯 Ready to build TRUE schema-driven configuration analysis")
    else:
        _verbose_print(f"\n🔧 Still debugging leafref extraction from yangson schema")