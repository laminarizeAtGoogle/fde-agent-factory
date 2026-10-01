
import markdown_it
try:
    from .utils import hex_to_rgb, is_color_dark
except ImportError:
    from utils import hex_to_rgb, is_color_dark

class MarkdownConverter:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.default_text_color = self.settings.get('defaultTextColor', '#000000')
        self.hyperlink_color = self.settings.get('hyperlinkColor', '#1155cc')
        self.primary_accent_color = self.settings.get('primaryAccentColor', None)
        self.use_alternating_rows = self.settings.get('useAlternatingRowColors', False)
        self.alternating_row_color = self.settings.get('alternatingRowColor', '#f3f3f3')
        
        # Initialize markdown-it
        self.md = markdown_it.MarkdownIt()
        
    def convert(self, markdown_text):
        """
        Parses markdown and returns blueprints (intermediate representation).
        """
        tokens = self.md.parse(markdown_text)
        blueprints = self._tokens_to_blueprints(tokens)
        return blueprints

    def _tokens_to_blueprints(self, tokens):
        """
        Groups tokens into 'blueprints' similar to the JS implementation reference.
        """
        blueprints = []
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == 'heading_open':
                # Grab content from next inline token
                inline_token = tokens[i + 1]
                blueprints.append({
                    'type': 'heading',
                    'depth': int(token.tag[1:]),
                    'text': inline_token.content
                })
                i += 3 # skip heading_open, inline, heading_close
                
            elif token.type == 'paragraph_open':
                inline_token = tokens[i + 1]
                
                # Check if it's just an image
                if inline_token.children and len(inline_token.children) == 1 and inline_token.children[0].type == 'image':
                    img_token = inline_token.children[0]
                    blueprints.append({
                        'type': 'image',
                        'src': img_token.attrs.get('src'),
                        'alt': img_token.content
                    })
                else:
                    blueprints.append({
                        'type': 'paragraph',
                        'tokens': inline_token.children
                    })
                i += 3
                
            elif token.type == 'bullet_list_open' or token.type == 'ordered_list_open':
                is_ordered = (token.type == 'ordered_list_open')
                items = []
                list_tokens = []
                nesting = 1
                j = i + 1
                while j < len(tokens) and nesting > 0:
                    t = tokens[j]
                    if t.type == token.type: nesting += 1
                    elif t.type == token.type.replace('open', 'close'): nesting -= 1
                    if nesting > 0: list_tokens.append(t)
                    j += 1
                
                current_item = []
                for lt in list_tokens:
                    if lt.type == 'list_item_open':
                        current_item = []
                    elif lt.type == 'list_item_close':
                        item_text_tokens = []
                        for kit in current_item:
                            if kit.type == 'inline':
                                item_text_tokens.extend(kit.children)
                        items.append(item_text_tokens)
                    else:
                        current_item.append(lt)
                        
                blueprints.append({
                    'type': 'list',
                    'ordered': is_ordered,
                    'items': items
                })
                i = j
                
            elif token.type == 'table_open':
                header = []
                rows = []
                
                j = i + 1
                table_tokens = []
                nesting = 1
                while j < len(tokens) and nesting > 0:
                    if tokens[j].type == 'table_open': nesting += 1
                    elif tokens[j].type == 'table_close': nesting -= 1
                    if nesting > 0: table_tokens.append(tokens[j])
                    j += 1
                    
                in_thead = False
                current_row = []
                
                k = 0
                while k < len(table_tokens):
                    tt = table_tokens[k]
                    if tt.type == 'thead_open': in_thead = True
                    elif tt.type == 'thead_close': in_thead = False
                    elif tt.type == 'tr_open': current_row = []
                    elif tt.type == 'tr_close':
                        if in_thead: header = current_row
                        else: rows.append(current_row)
                    elif tt.type in ('th_open', 'td_open'):
                        content_tokens = []
                        if k+1 < len(table_tokens) and table_tokens[k+1].type == 'inline':
                             content_tokens = table_tokens[k+1].children
                             k += 1 
                        current_row.append({'tokens': content_tokens})
                    k += 1

                blueprints.append({
                    'type': 'table',
                    'header': header,
                    'rows': rows
                })
                i = j

            else:
                i += 1
                
        return blueprints

    def generate_requests(self, blueprints, start_index=1):
        """
        Generates Google Docs API requests from blueprints.
        """
        all_requests = []
        current_index = start_index
        
        # Add newline at start if not empty doc (usually good practice)
        if current_index > 1:
             all_requests.append({
                'insertText': {'location': {'index': current_index}, 'text': '\n'}
            })
             current_index += 1

        for idx, blueprint in enumerate(blueprints):
            reqs = []
            
            if blueprint['type'] == 'heading':
                text = blueprint['text']
                # Clean text (remove newlines)
                text = text.replace('\n', ' ')
                reqs.append({'insertText': {'location': {'index': current_index}, 'text': text + '\n'}})
                reqs.append({
                    'updateParagraphStyle': {
                        'range': {'startIndex': current_index, 'endIndex': current_index + len(text)},
                        'paragraphStyle': {'namedStyleType': f"HEADING_{blueprint['depth']}"},
                        'fields': 'namedStyleType'
                    }
                })
                reqs.append({
                    'updateTextStyle': {
                        'range': {'startIndex': current_index, 'endIndex': current_index + len(text)},
                        'textStyle': {
                            'foregroundColor': {'color': {'rgbColor': hex_to_rgb('#000000')}},
                            'underline': False,
                            'link': None
                        },
                        'fields': 'foregroundColor,underline,link'
                    }
                })
                current_index += len(text) + 1
                
            elif blueprint['type'] == 'paragraph':
                paragraph_reqs, p_len = self._process_inline_tokens(blueprint['tokens'], current_index, self.default_text_color)
                reqs.extend(paragraph_reqs)
                reqs.append({'insertText': {'location': {'index': current_index + p_len}, 'text': '\n'}})
                current_index += p_len + 1

            elif blueprint['type'] == 'list':
                for item_tokens in blueprint['items']:
                    ver_reqs, v_len = self._process_inline_tokens(item_tokens, current_index, self.default_text_color)
                    reqs.extend(ver_reqs)
                    reqs.append({'insertText': {'location': {'index': current_index + v_len}, 'text': '\n'}})
                    
                    reqs.append({
                        'createParagraphBullets': {
                            'range': {'startIndex': current_index, 'endIndex': current_index + 1},
                            'bulletPreset': 'NUMBERED_DECIMAL_ALPHA_ROMAN' if blueprint['ordered'] else 'BULLET_DISC_CIRCLE_SQUARE'
                        }
                    })
                    current_index += v_len + 1

            elif blueprint['type'] == 'table':
                # Return state for external handling
                return {
                    'type': 'table_break', 
                    'blueprint': blueprint, 
                    'processed_requests': all_requests, 
                    'current_index': current_index,
                    'remaining_blueprints': blueprints[idx+1:]
                }

            all_requests.extend(reqs)

        return {'type': 'complete', 'requests': all_requests, 'final_index': current_index}

    def _process_inline_tokens(self, tokens, start_index, default_color):
        requests = []
        current_off = 0
        style_stack = [] 
        current_link = None
        
        if not tokens:
            return requests, 0

        for token in tokens:
            if token.type == 'text':
                content = token.content
                if not content: continue
                
                requests.append({
                    'insertText': {'location': {'index': start_index + current_off}, 'text': content}
                })
                
                text_style = {
                    'bold': 'strong' in style_stack,
                    'italic': 'em' in style_stack,
                    'underline': False,
                    'foregroundColor': {'color': {'rgbColor': hex_to_rgb(default_color)}}
                }
                fields = 'bold,italic,underline,foregroundColor'
                
                if current_link:
                    text_style['link'] = {'url': current_link}
                    text_style['foregroundColor'] = {'color': {'rgbColor': hex_to_rgb(self.hyperlink_color)}}
                    text_style['underline'] = True
                    fields += ',link'
                
                requests.append({
                    'updateTextStyle': {
                        'range': {'startIndex': start_index + current_off, 'endIndex': start_index + current_off + len(content)},
                        'textStyle': text_style,
                        'fields': fields
                    }
                })
                
                current_off += len(content)
            
            elif token.type == 'strong_open': style_stack.append('strong')
            elif token.type == 'strong_close': 
                if 'strong' in style_stack: style_stack.remove('strong')
            elif token.type == 'em_open': style_stack.append('em')
            elif token.type == 'em_close': 
                if 'em' in style_stack: style_stack.remove('em')
            elif token.type == 'link_open': 
                current_link = token.attrs.get('href', '')
            elif token.type == 'link_close': 
                current_link = None
                
        return requests, current_off
