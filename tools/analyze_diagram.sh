#!/bin/bash
# Test pipeline: Render Mermaid diagram and analyze SVG structure
# Purpose: Debug state highlighting issues by examining actual SVG coordinates and structure
#
# Usage: ./analyze_diagram.sh <config.yaml> <state_name> <event_name>
# Example: ./analyze_diagram.sh examples/face_processor.yaml scaling_image image_scaled

set -e

CONFIG_FILE=$1
STATE_NAME=$2
EVENT_NAME=$3

if [ -z "$CONFIG_FILE" ] || [ -z "$STATE_NAME" ]; then
    echo "Usage: $0 <config.yaml> <state_name> [event_name]"
    echo ""
    echo "Example:"
    echo "  $0 config/face_processor.yaml scaling_image image_scaled"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TEMP_DIR=$(mktemp -d)

echo "═══════════════════════════════════════════════════════════"
echo "  Mermaid Diagram Analysis Pipeline"
echo "═══════════════════════════════════════════════════════════"
echo "Config:   $CONFIG_FILE"
echo "State:    $STATE_NAME"
echo "Event:    ${EVENT_NAME:-<none>}"
echo "Temp dir: $TEMP_DIR"
echo ""

# Step 1: Generate Mermaid diagram from config
echo "──────────────────────────────────────────────────────────"
echo "Step 1: Generating Mermaid diagram from config..."
echo "──────────────────────────────────────────────────────────"

cd "$PROJECT_ROOT"
python3 - <<EOF > "$TEMP_DIR/diagram.mmd"
import sys
import yaml
from pathlib import Path

config_path = Path("$CONFIG_FILE")
if not config_path.exists():
    print(f"Error: Config file not found: {config_path}", file=sys.stderr)
    sys.exit(1)

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Generate Mermaid stateDiagram-v2
print("stateDiagram-v2")

states = config.get('states', {})
initial_state = config.get('initial_state', 'START')
final_states = config.get('final_states', [])

# Detect composite states
composites = {name: data for name, data in states.items() 
              if isinstance(data, dict) and data.get('type') == 'composite'}

# Generate main diagram
print(f"    [*] --> {initial_state}")

for state_name in states.keys():
    if state_name in composites:
        # Composite state
        print(f"    state {state_name} {{")
        substates = composites[state_name].get('states', {})
        sub_initial = composites[state_name].get('initial_state')
        if sub_initial:
            print(f"        [*] --> {sub_initial}")
        
        for substate_name, substate_data in substates.items():
            if isinstance(substate_data, dict):
                transitions = substate_data.get('on', {})
                for event, target in transitions.items():
                    print(f"        {substate_name} --> {target} : {event}")
        
        print(f"    }}")
    else:
        # Regular state
        state_data = states[state_name]
        if isinstance(state_data, dict):
            transitions = state_data.get('on', {})
            for event, target in transitions.items():
                print(f"    {state_name} --> {target} : {event}")

for final_state in final_states:
    print(f"    {final_state} --> [*]")
EOF

if [ ! -s "$TEMP_DIR/diagram.mmd" ]; then
    echo "Error: Failed to generate Mermaid diagram"
    exit 1
fi

echo "✓ Generated diagram:"
cat "$TEMP_DIR/diagram.mmd"
echo ""

# Step 2: Render to SVG using mermaid-cli
echo "──────────────────────────────────────────────────────────"
echo "Step 2: Rendering diagram to SVG with mermaid-cli..."
echo "──────────────────────────────────────────────────────────"

# Check if mmdc is installed
if ! command -v mmdc &> /dev/null; then
    echo "Error: mermaid-cli (mmdc) not found"
    echo "Install it with: npm install -g @mermaid-js/mermaid-cli"
    exit 1
fi

mmdc -i "$TEMP_DIR/diagram.mmd" -o "$TEMP_DIR/diagram.svg" -t default

if [ ! -f "$TEMP_DIR/diagram.svg" ]; then
    echo "Error: SVG generation failed"
    exit 1
fi

echo "✓ SVG generated ($(wc -c < "$TEMP_DIR/diagram.svg") bytes)"
echo ""

# Step 3: Analyze SVG structure
echo "──────────────────────────────────────────────────────────"
echo "Step 3: Analyzing SVG structure..."
echo "──────────────────────────────────────────────────────────"

python3 - <<EOF
import xml.etree.ElementTree as ET
import re
import sys

svg_path = "$TEMP_DIR/diagram.svg"
state_name = "$STATE_NAME"
event_name = "$EVENT_NAME"

# Parse SVG
tree = ET.parse(svg_path)
root = tree.getroot()

# Use namespace-agnostic iteration (Mermaid uses default xmlns)
SVG_NS = '{http://www.w3.org/2000/svg}'
HTML_NS = '{http://www.w3.org/1999/xhtml}'

print("═══ SVG Structure Analysis ═══\n")

# Find all state nodes
print("📦 State Nodes:")
print("-" * 60)

state_nodes = []
for elem in root.iter():
    # Match 'g' elements regardless of namespace
    elem_tag = elem.tag.replace(SVG_NS, '') if SVG_NS in elem.tag else elem.tag
    if elem_tag == 'g':
        class_attr = elem.get('class', '')
        if class_attr and ('node' in class_attr or 'statediagram-state' in class_attr):
            # Extract state name from text or foreignObject
            name = None
            # Search descendants for text content
            for child in elem.iter():
                # Strip both SVG and HTML namespaces
                child_tag = child.tag.replace(SVG_NS, '').replace(HTML_NS, '')
                # Check for text in <p> element (inside foreignObject with HTML namespace)
                if child_tag == 'p':
                    # Use itertext() to get all text content
                    text = ''.join(child.itertext()).strip()
                    if text:
                        name = text
                        break
                # Fallback to <text> element
                elif child_tag == 'text' and child.text:
                    name = child.text.strip()
            
            if name:
                node_id = elem.get('id', '')
                transform = elem.get('transform', '')
                
                # Extract coordinates from transform
                coords = re.search(r'translate\(([\d.-]+),\s*([\d.-]+)\)', transform)
                x, y = coords.groups() if coords else ('?', '?')
                
                state_nodes.append({
                    'name': name,
                    'id': node_id,
                    'class': class_attr,
                    'x': x,
                    'y': y
                })
                
                highlight = "👉 TARGET" if name == state_name else ""
                print(f"  • {name:30} id={node_id:30} at ({x:>6}, {y:>6}) {highlight}")

print(f"\nTotal state nodes: {len(state_nodes)}")
print()

# Find all edges (transitions)
print("🔀 Transitions (Edges):")
print("-" * 60)

edges = []
# Find edge label groups
for elem in root.iter():
    elem_tag = elem.tag.replace(SVG_NS, '') if SVG_NS in elem.tag else elem.tag
    if elem_tag == 'g':
        class_attr = elem.get('class', '')
        if class_attr == 'label':
            # Check if parent is edgeLabels group
            parent_class = ''
            parent = elem.getparent() if hasattr(elem, 'getparent') else None
            if parent is not None:
                parent_tag = parent.tag.replace(SVG_NS, '') if SVG_NS in parent.tag else parent.tag
                if parent_tag == 'g':
                    parent_class = parent.get('class', '')
            
            if parent_class == 'edgeLabels':
                # Get event name from label
                event = None
                for child in elem.iter():
                    # Strip both SVG and HTML namespaces
                    child_tag = child.tag.replace(SVG_NS, '').replace(HTML_NS, '')
                    if child_tag == 'p':
                        # Use itertext() to get all text content
                        text = ''.join(child.itertext()).strip()
                        if text:
                            event = text
                            break
                
                if event:
                    data_id = elem.get('data-id', '')
                    
                    # Find corresponding path
                    path_elem = None
                    for p in root.iter():
                        p_tag = p.tag.replace(SVG_NS, '') if SVG_NS in p.tag else p.tag
                        if p_tag == 'path' and p.get('data-id') == data_id:
                            path_elem = p
                            break
                    
                    if path_elem is not None:
                        path_id = path_elem.get('id', '')
                        d_attr = path_elem.get('d', '')
                        
                        # Extract start/end coordinates from path
                        coords = re.findall(r'M([\d.-]+),([\d.-]+)', d_attr)
                        start = coords[0] if coords else ('?', '?')
                        
                        edges.append({
                            'event': event,
                            'data_id': data_id,
                            'path_id': path_id,
                            'start': start
                        })
                        
                        highlight = "👉 TARGET" if event == event_name else ""
                        print(f"  • {event:30} data-id={data_id:20} path-id={path_id:20} {highlight}")

print(f"\nTotal transitions: {len(edges)}")
print()

# Analysis for target state
print("═══ Target State Analysis ═══\n")
target_state = next((s for s in state_nodes if s['name'] == state_name), None)

if target_state:
    print(f"✓ Found state: {state_name}")
    print(f"  ID:      {target_state['id']}")
    print(f"  Class:   {target_state['class']}")
    print(f"  Position: ({target_state['x']}, {target_state['y']})")
    print()
    
    # Check if it's in a composite
    parent = None
    for elem in root.iter():
        elem_tag = elem.tag.replace(SVG_NS, '') if SVG_NS in elem.tag else elem.tag
        if elem_tag == 'g':
            class_attr = elem.get('class', '')
            if 'statediagram-cluster' in class_attr or 'cluster' in class_attr:
                # Check if our state is inside this cluster
                found = False
                for child in elem.iter():
                    if child.get('id') == target_state['id']:
                        found = True
                        break
                
                if found:
                    # Find cluster name
                    for text_elem in elem.iter():
                        text_tag = text_elem.tag.replace(SVG_NS, '') if SVG_NS in text_elem.tag else text_elem.tag
                        if text_tag == 'text' and text_elem.text:
                            parent = text_elem.text.strip()
                            print(f"  ⚠️  State is INSIDE composite: {parent}")
                            print(f"     → On main diagram, should highlight composite, not state")
                            print()
                            break
                    if parent:
                        break
else:
    print(f"✗ State not found: {state_name}")
    print(f"  Available states: {', '.join(s['name'] for s in state_nodes)}")
    print()

# Analysis for target event
if event_name:
    print("═══ Target Event Analysis ═══\n")
    target_event = next((e for e in edges if e['event'] == event_name), None)
    
    if target_event:
        print(f"✓ Found event: {event_name}")
        print(f"  data-id: {target_event['data_id']}")
        print(f"  path-id: {target_event['path_id']}")
        print(f"  Start:   ({target_event['start'][0]}, {target_event['start'][1]})")
        print()
    else:
        print(f"✗ Event not found: {event_name}")
        print(f"  Available events: {', '.join(e['event'] for e in edges)}")
        print()

# Generate enrichment recommendations
print("═══ Enrichment Recommendations ═══\n")

if target_state:
    print(f"To enrich state node for fast highlighting:")
    print(f"  querySelector: g[id='{target_state['id']}']")
    print(f"  setAttribute:  data-state-id='{state_name}'")
    print()

if event_name and target_event:
    print(f"To enrich transition edge for arrow highlighting:")
    print(f"  querySelector: path[data-id='{target_event['data_id']}']")
    print(f"  setAttribute:  data-edge-event='{event_name}'")
    print()

print("═══════════════════════════════════════════════════════════")
EOF

# Step 4: Save results
echo ""
echo "──────────────────────────────────────────────────────────"
echo "Step 4: Results saved"
echo "──────────────────────────────────────────────────────────"
echo "Mermaid diagram: $TEMP_DIR/diagram.mmd"
echo "SVG output:      $TEMP_DIR/diagram.svg"
echo ""
echo "To inspect SVG visually:"
echo "  open $TEMP_DIR/diagram.svg"
echo ""
echo "To keep files, copy from:"
echo "  cp $TEMP_DIR/* /desired/location/"
echo ""
