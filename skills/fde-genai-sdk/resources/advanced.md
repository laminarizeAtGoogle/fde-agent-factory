# Advanced Capabilities

## Thinking (Reasoning)

The Gemini 3 series of models support explicit "thinking" for complex logic.

Thinking is on by default for `gemini-3.1-pro-preview` and `gemini-3-flash-preview`.
It can be adjusted by using the `thinking_level` parameter.

- **`MINIMAL`:** (Gemini 3 Flash Only) Constrains the model to use as few tokens as possible for thinking and is best used for low-complexity tasks that wouldn't benefit from extensive reasoning.
- **`LOW`**: Constrains the model to use fewer tokens for thinking and is suitable for simpler tasks where extensive reasoning is not required.
- **`MEDIUM`**: (Gemini 3 Flash only) Offers a balanced approach suitable for tasks of moderate complexity that benefit from reasoning but don't require deep, multi-step planning.
- **`HIGH`**: (Default) Maximizes reasoning depth. The model may take significantly longer to reach a first token, but the output will be more thoroughly vetted.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3.1-pro-preview',
    contents='What is AI?',
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.HIGH
        )
    )
)

# Access thoughts if returned
for part in response.candidates[0].content.parts:
    if hasattr(part, 'thought'):
        print(f"Thought: {part.text}")
    else:
        print(f"Response: {part.text}")
```

## System Instructions

Use system instructions to guide model's behavior.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Explain quantum physics.',
    config=types.GenerateContentConfig(
        system_instruction='You are a pirate',
    )
)
print(response.text)
```

## Hyperparameters

You can also set `temperature` or `max_output_tokens` within `types.GenerateContentConfig`.
While `topP` and `topK` should generally be avoided unless you have a specific use case, setting `max_output_tokens` can be a useful tool for controlling costs and preventing overly verbose responses. However, be mindful that setting it too low can result in truncated or incomplete answers. See the Cost Optimization guide for more details.

## Safety configurations

Avoid setting safety configurations unless explicitly requested by the user. If explicitly asked for by the user:

```python
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()

img = Image.open('/path/to/img')
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=['Do these look store-bought or homemade?', img],
    config=types.GenerateContentConfig(
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ]
    )
)

print(response.text)
```

## Streaming

Use `generate_content_stream` to reduce time-to-first-token.

```python
from google import genai

client = genai.Client()

response = client.models.generate_content_stream(
    model='gemini-3-flash-preview',
    contents='Write a long story about a space pirate.'
)

for chunk in response:
    print(chunk.text, end='')
```

## Function Calling

You can provide the model with tools (functions) it can use to bring in external information to answer a question or act on a request outside the model.

### Basic Function Calling Detection

```python
from google import genai
from google.genai import types

# Define a function that the model can call (to access external information)
def get_current_weather(city: str) -> str:
    """Returns the current weather in a given city. For this example, it's hardcoded."""
    if 'boston' in city.lower():
        return 'The weather in Boston is 15°C and sunny.'
    else:
        return f'Weather data for {city} is not available.'

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='What is the weather in Boston?',
    config=types.GenerateContentConfig(
        tools=[get_current_weather] # Make the function available to the model as a tool
    ),
)

# The model may respond with a request to call the function
if response.function_calls:
    print('Function calls requested by the model:')
    for function_call in response.function_calls:
        print(f'- Function: {function_call.name}')
        print(f'- Args: {dict(function_call.args)}')
else:
    print('The model responded directly:')
    print(response.text)
```

### Complete Function Calling Loop

For production use, implement the full loop that executes functions and returns results to the model:

```python
from google import genai
from google.genai import types

def get_current_weather(city: str) -> str:
    """Returns the current weather in a given city."""
    if 'boston' in city.lower():
        return 'The weather in Boston is 15°C and sunny.'
    return f'Weather data for {city} is not available.'

def get_forecast(city: str, days: int = 3) -> str:
    """Returns weather forecast for upcoming days."""
    return f'{days}-day forecast for {city}: Mostly sunny with temperatures 12-18°C.'

client = genai.Client()

# Initial request
messages = [types.Content(role='user', parts=[types.Part.from_text('What is the weather in Boston and the 5-day forecast?')])]

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=messages,
    config=types.GenerateContentConfig(tools=[get_current_weather, get_forecast]),
)

# Execute function calls and send results back
while response.function_calls:
    # Add model's function call request to history
    messages.append(response.candidates[0].content)

    # Execute each function and collect results
    for fc in response.function_calls:
        if fc.name == 'get_current_weather':
            result = get_current_weather(**dict(fc.args))
        elif fc.name == 'get_forecast':
            result = get_forecast(**dict(fc.args))
        else:
            result = f"Unknown function: {fc.name}"

        # Add function response to history
        messages.append(types.Content(
            parts=[types.Part.from_function_response(
                name=fc.name,
                response={'result': result}
            )]
        ))

    # Get next response with function results
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=messages,
        config=types.GenerateContentConfig(tools=[get_current_weather, get_forecast]),
    )

# Final answer after all function calls completed
print(response.text)
```

## Grounding (Google Search)

Connect the model to real-time web data.

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='What was the score of the latest Olympique Lyonais game?',
    config=types.GenerateContentConfig(
        tools=[
            types.Tool(google_search=types.GoogleSearch())
        ]
    ),
)

print(response.text)
# Search details
print(f'Search Query: {response.candidates[0].grounding_metadata.web_search_queries}')
# Inspect grounding metadata
print(response.candidates[0].grounding_metadata.search_entry_point.rendered_content)
# Urls used for grounding
print(f"Search Pages: {', '.join([site.web.title for site in response.candidates[0].grounding_metadata.grounding_chunks])}")
```

The output `response.text` will likely not be in JSON format, do not attempt to parse it as JSON.

## Error Handling

### Common Errors

Handle common API errors gracefully:

```python
from google import genai
from google.genai import errors

client = genai.Client()

try:
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents='Explain artificial intelligence',
    )
    print(response.text)
except errors.ResourceExhausted as e:
    print(f"Rate limit exceeded: {e}")
    # Implement exponential backoff and retry
except errors.InvalidArgument as e:
    print(f"Invalid request parameters: {e}")
    # Check your model name, config, or input format
except errors.PermissionDenied as e:
    print(f"Authentication failed: {e}")
    # Verify your API key or Vertex AI permissions
except errors.NotFound as e:
    print(f"Resource not found: {e}")
    # Check if model name exists or file is available
except errors.DeadlineExceeded as e:
    print(f"Request timeout: {e}")
    # Consider using streaming or shorter prompts
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Safety Blocking

Check if content was blocked by safety filters:

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Your prompt here',
)

# Check finish reason
if response.candidates[0].finish_reason == types.FinishReason.SAFETY:
    print("Content was blocked by safety filters")
    print(f"Safety ratings: {response.candidates[0].safety_ratings}")
elif response.candidates[0].finish_reason == types.FinishReason.RECITATION:
    print("Content was blocked due to recitation concerns")
elif response.candidates[0].finish_reason == types.FinishReason.MAX_TOKENS:
    print("Response was truncated due to max_output_tokens limit")
elif response.candidates[0].finish_reason == types.FinishReason.STOP:
    print("Response completed normally")
```

### Retry with Exponential Backoff

Implement retry logic for rate limit errors:

```python
import time
from google import genai
from google.genai import errors

def generate_with_retry(client, model, contents, max_retries=3):
    """Generate content with exponential backoff retry."""
    wait_time = 1
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
            )
        except errors.ResourceExhausted:
            if attempt == max_retries - 1:
                raise
            print(f"Rate limited. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            wait_time *= 2  # Exponential backoff
        except errors.DeadlineExceeded:
            if attempt == max_retries - 1:
                raise
            print(f"Request timeout. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            wait_time *= 2

client = genai.Client()
response = generate_with_retry(client, 'gemini-3-flash-preview', 'Your prompt')
print(response.text)
```

## Context Caching

For repeated queries with the same large context (documents, code, images), use context caching to reduce costs and latency:

```python
from google import genai
from google.genai import types

client = genai.Client()

# Load large document
with open('large_document.txt', 'r') as f:
    document_content = f.read()

# Create cached content (valid for up to 1 hour)
cache = client.caches.create(
    model='gemini-3-flash-preview',
    contents=[document_content],
    ttl='3600s',  # Cache for 1 hour (can be up to 24 hours)
    display_name='Large Document Cache',
)

print(f"Cache created: {cache.name}")

# Use cached context for multiple queries
queries = [
    'Summarize the key points',
    'What are the main arguments?',
    'List the conclusions',
]

for query in queries:
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=query,
        config=types.GenerateContentConfig(
            cached_content=cache.name,
        )
    )
    print(f"\nQuery: {query}")
    print(f"Response: {response.text}")

# List all caches
for cache_info in client.caches.list():
    print(f"Cache: {cache_info.display_name} - Expires: {cache_info.expire_time}")

# Delete cache when done (or let it expire)
client.caches.delete(name=cache.name)
```

**Cache Best Practices:**
- Minimum content size: 32,768 tokens (~50 pages of text)
- Maximum TTL: 24 hours
- Use for documents, codebases, or large image sets you query repeatedly
- Caching saves both cost and latency on subsequent requests

## Token Counting

Estimate costs and validate input sizes before making API calls:

```python
from google import genai

client = genai.Client()

# Count tokens in a prompt
prompt = "Explain quantum computing in detail with examples and applications."

token_count = client.models.count_tokens(
    model='gemini-3-flash-preview',
    contents=prompt,
)

print(f"Input tokens: {token_count.total_tokens}")
print(f"Estimated input cost: ${token_count.total_tokens * 0.00001:.6f}")  # Example rate

# Count tokens with multimodal input
from google.genai import types
from PIL import Image

image = Image.open('diagram.png')

token_count = client.models.count_tokens(
    model='gemini-3-flash-preview',
    contents=[prompt, image],
)

print(f"Total tokens (text + image): {token_count.total_tokens}")

# Validate before sending to avoid hitting limits
max_input_tokens = 1_000_000  # Model limit for gemini-3-flash-preview
if token_count.total_tokens > max_input_tokens:
    print(f"Warning: Input exceeds model limit of {max_input_tokens} tokens")
else:
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=[prompt, image],
    )
```
