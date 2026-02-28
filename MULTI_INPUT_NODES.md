# Multi-Input Nodes Feature

## Overview
The application now supports nodes that accept multiple input images with named slots. This enables advanced image processing operations that require multiple source images.

## Current Multi-Input Nodes

### Flat Field Correction
**Category:** Enhancement  
**Inputs:** 3 (labeled slots)  
**Purpose:** Correct uneven illumination in images using gain (bright field) and dark (dark field) calibration images.

**Input Slots:**
1. **projection** - The raw image to be corrected
2. **gain** - Bright field reference image (uniform bright field)
3. **dark** - Dark field reference image (camera dark current/noise)

**Formula:**
```
corrected = (projection - dark) / (gain - dark + epsilon)
```

**Parameters:**
- `epsilon` (default: 1e-6): Small value to prevent division by zero
- `input_type`: Currently unused in multi-input mode

## How to Use Multi-Input Nodes

### 1. Add Nodes to Canvas
- Drag 3 **Image Input** nodes from the palette
- Drag 1 **Flat Field Correction** node from the Enhancement category
- Drag 1 **Image Output** node

### 2. Upload Images
- Double-click each input node or click "Choose File" button
- Upload your projection, gain, and dark images
- Images will be automatically assigned to the input nodes

### 3. Connect Inputs
The Flat Field Correction node displays **three labeled input handles** on its left side:
- **projection** (top) - Connect your raw image here
- **gain** (middle) - Connect your bright field reference
- **dark** (bottom) - Connect your dark field reference

Simply drag edges from the output (right) of each input node to the corresponding labeled handle on the Flat Field Correction node.

### 4. Connect Output
- Connect the Flat Field Correction node's output (right handle) to the Output node's input

### 5. Execute Pipeline
- Click the "Execute Pipeline" button
- The corrected image will be displayed in the Image Preview panel

## Visual Indicators

### Multi-Input Handles
- **Color:** Orange (`#ff9800`)
- **Position:** Vertically distributed on the left side of the node
- **Labels:** Slot names displayed next to each handle
- **Hover Effect:** Handles glow when hovering to show connectivity

### Node Information
- Multi-input nodes show the number of parameters in the node card
- Double-click to view/edit parameters
- Labels are positioned inside the node boundary for clarity

## Technical Details

### Backend Processing
The pipeline executor automatically:
1. Detects multi-input nodes via `processor.multi_input` attribute
2. Maps source node IDs to slot names using `input_mapping` from edge data
3. Calls `processor.process_multi(images_dict, **kwargs)` with slot-keyed dictionary
4. Falls back to single-input `processor.process()` for standard nodes

### Frontend Handling
- CustomNode component renders multiple handles for multi-input nodes
- Edge `targetHandle` property stores the slot name
- Pipeline execution builds `input_mapping` dict from edges
- Node palette shows complete metadata including `input_slots` array

## Future Multi-Input Nodes

Planned additions:
- **Image Blending** - Blend multiple images with alpha channels
- **HDR Merge** - Combine multiple exposures into HDR image
- **Image Difference** - Subtract one image from another
- **Multi-Image Average** - Average stack of images for noise reduction
- **Color Channel Merge** - Combine separate R/G/B images into color image

## Troubleshooting

### Issue: Can't connect to specific slot
**Solution:** Make sure you're dragging to the correct colored handle. Orange handles indicate multi-input slots.

### Issue: Edge connects but processing fails
**Solution:** Verify that all required slots have connections. Check browser console for `input_mapping` debug output.

### Issue: Wrong image in wrong slot
**Solution:** Edges can be reconnected by dragging the arrow head. Drag from the orange handle to a different input node.

### Issue: Node doesn't show multiple handles
**Solution:** Check that the node metadata includes `multi_input: true` and `input_slots` array in the API response at `/api/nodes`.

## API Reference

### Node Metadata Structure (multi-input)
```json
{
  "id": "flat_field",
  "name": "Flat Field Correction",
  "type": "processor",
  "category": "Enhancement",
  "inputs": 3,
  "outputs": 1,
  "multi_input": true,
  "input_slots": ["projection", "gain", "dark"],
  "parameters": {
    "epsilon": {
      "type": "number",
      "default": 1e-6,
      "description": "Small value to prevent division by zero"
    }
  }
}
```

### Pipeline Execution Format
```json
{
  "nodes": [
    {
      "id": "flat_field-123456",
      "type": "flat_field",
      "data": {
        "epsilon": 1e-6,
        "input_mapping": {
          "projection": "input-111111",
          "gain": "input-222222",
          "dark": "input-333333"
        }
      }
    }
  ],
  "edges": [
    {
      "source": "input-111111",
      "target": "flat_field-123456",
      "targetHandle": "projection"
    },
    {
      "source": "input-222222",
      "target": "flat_field-123456",
      "targetHandle": "gain"
    },
    {
      "source": "input-333333",
      "target": "flat_field-123456",
      "targetHandle": "dark"
    }
  ]
}
```

## Implementation Notes

### Creating New Multi-Input Processors

To add a new multi-input processor:

1. **Backend (`basic_processors.py`):**
```python
class MyMultiInputProcessor(ImageProcessor):
    multi_input = True
    input_slots = ['image1', 'image2', 'image3']
    
    def __init__(self):
        self.name = "My Multi-Input Processor"
        self.description = "Process multiple images"
        self.parameters = {}
    
    def process_multi(self, images_dict, **kwargs):
        """
        images_dict: {'image1': cv2_img, 'image2': cv2_img, ...}
        """
        img1 = images_dict.get('image1')
        img2 = images_dict.get('image2')
        
        # Your processing logic here
        result = cv2.add(img1, img2)
        return result
```

2. **Register in `node_registry.py`:**
```python
from app.processors.basic_processors import MyMultiInputProcessor

class NodeRegistry:
    def __init__(self):
        self.processors = {
            # ... existing processors
            'my_multi_input': MyMultiInputProcessor(),
        }
```

3. **Add to categories:**
```python
processor_categories = {
    # ... existing categories
    'my_multi_input': 'Enhancement',
}
```

4. **Frontend automatically handles:**
   - Multiple handle rendering
   - Slot label display
   - Edge target mapping
   - Input mapping construction

No frontend changes needed - the system auto-detects multi-input nodes!
