
import re

def hex_to_rgb(hex_color):
    """
    Converts a hex color string to an RGB dictionary with values 0-1.
    """
    if not hex_color:
        return None
    
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join([c*2 for c in hex_color])
    
    if len(hex_color) != 6:
        return None
        
    try:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return {'red': r, 'green': g, 'blue': b}
    except ValueError:
        return None

def is_color_dark(hex_color):
    """
    Determines if a color is dark by calculating its luminance.
    Matches the logic: ((r*299) + (g*587) + (b*114)) / 1000 < 128
    """
    rgb = hex_to_rgb(hex_color)
    if not rgb:
        return False
    
    # rgb values are 0-1, so we multiply by 255 for the formula
    yiq = ((rgb['red'] * 255 * 299) + (rgb['green'] * 255 * 587) + (rgb['blue'] * 255 * 114)) / 1000
    return yiq < 128

def get_credentials():
    """
    Gets valid user credentials from local file.
    """
    import os
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    SCOPES = ['https://www.googleapis.com/auth/documents', 'https://www.googleapis.com/auth/drive.file']
    creds = None
    
    # standard location for token
    token_path = 'token.json'
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            # First try credentials.json (Explicit OAuth Flow)
            if os.path.exists('credentials.json'):
                print("Found credentials.json, initiating OAuth flow...")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            
            # Fallback to Application Default Credentials (ADC)
            else:
                print("credentials.json not found. Attempting Application Default Credentials (ADC)...")
                try:
                    creds, project_id = google.auth.default(scopes=SCOPES)
                    print(f"Using ADC with project: {project_id}")
                except DefaultCredentialsError:
                    print("Error: No valid credentials found.")
                    print("Please either:")
                    print("1. Place 'credentials.json' in this directory (for personal/installed app flow).")
                    print(f"2. Run 'gcloud auth application-default login --scopes {','.join(SCOPES)}'")
                    return None
            
    return creds
