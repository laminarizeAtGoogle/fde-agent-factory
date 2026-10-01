
import argparse
import json
import os
import sys
import os

# Add script directory to path to allow imports when run directly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from googleapiclient.discovery import build
try:
    from .utils import get_credentials, hex_to_rgb, is_color_dark
    from .markdown_converter import MarkdownConverter
except ImportError:
    from utils import get_credentials, hex_to_rgb, is_color_dark
    from markdown_converter import MarkdownConverter

def create_doc(title, service):
    body = {
        'title': title
    }
    doc = service.documents().create(body=body).execute()
    return doc.get('documentId')

def get_doc_content(service, document_id):
    return service.documents().get(documentId=document_id).execute()

def find_table_at_index(content, index):
    """
    Traverses the document content to find a table that starts at or just after the given index.
    In Google Docs, the table is an element.
    """
    for element in content.get('body', {}).get('content', []):
        if 'table' in element:
            # Table element has startIndex
             if element.get('startIndex') >= index:
                 return element
    return None

def process_table_content(service, document_id, table_element, blueprint, converter, settings):
    # This logic mirrors the JS generateTablePopulationRequests
    # We need to find cell start indices.
    
    cell_start_indices = []
    
    # Flatten rows to get cells in order
    for row in table_element.get('table', {}).get('tableRows', []):
        for cell in row.get('tableCells', []):
            # The content of a cell is a list of structural elements.
            # Usually it starts with a paragraph.
            if cell.get('content'):
                # We want the start index of the first paragraph's content to insert text
                # Actually we can insert at cell.content[0].startIndex
                # But we should check if it's empty.
                # Usually a cell has at least one paragraph with a newline.
                first_elem = cell['content'][0]
                cell_start_indices.append(first_elem['startIndex'])
            else:
                cell_start_indices.append(None)
    
    requests = []
    cell_counter = 0
    cumulative_offset = 0
    
    # helper to iterate blueprint rows
    all_rows = []
    if blueprint.get('header'):
        all_rows.append((blueprint['header'], True)) # row, is_header
    for r in blueprint.get('rows', []):
        all_rows.append((r, False))
        
    for row_idx, (row_data, is_header) in enumerate(all_rows):
        use_white_text = is_header and settings.get('primaryAccentColor') and is_color_dark(settings.get('primaryAccentColor'))
        
        for col_idx, cell_tokens in enumerate(row_data):
            if cell_counter >= len(cell_start_indices): break
            start_index = cell_start_indices[cell_counter]
            cell_counter += 1
            
            if start_index is None: continue
            
            actual_start_index = start_index + cumulative_offset
            
            # Use converter's inline processor
            # cell_tokens is {'tokens': [...] }
            inline_tokens = cell_tokens.get('tokens', [])
            
            # Determine color
            default_color = '#FFFFFF' if use_white_text else settings.get('defaultTextColor', '#000000')
            
            cell_reqs, cell_len = converter._process_inline_tokens(inline_tokens, actual_start_index, default_color)
            requests.extend(cell_reqs)
            
            # Cell background style
            if is_header and settings.get('primaryAccentColor'):
                 requests.append({
                    'updateTableCellStyle': {
                        'tableRange': {
                            'tableCellLocation': {
                                'tableStartLocation': {'index': table_element['startIndex']},
                                'rowIndex': row_idx,
                                'columnIndex': col_idx
                            },
                            'rowSpan': 1,
                            'columnSpan': 1
                        },
                        'tableCellStyle': {'backgroundColor': {'color': {'rgbColor': hex_to_rgb(settings['primaryAccentColor'])}}},
                        'fields': 'backgroundColor'
                    }
                })
            elif not is_header and settings.get('useAlternatingRowColors') and (row_idx) % 2 != 0:
                 # Note: row_idx includes header. If header is 0, first data row is 1 (odd).
                 # If alternating starts at 1...
                 # User logic: (rowIndex - 1) % 2 !== 0. If header is 0, data row 1 -> (1-1)%2==0 (even). 
                 # Let's stick to simple alternating.
                 requests.append({
                    'updateTableCellStyle': {
                        'tableRange': {
                            'tableCellLocation': {
                                'tableStartLocation': {'index': table_element['startIndex']},
                                'rowIndex': row_idx,
                                'columnIndex': col_idx
                            },
                            'rowSpan': 1,
                            'columnSpan': 1
                        },
                        'tableCellStyle': {'backgroundColor': {'color': {'rgbColor': hex_to_rgb(settings.get('alternatingRowColor', '#f3f3f3'))}}},
                        'fields': 'backgroundColor'
                    }
                })

            cumulative_offset += cell_len
            
    return requests

def main():
    parser = argparse.ArgumentParser(description='Create Google Doc from Markdown')
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    create_parser = subparsers.add_parser('create')
    create_parser.add_argument('--title', required=True, help='Document title')
    create_parser.add_argument('--content-file', required=True, help='Path to markdown content')
    create_parser.add_argument('--settings-file', help='Path to settings JSON')

    append_parser = subparsers.add_parser('append')
    append_parser.add_argument('--document-id', required=True, help='Google Doc ID')
    append_parser.add_argument('--content', required=True, help='Content to append')

    insert_parser = subparsers.add_parser('insert')
    insert_parser.add_argument('--document-id', required=True, help='Google Doc ID')
    insert_parser.add_argument('--content', required=True, help='Content to insert')
    insert_parser.add_argument('--index', required=True, help='Index to insert at')

    delete_parser = subparsers.add_parser('delete')
    delete_parser.add_argument('--document-id', required=True, help='Google Doc ID')
    delete_parser.add_argument('--start-index', required=True, help='Start index of range to delete')
    delete_parser.add_argument('--end-index', required=True, help='End index of range to delete')

    replace_parser = subparsers.add_parser('replace')
    replace_parser.add_argument('--document-id', required=True, help='Google Doc ID')
    replace_parser.add_argument('--find', required=True, help='Text to find')
    replace_parser.add_argument('--replace-with', help='Text to replace with (default: empty string to delete)')
    
    args = parser.parse_args()
    
    if args.command == 'create':
        creds = get_credentials()
        if not creds:
            print("Authentication failed.")
            sys.exit(1)
            
        service = build('docs', 'v1', credentials=creds)
        
        # Read content
        with open(args.content_file, 'r') as f:
            content = f.read()
            
        settings = {}
        if args.settings_file:
            with open(args.settings_file, 'r') as f:
                settings = json.load(f)
                
        # Create Doc
        print(f"Creating document: {args.title}")
        doc_id = create_doc(args.title, service)
        print(f"Created document ID: {doc_id}")
        
        # Init converter
        converter = MarkdownConverter(settings)
        blueprints = converter.convert(content)
        
        current_index = 1
        current_blueprints = blueprints
        
        while True:
            result = converter.generate_requests(current_blueprints, start_index=current_index)
            
            if result['requests']:
                print(f"Executing batch of {len(result['requests'])} requests...")
                service.documents().batchUpdate(documentId=doc_id, body={'requests': result['requests']}).execute()
            
            if result['type'] == 'complete':
                break
            
            if result['type'] == 'table_break':
                # Insert empty table
                blueprint = result['blueprint']
                rows = len(blueprint.get('rows', [])) + (1 if blueprint.get('header') else 0)
                cols = 0
                if blueprint.get('header'): cols = len(blueprint['header'])
                elif blueprint.get('rows'): cols = len(blueprint['rows'][0])
                
                if rows > 0 and cols > 0:
                    print(f"Inserting table {rows}x{cols} at index {result['current_index']}")
                    service.documents().batchUpdate(documentId=doc_id, body={
                        'requests': [{
                            'insertTable': {
                                'rows': rows, 
                                'columns': cols, 
                                'location': {'index': result['current_index']}
                            }
                        }]
                    }).execute()
                    
                    # Fetch doc to find table
                    doc = get_doc_content(service, doc_id)
                    table_element = find_table_at_index(doc, result['current_index'])
                    
                    if table_element:
                        # Populate table
                        table_requests = process_table_content(service, doc_id, table_element, blueprint, converter, settings)
                        if table_requests:
                            print(f"Populating table with {len(table_requests)} requests...")
                            service.documents().batchUpdate(documentId=doc_id, body={'requests': table_requests}).execute()
                            
                        # Update current_index for next batch
                        # We need the NEW index after table insertion.
                        # Actually, table population shifts indices inside the table, but the stored current_index
                        # for the NEXT element should be after the table.
                        # Let's fetch the doc again to be safe and find the end of the table.
                        doc = get_doc_content(service, doc_id)
                        # We know the table was at result['current_index'] (roughly)
                        # But simpler: the table element has endIndex.
                        # We need to find the table again.
                        # table_element was from OLD doc (before population).
                        # Population changes text content lengths inside details.
                        # So we MUST fetch again.
                        # Or better: `find_table_at_index` should ideally effectively find the *same* table.
                        # Since we process sequentially, it should be the same one or close.
                        # Actually, iterating elements and finding the one at or after the known insertion point is safe.
                        
                        # Optimization: table is likely the last element or we can search from end?
                        # No, just linear search is fine for typical docs.
                        
                        updated_table = find_table_at_index(doc, result['current_index'])
                        if updated_table:
                             current_index = updated_table['endIndex'] 
                             # Note: endIndex is exclusive, so it points to the position *after* the table.
                             # But in Docs API, usually we insert at index.
                             # Wait, if table ends at 100, next insertion is at 100? Yes.
                             current_index = current_index - 1 # Docs indices are funky.
                             # Actually `endIndex` of a table includes the table itself.
                             # If we want to insert text AFTER the table, we use `endIndex`.
                             # BUT `endIndex` is usually "after the last character".
                             # Let's start with `endIndex`.
                             current_index = updated_table['endIndex'] 
                        else:
                             print("Error: Could not find table after population.")
                             break
                    else:
                        print("Error: Could not find inserted table.")
                        break
                
                current_blueprints = result['remaining_blueprints']
                # If no more blueprints, break?
                if not current_blueprints:
                    break
                    
        print("Document creation complete!")
        print(f"URL: https://docs.google.com/document/d/{doc_id}")

    elif args.command == 'append':
        creds = get_credentials()
        if not creds:
            print("Authentication failed.")
            sys.exit(1)
            
        service = build('docs', 'v1', credentials=creds)
        
        # Insert text at the end of the document
        doc = get_doc_content(service, args.document_id)
        content = doc.get('body').get('content')
        if not content:
            print("Error: Could not retrieve document content.")
            sys.exit(1)
            
        # The last element is usually a SectionBreak with a newline.
        # We want to insert before the very last character (which is the document terminator).
        end_index = content[-1].get('endIndex') - 1
        
        text_to_insert = args.content
        if not text_to_insert.startswith('\n'):
            text_to_insert = '\n' + text_to_insert

        requests = [{
            'insertText': {
                'location': {'index': end_index},
                'text': text_to_insert
            }
        }]
        
        service.documents().batchUpdate(documentId=args.document_id, body={'requests': requests}).execute()
        print(f"Appended text to document {args.document_id}")

    elif args.command == 'insert':
        creds = get_credentials()
        if not creds:
            print("Authentication failed.")
            sys.exit(1)
            
        service = build('docs', 'v1', credentials=creds)
        
        requests = [{
            'insertText': {
                'location': {'index': int(args.index)},
                'text': args.content
            }
        }]
        
        service.documents().batchUpdate(documentId=args.document_id, body={'requests': requests}).execute()
        print(f"Inserted text at index {args.index}")

    elif args.command == 'delete':
        creds = get_credentials()
        if not creds:
            print("Authentication failed.")
            sys.exit(1)
            
        service = build('docs', 'v1', credentials=creds)
        
        requests = [{
            'deleteContentRange': {
                'range': {
                    'startIndex': int(args.start_index),
                    'endIndex': int(args.end_index)
                }
            }
        }]
        
        service.documents().batchUpdate(documentId=args.document_id, body={'requests': requests}).execute()
        print(f"Deleted content from {args.start_index} to {args.end_index}")

    elif args.command == 'replace':
        creds = get_credentials()
        if not creds:
            print("Authentication failed.")
            sys.exit(1)
            
        service = build('docs', 'v1', credentials=creds)
        
        requests = [{
            'replaceAllText': {
                'containsText': {
                    'text': args.find,
                    'matchCase': True
                },
                'replaceText': args.replace_with or ''
            }
        }]
        
        service.documents().batchUpdate(documentId=args.document_id, body={'requests': requests}).execute()
        if args.replace_with:
            print(f"Replaced '{args.find}' with '{args.replace_with}'")
        else:
            print(f"Deleted occurrences of '{args.find}'")

if __name__ == '__main__':
    main()
