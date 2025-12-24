# Project Architecture: MLX-VLM

## Executive Summary
**MLX-VLM** is a high-performance library for running, training, and fine-tuning Vision Language Models (VLMs) on Apple Silicon. Built on top of the **MLX** framework, it provides optimized implementations of state-of-the-art models like Qwen2-VL, LLaVA, Pixtral, Florence-2, and Molmo. The library aims to make VLM research and application accessible on Mac devices, supporting features like quantization (4-bit/8-bit), LoRA fine-tuning, and multi-modal generation (Text, Image, Video, Audio).

## Technology Stack
- **Core Framework**: Python, MLX (Apple's array framework).
- **Inference**: MLX-LM (for language model backend), Custom Metal Kernels.
- **Data Processing**: Hugging Face Transformers (Tokenizers, Image Processors), PIL, OpenCV (Video).
- **Serving**: FastAPI (OpenAI-compatible server), Uvicorn.
- **UI/Demo**: Gradio.
- **Training**: LoRA/QLoRA via MLX Optimizers.
- **Testing**: Unittest framework with parameterized test runners.

## Architecture Overview
The project generally follows a modular "Vision Tower + Language Model" architecture pattern, but accommodates significant deviations for specialized models.

### Component Map

1.  **Core Library (`mlx_vlm/`)**
    -   **`models/`**: Implementation of specific model architectures.
        -   **Infrastructure**: `base.py`, `cache.py` (KV Cache), `interpolate.py` (Image resizing).
        -   **Standard VLM (LLaVA-like)**: Vision Tower -> Projector -> Text Embeddings -> LLM.
        -   **Advanced VLM (Qwen2-VL, Pixtral)**: Adds temporal embeddings, 2D-RoPE, and complex packing logic.
        -   **Encoder-Decoder (Florence-2)**: DaViT Vision Encoder + BART/T5-style Language Model. Uses 2D learned positional embeddings.
        -   **Embedding Injection (Molmo)**: Adds visual features to text embeddings at specific indices instead of replacing placeholder tokens.
    -   **`utils.py`**: Model loading, weight sanitization, quantization logic.
    -   **`prompt_utils.py`**: Handles diverse chat templates and message formatting (images/videos).
    -   **`generate.py`**: Core inference engine (streaming, batching, sampling).

2.  **Tools & Workflows**
    -   **Conversion (`convert.py`)**: Converts HF models to MLX format, applying quantization and mixed-precision recipes.
    -   **Training (`trainer/`)**: `lora.py` implements fine-tuning using LoRA adapters. Supports `train_on_completions`.
    -   **Evaluation (`evals/`)**: Scripts for benchmarks like MMMU.

3.  **Applications**
    -   **Server (`server.py`)**: OpenAI-compatible API for VLM serving.
    -   **Chat UI (`chat_ui.py`)**: Gradio interface.
    -   **Computer Use (`computer_use/`)**: Autonomous GUI agent using a dual-model (Planner + Grounder) approach.

## Data Flow (Inference)

1.  **Input**: User provides Text Prompt + Images/Video.
2.  **Preprocessing**:
    -   `prompt_utils` formats text into model-specific chat template.
    -   `utils.load_image` / `video_generate.fetch_video` loads and resizes visual data.
    -   `prepare_inputs` tokenizes text and creates pixel tensors.
3.  **Model Forward Pass**:
    -   **Standard**: Vision Tower -> Projector -> Replace `<image>` tokens in text embeddings.
    -   **Florence-2**: Vision Tower -> Prepend features to text embeddings -> Encoder-Decoder generation.
    -   **Molmo**: Vision Tower -> Add features to text embeddings at `image_input_idx`.
4.  **Generation**:
    -   `generate_step` yields tokens using KV Caching and Sampling (Temp/Top-P).
    -   `stream_generate` detokenizes outputs in real-time.

## Key Design Patterns

-   **Factory Pattern**: `utils.load()` dynamically imports and instantiates model classes based on `config.json` model type.
-   **Adapter Pattern**: `LoRaLayer` wraps linear layers to enable parameter-efficient fine-tuning without modifying the base model.
-   **Composition**: Models are composed of `VisionModel`, `LanguageModel`, and `MultiModalProjector` classes, allowing mix-and-match of components.
-   **Metal Optimization**: Custom Metal kernels (`kernels.py`) are used for performance-critical operations like `bicubic_interpolate` and `nearest_interpolate` to match PyTorch behavior exactly.
-   **Unified Interface**: All models expose a similar API (`get_input_embeddings`, `sanitize`), abstracting away architectural differences (e.g., how they handle padding or rotary embeddings).

## Build & Deployment
-   **Distribution**: PyPI package `mlx-vlm`.
-   **Dependency Management**: `requirements.txt` and `pyproject.toml`.
-   **Model Management**: Automatic download/caching from Hugging Face Hub.
-   **CI/CD**: GitHub Actions for publishing (`python-publish.yml`) and testing (`tests.yml`).

## Supported Model Families
-   **Standard**: LLaVA, LLaVA-Next, PaliGemma.
-   **Advanced**: Qwen2-VL (M-RoPE, Video), Pixtral (2D-RoPE), Idefics3 (Dynamic Packing).
-   **Specialized**: DeepSeek-VL, Molmo, SmolVLM, Florence-2 (Encoder-Decoder).