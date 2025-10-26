# SDXLGENERATIONPHASE SVG Structure Analysis

## Source
Captured from production UI on 2025-10-26

## Diagram Metadata
- Diagram Type: statediagram
- Mermaid ID: mermaid-1761506845500
- Classes: node, statediagram-state

## State Nodes Found

### state-switching_to_sdxl-1
### state-enhancing_prompt-3
### state-updating_job_prompt-5
### state-generating_fallback_image-7
### state-generating_enhanced_image-6
### state-early_face_detection-9
### state-scaling_image-10
### state-COMPLETIONPHASE-10

## Text Content Extraction

                <g class="node  statediagram-state" id="state-switching_to_sdxl-1"	                <g class="node  statediagram-state" id="state-enhancing_prompt-3"
                <g class="node  statediagram-state" id="state-updating_job_prompt-5"	                <g class="node  statediagram-state" id="state-generating_fallback_image-7"
                <g class="node  statediagram-state" id="state-generating_enhanced_image-6"	                <g class="node  statediagram-state" id="state-early_face_detection-9"
                <g class="node  statediagram-state" id="state-scaling_image-10"	                <g class="node  statediagram-state" id="state-COMPLETIONPHASE-10"

## Key Observations

1. **Node Class Pattern**: All nodes have `class="node  statediagram-state"` (note: double space)
2. **ID Pattern**: `state-{name}-{number}` format
3. **Text Content**: Inside `<p>` tags within foreignObject
4. **Selector**: Should match `g.node, g.statediagram-state`

## Issues Found

- Node IDs don't always match state names directly
- Text content is in nested foreignObject > div > span > p structure
- Some nodes have unexpected IDs (e.g., COMPLETIONPHASE instead of a single state)

