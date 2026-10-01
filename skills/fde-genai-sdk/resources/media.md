# Media and Multimodal

## Multimodal Inputs

Pass images directly as PIL objects, bytes, or file URIs.

### Using PIL Images

```python
from google import genai
from PIL import Image

image = Image.open('image.jpg')

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[image, 'Describe this image in detail.'],
)

print(response.text)
```

### Using Bytes (Best for Web/API Backends)

You can also use `Part.from_bytes` type to pass a variety of data types (images, audio, video, pdf).

```python
from google import genai
from google.genai import types

with open('audio_sample.mp3', 'rb') as f:
    audio_bytes = f.read()

response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[
        types.Part.from_bytes(
            data=audio_bytes,
            mime_type='audio/mp3',
        ),
        'Transcribe this audio.'
    ]
)
print(response.text)
```

### File API (For Large Files)

For video files or long audio, upload to the File API first.

```python
# Upload
my_file = client.files.upload(file='video.mp4')

# Generate
response = client.models.generate_content(
    model='gemini-3-flash-preview',
    contents=[my_file, 'What happens in this video?']
)
print(response.text)

# You can delete files after use like this:
client.files.delete(name=my_file.name)
```

### File Management Best Practices

Manage uploaded files to stay within quota limits:

```python
from datetime import datetime, timedelta

# List all uploaded files
files = client.files.list()
for file in files:
    print(f"{file.name}: {file.display_name} ({file.size_bytes} bytes)")

# Delete old files (older than 24 hours)
cutoff = datetime.now() - timedelta(hours=24)
for file in client.files.list():
    if file.create_time < cutoff:
        print(f"Deleting old file: {file.display_name}")
        client.files.delete(name=file.name)
```

**File Size Limits:**
- Images: Up to 20MB
- Audio: Up to 2 hours
- Video: Up to 2 hours or 2GB
- Documents (PDF): Up to 50MB

## Media Generation

### Generate Images

Here's how to generate images using the Nano Banana models. Start with the Gemini 2.5 Flash Image (Nano Banana) model as it should cover most use-cases.

```python
from google import genai
from google.genai import types
from PIL import Image

prompt =  "Create a picture of a nano banana dish in a fancy restaurant with a Gemini theme"

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3.1-flash-image-preview",
    contents=prompt,
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save("generated_image.png")
```

Upgrade to the Gemini 3 Pro image (Nano Banana Pro) model if the user requests high-resolution images or needs real-time information using the Google Search tool.

```python
from google import genai
from google.genai import types
from PIL import Image

prompt = "Visualize the current weather forecast for the next 5 days in San Francisco as a clean, modern weather chart. Add a visual on what I should wear each day"
aspect_ratio = "16:9" # "1:1","2:3","3:2","3:4","4:3","4:5","5:4","9:16","16:9","21:9"
resolution = "1K" # "1K", "2K", "4K"

client = genai.Client()

response = client.models.generate_content(
    model="gemini-3-pro-image-preview",
    contents=prompt,
    config=types.GenerateContentConfig(
        image_config=types.ImageConfig(
            aspect_ratio=aspect_ratio,
            image_size=resolution
        ),
        # Optional
        tools=[
            types.Tool(google_search=types.GoogleSearch())
        ]
    )
)

for part in response.parts:
    if part.text is not None:
        print(part.text)
    elif image:= part.as_image():
        image.save("weather.png")
```

### Edit images

Editing images is better done using the Gemini native image generation model, and it is recommended to use chat mode. Configs are not supported in this model (except modality).

```python
from google import genai
from PIL import Image
from io import BytesIO

client = genai.Client()

prompt = """
Create a picture of my cat eating a nano-banana in a fancy restaurant under the gemini constellation
"""
image = Image.open('/path/to/image.png')

# Create the chat
chat = client.chats.create(model='gemini-3.1-flash-image-preview')
# Send the image and ask for it to be edited
response = chat.send_message([prompt, image])

# Get the text and the image generated
for i, part in enumerate(response.candidates[0].content.parts):
    if part.text is not None:
        print(part.text)
    elif part.inline_data is not None:
        image = part.as_image()
        image.save(f'generated_image_{i}.png') # Multiple images can be generated

# Continue iterating
chat.send_message('Can you make it a bananas foster?')
```

### Video Generation (Veo)

Use the Veo models for video generation. Usage of Veo can be costly, so after generating code for it, give user a heads up to check pricing for Veo. Start with the fast model since the result quality is usually sufficient, and swap to the larger model if needed.

```python
import time
from google import genai
from google.genai import types
from PIL import Image

client = genai.Client()

image = Image.open('path/to/image.png') # Optional

# Video generation is an async operation
operation = client.models.generate_videos(
    model='veo-3.1-fast-generate-001',
    prompt='Panning wide shot of a calico kitten sleeping in the sunshine',
    image=image,
    config=types.GenerateVideosConfig(
        person_generation='dont_allow',  # 'dont_allow' or 'allow_adult'
        aspect_ratio='16:9',  # '16:9' or '9:16'
        number_of_videos=1, # supported value is 1-4, use 1 by default
        duration_seconds=8, # supported value is 5-8
    ),
)

# Poll for completion with exponential backoff
wait_time = 5
max_wait = 60
while not operation.done:
    time.sleep(wait_time)
    operation = client.operations.get(operation)
    if not operation.done:
        wait_time = min(wait_time * 1.5, max_wait)  # Exponential backoff
        print(f"Video generation in progress... (waiting {wait_time:.0f}s)")

print("Video generation complete!")
for n, generated_video in enumerate(operation.response.generated_videos):
    video_bytes = client.files.download(name=generated_video.video.name)
    with open(f"video{n}.mp4", "wb") as f:
        f.write(video_bytes)
    print(f"Saved video{n}.mp4")
```
