# Presentation Skill Workflows

This document contains the detailed step-by-step workflows for creating presentations using the `presentation-skill`.

## Workflow A: Using the Default Google Template

**Location**: `~/.agentss/skills/presentation-skill/resources/template.pptx`
**Total Slides**: 48 (indexed 0-47)

### Step 1: Extract and Analyze Template
```bash
SKILL_PATH=~/.agentss/skills/presentation-skill
python -m markitdown $SKILL_PATH/resources/template.pptx > template-content.md
python $SKILL_PATH/scripts/cli.py thumbnail $SKILL_PATH/resources/template.pptx template-thumbnails --cols 5
```

### Step 2: Create Template Mapping
Create an outline mapping content to template slide indices (0-47).
Example: `2,3,7,12,13,7,12`

### Step 3: Rearrange Template Slides
```bash
python $SKILL_PATH/scripts/cli.py rearrange $SKILL_PATH/resources/template.pptx working.pptx 2,3,7,12,13,7,12
```

### Step 4: Extract Text Inventory
```bash
python $SKILL_PATH/scripts/cli.py inventory working.pptx text-inventory.json
```
Read `text-inventory.json` carefully to understand available shapes and formatting.

### Step 5: Generate Replacement Text
Create `replacement-text.json`. Critical Rules:
1. Only reference shapes found in the inventory.
2. Copy formatting properties (bold, alignment) from the inventory.
3. Use `"bullet": true, "level": 0` for bullets.

Example:
```json
{
  "slide-0": {
    "shape-0": {
      "paragraphs": [{"text": "Title", "bold": true}]
    }
  }
}
```

### Step 6: Apply Replacements
```bash
python $SKILL_PATH/scripts/cli.py replace working.pptx replacement-text.json output.pptx --cleanup
```

---

## Workflow B: Using a Custom User Template

### Step 1: Analyze Custom Template
```bash
SKILL_PATH=~/.agentss/skills/presentation-skill
python -m markitdown user-template.pptx > template-analysis.md
python $SKILL_PATH/scripts/cli.py thumbnail user-template.pptx template-thumbnails --cols 5
python $SKILL_PATH/scripts/cli.py analyze user-template.pptx
```

### Step 2: Create Template Mapping
Identify slide indices from the analysis and map them to the new presentation outline.

### Step 3: Rearrange
```bash
python $SKILL_PATH/scripts/cli.py rearrange user-template.pptx working.pptx 0,1,2,3,4,2,3
```

### Step 4: Inventory & Replace
Follow the exact same inventory extraction and text replacement steps as Workflow A (Steps 4-6).

---

## Common Errors
- **Slide index out of range**: You used an index outside the boundaries of the template length.
- **Shape not found**: Read `text-inventory.json` again. You referenced a shape that doesn't exist on that slide layout.
- **Text overflow**: Your replacement text is too long for the shape block. Shorten the text.
