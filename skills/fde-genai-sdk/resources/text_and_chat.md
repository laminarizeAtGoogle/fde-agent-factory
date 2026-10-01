# Text and Chat

## Basic Inference (Text Generation)

Here's how to generate a response from a text prompt. Calls are stateless using the `client.models` accessor.

```python
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Why is the sky blue?',
)

print(response.text)  # output is often markdown
```

## Chat

For multi-turn conversations, use the `chats` service to maintain conversation history.

```python
from google import genai

client = genai.Client()
chat = client.chats.create(model='gemini-3-flash-preview')

response1 = chat.send_message('I have a cat named Whiskers.')
print(response1.text)

response2 = chat.send_message('What is the name of my pet?')
print(response2.text)

# To access specific elements in chat history
for message in chat.get_history():
    print(f'role - {message.role}', end=': ')
    print(message.parts[0].text)
```

## Structured Outputs (Pydantic)

Enforce a specific JSON schema using standard Python type hints or Pydantic models.

```python
from google import genai
from google.genai import types
from pydantic import BaseModel

class Recipe(BaseModel):
    name: str
    description: str
    ingredients: list[str]
    steps: list[str]

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Provide a classic recipe for chocolate chip cookies.',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=Recipe,
    ),
)

# response.text is guaranteed to be valid JSON matching the schema
print(response.text)

# Access the response as a Pydantic object
parsed_response = response.parsed
```

### Advanced Pydantic Example with Enums and Nested Models

For more complex schemas with enums, nested models, and field descriptions:

```python
from enum import Enum
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class Ingredient(BaseModel):
    name: str
    amount: str
    optional: bool = False

class Recipe(BaseModel):
    name: str
    description: str = Field(description="Brief description of the dish")
    difficulty: Difficulty
    ingredients: list[Ingredient]
    steps: list[str]
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='Provide a detailed recipe for chocolate chip cookies.',
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=Recipe,
    ),
)

# Type-safe access to structured data
recipe = response.parsed
print(f"Recipe: {recipe.name}")
print(f"Difficulty: {recipe.difficulty.value}")
print(f"Total time: {(recipe.prep_time_minutes or 0) + (recipe.cook_time_minutes or 0)} minutes")
for ingredient in recipe.ingredients:
    optional_tag = " (optional)" if ingredient.optional else ""
    print(f"- {ingredient.amount} {ingredient.name}{optional_tag}")
```

## Content and Part Hierarchy

While the simpler API call is often sufficient, you may run into scenarios where you need to work directly with the underlying `Content` and `Part` objects for more explicit control. These are the fundamental building blocks of the `generate_content` API.

For instance, the following simple API call:

```python
from google import genai

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents='How does AI work?'
)
print(response.text)
```

is effectively a shorthand for this more explicit structure:

```python
from google import genai
from google.genai import types

client = genai.Client()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[
        types.Content(role='user', parts=[types.Part.from_text(text='How does AI work?')]),
    ]
)
print(response.text)
```
