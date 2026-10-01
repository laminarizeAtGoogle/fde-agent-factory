
import sys
import os
import json
from unittest.mock import MagicMock

# Add script directory
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    from markdown_converter import MarkdownConverter
    from docs_cli import find_table_at_index, process_table_content
except ImportError as e:
    print(f"ImportError: {e}")
    print("Please ensure you are running this from the correct directory or have dependencies installed.")
    sys.exit(1)

def verify():
    print("Verifying Google Docs Skill Logic...")
    
    markdown_sample = """
# Title
This is a **bold** paragraph with a [link](https://google.com).

## List
1. First item
2. Second item

## Table
| Header 1 | Header 2 |
| --- | --- |
| Cell 1 | Cell 2 |
| Cell 3 | Cell 4 |

End of doc.
    """
    
    settings = {
        "primaryAccentColor": "#4285f4",
        "useAlternatingRowColors": True
    }
    
    print("Initializing converter...")
    converter = MarkdownConverter(settings)
    
    print("Converting markdown...")
    blueprints = converter.convert(markdown_sample)
    print(f"Generated {len(blueprints)} blueprints.")
    
    current_index = 1
    current_blueprints = blueprints
    
    # Mocking service for table check
    mock_service = MagicMock()
    
    while True:
        result = converter.generate_requests(current_blueprints, start_index=current_index)
        
        print(f"Batch Type: {result['type']}")
        print(f"Requests Count: {len(result['requests'])}")
        
        for req in result['requests']:
            if 'insertText' in req:
                print(f"  [InsertText] idx={req['insertText']['location']['index']} len={len(req['insertText']['text'])}")
            elif 'updateParagraphStyle' in req:
                print(f"  [UpdateParagraphStyle] range={req['updateParagraphStyle']['range']['startIndex']}-{req['updateParagraphStyle']['range']['endIndex']}")
        
        if result['type'] == 'complete':
            break
            
        if result['type'] == 'table_break':
            blueprint = result['blueprint']
            print(f"  [TableBreak] Inserting table at {result['current_index']}")
            
            # Simulate table insertion
            # We need to simulate the table structure being present for population
            # Construct a fake table element
            rows = len(blueprint['rows']) + (1 if blueprint['header'] else 0)
            cols = len(blueprint['header']) if blueprint['header'] else (len(blueprint['rows'][0]) if blueprint['rows'] else 0)
            
            # Fake logic: table start index is at insertion point
            table_start = result['current_index'] + 1 # +1 for table start char?
            
            fake_table = {
                'startIndex': table_start,
                'endIndex': table_start + 100, # Fake length
                'table': {
                    'tableRows': []
                }
            }
            
            # Create fake cells
            current_cell_idx = table_start + 2
            for r in range(rows):
                row_cells = []
                for c in range(cols):
                    row_cells.append({
                        'content': [{'startIndex': current_cell_idx}]
                    })
                    current_cell_idx += 10 # Fake cell content length
                fake_table['table']['tableRows'].append({'tableCells': row_cells})
            
            print(f"  [Mock] Generated fake table structure with {rows} rows, {cols} cols.")
            
            # Process table
            table_reqs = process_table_content(mock_service, 'dummy_id', fake_table, blueprint, converter, settings)
            print(f"  [TablePopulation] Generated {len(table_reqs)} requests for table cells.")
            
            current_index = fake_table['endIndex']
            current_blueprints = result['remaining_blueprints']
            if not current_blueprints:
                break
                
    print("\nVerification Complete: Logic seems sound.")

if __name__ == '__main__':
    verify()
