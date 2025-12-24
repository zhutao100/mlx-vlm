# Inference Entry Points Analysis

## `mlx_vlm/generate.py`
The core inference engine.
- **`generate_step()`**:
    - Low-level generator function yielding tokens one by one.
    - Manages KV Cache creation (`cache.make_prompt_cache`).
    - Implements sampling (Temperature, Top-P) and repetition penalty.
    - Handles periodic cache cleanup.
- **`stream_generate()`**:
    - Wraps `generate_step` with `processor.detokenizer` to yield text chunks.
    - Handles input preparation via `prepare_inputs`.
- **`batch_generate()`**:
    - Efficient batch processing.
    - **Optimization**: Groups images by shape (`group_images_by_shape`) to minimize padding and computational waste.
    - Uses `BatchGenerator` class to manage batch state.
- **CLI**:
    - Provides a command-line interface for single-prompt or multi-turn chat generation.

## `mlx_vlm/chat.py`
Interactive CLI Chat tool.
- **`MLXVisionChat` class**:
    - Manages conversation state (`history`).
    - Supports slash commands (`/image`, `/clear`, `/help`, `/exit`).
    - Uses `rich` library for formatted console output.
    - Calls `generate_step` directly for fine-grained control over streaming output.

## `mlx_vlm/server.py`
FastAPI-based server for serving VLMs.
- **OpenAI Compatibility**:
    - Implements `/v1/chat/completions` style endpoint (`/chat/completions`).
    - Implements `/responses` for text/image inputs.
    - Supports streaming responses (SSE).
- **State Management**:
    - `get_cached_model`: Caches the loaded model to avoid reloading on every request (Single-model serving pattern).
    - `/unload`: Frees GPU memory.
- **Multimodal Support**:
    - Handles text, image, and audio inputs in the API request payload.
