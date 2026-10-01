---
name: fde-google-docs
description: Expert in creating and updating Google Docs from Markdown. Use this skill to generate professional documents with formatting, tables, and styles directly from text content.
---

# Google Docs Skill

This skill provides capabilities to interact with Google Docs, specifically focusing on converting Markdown content into formatted Google Docs.

## Prerequisites
- **Google Cloud Platform Project**: You must have an active GCP project.
- **APIs Enabled**: Enable **Google Docs API** and **Google Drive API**.
- **OAuth Consent Screen**:
  - Configure as **External** (for testing with personal Gmail) or **Internal** (workspace).
  - Add your email as a **Test User** if using External mode.
- **Scopes**: Ensure the following scopes are added:
  - `https://www.googleapis.com/auth/documents`
  - `https://www.googleapis.com/auth/drive.file`

## Setup & Authentication
1.  **Download Credentials**:
    -   Go to **APIs & Services > Credentials** in GCP Console.
    -   Create **OAuth 2.0 Client ID** (Desktop App).
    -   Download the JSON file and rename it to `credentials.json`.
    -   Place `credentials.json` in the root of your project (where you run the script from).

2.  **Dependencies**:
    ```bash
    uv pip install -r .agents/skill-library/fde-google-docs/requirements.txt
    ```

3.  **Authentication Flow**:
    -   The first time you run a command, a browser window will open for you to authorize the app.
    -   A `token.json` file will be created to store your session (so you don't need to log in every time).

## Capabilities

## capabilities
- **Markdown to Docs**: Converts Markdown (including headers, lists, tables, links, bold/italic) into a Google Doc.
- **Styling**: Supports custom colors for text, links, and table headers/alternating rows.

## Usage

### 1. Create a Doc from Markdown
```bash
python .agents/skill-library/fde-google-docs/scripts/docs_cli.py create \
  --title "My Document Title" \
  --content-file "path/to/content.md" \
  --settings-file "path/to/settings.json" # Optional
```

### 2. Append Text
```bash
python .agents/skill-library/fde-google-docs/scripts/docs_cli.py append \
  --document-id <DOC_ID> \
  --content "Text to append"
```

### 3. Insert Text
```bash
python .agents/skill-library/fde-google-docs/scripts/docs_cli.py insert \
  --document-id <DOC_ID> \
  --content "Text to insert" \
  --index <INDEX>
```

### 4. Delete Text
```bash
python .agents/skill-library/fde-google-docs/scripts/docs_cli.py delete \
  --document-id <DOC_ID> \
  --start-index <START> \
  --end-index <END>
```

### 5. Find and Replace
```bash
python .agents/skill-library/fde-google-docs/scripts/docs_cli.py replace \
  --document-id <DOC_ID> \
  --find "Text to find" \
  --replace-with "New text"
```

### Settings JSON Format (Optional)
You can customize the appearance with a JSON file:
```json
{
  "defaultTextColor": "#333333",
  "hyperlinkColor": "#1155cc",
  "primaryAccentColor": "#4285f4",
  "useAlternatingRowColors": true,
  "alternatingRowColor": "#f3f3f3"
}
```
