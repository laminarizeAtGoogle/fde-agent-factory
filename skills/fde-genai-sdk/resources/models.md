# Models

## Available Models

By default, use the following models when using `google-genai`:

-   **General Text & Multimodal Tasks:** `gemini-3-flash-preview`
-   **Coding and Complex Reasoning Tasks:** `gemini-3.1-pro-preview`
-   **Low Latency & High Volume Tasks:** `gemini-3.1-flash-lite-preview`
-   **Fast Image Generation and Editing:** `gemini-3.1-flash-image-preview` (aka Nano Banana 2)
-   **High-Quality Image Generation and Editing:** `gemini-3-pro-image-preview` (aka Nano Banana Pro)
-   **High-Fidelity Video Generation:** `veo-3.1-generate-001`
-   **Fast Video Generation:** `veo-3.1-fast-generate-001`
-   **Advanced Video Editing Tasks:** `veo-3.1-generate-001`
-   **Text Embedding:** `text-embedding-005`

It is also acceptable to use following models if explicitly requested by the user:

-   **Gemini 2.0 Series**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`
-   **Gemini 2.5 Series**: `gemini-2.5-flash`, `gemini-2.5-pro`

**Do not use** the following deprecated models (or their variants like `gemini-1.5-flash-latest`):

-   **Prohibited:** `gemini-1.5-flash`
-   **Prohibited:** `gemini-1.5-pro`
-   **Prohibited:** `gemini-pro`

## Model Selection Strategy

Default to the latest stable model families for consistent behavior:

-   **Reasoning & Planning (Pro)**: Use for architectural decisions, complex debugging, and multi-step strategy (e.g., `gemini-3.1-pro-preview`).
-   **Speed & Volume (Flash)**: Use for routing, triage, summarization, and high-volume processing (e.g., `gemini-3-flash-preview`).
-   **Low Latency (Lite)**: Use for fast, low-cost transformations and simple utility tasks (e.g., `gemini-3.1-flash-lite-preview`).
-   **Media Generation**: Use `veo` for video and `imagen` equivalents (like `gemini-3-pro-image-preview` or `gemini-3.1-flash-image-preview`) for high-quality visuals.
-   **Embeddings**: Use `text-embedding-005` for generating text embeddings.
