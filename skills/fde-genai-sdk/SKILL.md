---
name: fde-genai-sdk
description: Expert in Google GenAI SDK (google-genai package) for Gemini, Veo, and Imagen models. Covers multimodal inputs, structured outputs, function calling, grounding, video/image generation, chat, streaming, and thinking capabilities. Use for all Gemini API and Vertex AI generative model integrations.
---

# GenAI SDK Expert

You are a Gemini API coding expert. Help me with writing code using the Gemini API calling the official libraries and SDKs.

**Official Documentation:** [ai.google.dev/gemini-api/docs](https://ai.google.dev/gemini-api/docs)
**Example Notebook:** https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_genai_sdk.ipynb

## When to Use This Skill

Use this skill when you need to:
- Call Gemini, Veo, or Imagen models via the Google GenAI SDK
- Implement multimodal inputs (text, images, audio, video)
- Generate structured JSON outputs with schema validation
- Implement function calling for tool use
- Generate or edit images using Nano Banana models
- Generate videos using Veo models
- Enable Google Search grounding for real-time data
- Configure thinking/reasoning capabilities
- Work with chat conversations and message history
- Implement streaming responses

Do NOT use this skill for:
- Vertex AI Agent Builder (ADK) development → use `adk-agent-builder` skill (`https://github.com/google/adk-python/tree/main`) instead
- MCP server creation → use `fde-mcp-server-builder` skill instead
- Legacy `google-generativeai` package → this skill covers only `google-genai`

## Golden Rule: Use the Correct and Current SDK

Always use the **Google GenAI SDK** (`google-genai`), which is the unified standard library for all Gemini API requests (AI Studio/Gemini Developer API and Vertex AI) as of 2026. Do not use legacy libraries and SDKs.

-   **Library Name:** Google GenAI SDK
-   **Python Package:** `google-genai`
-   **Legacy Library**: (`google-generativeai`) is deprecated.

**Installation:**

-   **Incorrect:** `pip install google-generativeai`
-   **Incorrect:** `pip install google-ai-generativelanguage`
-   **Correct:** `pip install google-genai`

**Dependencies:**

The examples in this skill may use the following additional packages:
- `pandas`
- `google-cloud-storage`
- `fsspec`

You can install them with pip:
`pip install pandas google-cloud-storage fsspec`

**APIs and Usage:**

-   **Incorrect:** `import google.generativeai as genai` -> **Correct:** `from google import genai`
-   **Incorrect:** `from google.ai import generativelanguage_v1` -> **Correct:** `from google import genai`
-   **Incorrect:** `genai.configure(api_key=...)` -> **Correct:** `client = genai.Client(api_key='...')`
-   **Incorrect:** `model = genai.GenerativeModel(...)`
-   **Incorrect:** `model.generate_content(...)` -> **Correct:** `client.models.generate_content(...)`

## Initialization and API Key

The `google-genai` library requires creating a client object for all API calls.

-   Always use `client = genai.Client()` to create a client object.
-   For Vertex AI: Set `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` environment variables
-   For Gemini API: Set `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) environment variable

```python
import os
from google import genai

# Best practice: Vertex AI with environment variables
client = genai.Client(
    vertexai=True,
    project=os.getenv('GOOGLE_CLOUD_PROJECT'),
    location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
)

# Alternative: Gemini API with API key from environment
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# If environment variables are already set, simplest form:
client = genai.Client(vertexai=True)  # Auto-detects project from env
```

### Environment Configuration (.env)

```bash
# For Vertex AI
GOOGLE_CLOUD_PROJECT="your-project-id"
GOOGLE_CLOUD_LOCATION="us-central1"

# For Gemini API (alternative to Vertex AI)
GEMINI_API_KEY="your-api-key"
```


## Detailed Documentation

-   **Models & Selection**: See [resources/models.md](resources/models.md) for available models and selection strategy.
-   **Text & Chat**: See [resources/text_and_chat.md](resources/text_and_chat.md) for text generation, chat, and structured outputs.
-   **Media & Multimodal**: See [resources/media.md](resources/media.md) for images, video (Veo), and multimodal inputs.
-   **Advanced Capabilities**: See [resources/advanced.md](resources/advanced.md) for thinking, function calling, grounding, safety settings, streaming, error handling, and context caching.
-   **Cost Optimization**: See [resources/optimization.md](resources/optimization.md) for best practices on reducing costs and improving performance.

## Useful Links

-   Documentation: ai.google.dev/gemini-api/docs
-   API Keys and Authentication: ai.google.dev/gemini-api/docs/api-key
-   Models: ai.google.dev/models
-   API Pricing: ai.google.dev/pricing
-   Rate Limits: ai.google.dev/rate-limits