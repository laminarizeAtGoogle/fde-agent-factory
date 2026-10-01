# Cost Optimization

This guide covers best practices for reducing costs and improving performance when using the Google GenAI SDK.

## Model Selection

Choose the right model for your use case to balance cost and capability:

### Cost Tiers (from least to most expensive)

1. **`gemini-3.1-flash-lite-preview`** - Lowest cost, fastest response
   - Simple transformations, classification, routing
   - High-volume tasks where cost matters most
   - Tasks requiring minimal reasoning

2. **`gemini-3-flash-preview`** - Balanced cost/performance
   - General text generation and chat
   - Multimodal understanding
   - Moderate complexity reasoning
   - **Default recommendation for most tasks**

3. **`gemini-3.1-pro-preview`** - Premium tier
   - Complex reasoning and planning
   - Advanced coding tasks
   - Multi-step problem solving
   - Use only when Flash models are insufficient

### Model Selection Examples

```python
from google import genai

client = genai.Client()

# ❌ Wasteful: Using Pro for simple classification
response = client.models.generate_content(
    model='gemini-3-pro-preview',
    contents='Is this sentiment positive or negative? "I love this product!"',
)

# ✅ Cost-effective: Using Lite for simple tasks
response = client.models.generate_content(
    model='gemini-3.1-flash-lite-preview',
    contents='Is this sentiment positive or negative? "I love this product!"',
)

# ✅ Right tool: Using Pro for complex reasoning
response = client.models.generate_content(
    model='gemini-3-pro-preview',
    contents='Design a distributed system architecture for a real-time trading platform with these requirements...',
)
```

## Reduce Token Usage

### 1. Set Appropriate Output Limits

```python
from google import genai
from google.genai import types

client = genai.Client()

# ❌ No limit - model may generate unnecessarily long responses
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Summarize this article',
)

# ✅ Set reasonable limits
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Summarize this article in 3 bullet points',
    config=types.GenerateContentConfig(
        max_output_tokens=200,  # Prevent excessive output
    ),
)
```

### 2. Use Structured Outputs

Structured outputs are more token-efficient than verbose natural language:

```python
from pydantic import BaseModel
from google import genai
from google.genai import types

class Summary(BaseModel):
    key_points: list[str]
    sentiment: str
    category: str

client = genai.Client()

# ✅ Structured output - concise and predictable
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Analyze this product review: ...',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=Summary,
    ),
)
```

### 3. Optimize Prompts

```python
# ❌ Verbose, repetitive prompt
prompt = """
I would like you to please analyze the following text and tell me what the main
themes are. I'm really interested in understanding what the key topics are and
what the author is trying to communicate. Please be thorough but also concise.
"""

# ✅ Clear, concise prompt
prompt = "Identify the main themes in this text:"
```

## Context Caching

For large, repeated contexts, use caching to save costs:

```python
from google import genai
from google.genai import types

client = genai.Client()

# Load large codebase
with open('large_codebase.py', 'r') as f:
    code = f.read()

# Create cache (costs: full price once, then heavily discounted)
cache = client.caches.create(
    model='gemini-3-flash-preview',
    contents=[code],
    ttl='3600s',
)

# Multiple queries reuse cached context
queries = [
    'Find all function definitions',
    'What security vulnerabilities exist?',
    'Suggest performance improvements',
]

for query in queries:
    # Only charged for new tokens in query + output
    response = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=query,
        config=types.GenerateContentConfig(
            cached_content=cache.name
        )
    )
    print(response.text)
```

**When to use caching:**
- Same large document/codebase queried multiple times
- Minimum 32,768 tokens (cached portion)
- Break-even: ~3-4 requests with same context
- Maximum cache TTL: 24 hours

## Batch Processing

Process multiple independent requests in parallel to improve throughput:

```python
import asyncio
from google import genai

async def generate_batch(prompts: list[str], model: str = 'gemini-3-flash-preview'):
    """Process multiple prompts in parallel."""
    # Note: In a real application, you would create the client once.
    client = genai.Client()

    tasks = [
        client.aio.models.generate_content(
            model=model,
            contents=prompt
        )
        for prompt in prompts
    ]
    responses = await asyncio.gather(*tasks)
    return responses

# Process 100 prompts in parallel
prompts = [f"Summarize article {i}" for i in range(100)]
results = asyncio.run(generate_batch(prompts, model='gemini-3.1-flash-lite-preview'))
# You can then process the results:
# for result in results:
#     print(result.text)
```

## Streaming for Better UX

Streaming doesn't reduce costs, but improves perceived performance:

```python
from google import genai

client = genai.Client()

# Non-streaming: user waits for entire response
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Write a long story about space exploration',
)
print(response.text)  # All at once after waiting

# Streaming: user sees output immediately
response = client.models.generate_content_stream(
    model='gemini-3-flash-preview',
    contents='Write a long story about space exploration',
)
for chunk in response:
    print(chunk.text, end='', flush=True)  # Progressive output
```

## Disable Thinking When Not Needed

Gemini 3 models use thinking tokens by default. For simple tasks, you can reduce thinking to save costs.

```python
from google import genai
from google.genai import types

client = genai.Client()

# Default thinking for a flash model
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='What is 2+2?',
)

# Use MINIMAL thinking level for simple queries
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='What is 2+2?',
    config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(
            thinking_level=types.ThinkingLevel.MINIMAL
        )
    ),
)
```

## Monitor and Measure

Track token usage to identify optimization opportunities:

```python
from google import genai

client = genai.Client()

prompt = "Your prompt here"

# Count before generating
token_count = client.models.count_tokens(
    model='gemini-3-flash-preview',
    contents=prompt,
)

print(f"Input tokens: {token_count.total_tokens}")

# Generate
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=prompt,
)

# Track output tokens
output_tokens = client.models.count_tokens(
    model='gemini-3-flash-preview',
    contents=response.text,
)

print(f"Output tokens: {output_tokens.total_tokens}")
print(f"Total tokens: {token_count.total_tokens + output_tokens.total_tokens}")
```

## Cost Optimization Checklist

- [ ] Use the cheapest model that meets your needs (Lite → Flash → Pro)
- [ ] Set `max_output_tokens` to prevent excessive generation
- [ ] Use structured outputs instead of verbose natural language
- [ ] Cache large contexts that are reused across multiple requests
- [ ] Batch independent requests to improve throughput
- [ ] Disable thinking for simple tasks (Gemini 2.5/3 only)
- [ ] Use streaming to improve perceived performance
- [ ] Monitor token usage with `count_tokens()`
- [ ] Optimize prompts to be clear and concise
- [ ] Avoid unnecessary multimodal inputs (e.g., don't send images for text-only tasks)

## Cost Comparison Example

Processing 1,000 customer reviews:

```python
# ❌ Expensive approach: ~$5.00
# - Using gemini-3-pro-preview
# - No output limits
# - Verbose prompts
# - No caching

# ✅ Optimized approach: ~$0.15
# - Using gemini-3.1-flash-lite-preview
# - Structured outputs with max_output_tokens=100
# - Concise prompts
# - Batch processing

# That's a 97% cost reduction!
```

## Additional Resources

- [Gemini API Pricing](https://ai.google.dev/pricing)
- [Rate Limits](https://ai.google.dev/rate-limits)
- [Token Counting](https://ai.google.dev/gemini-api/docs/tokens)
