# UI & Video Tools Analysis

## `mlx_vlm/chat_ui.py`
A Gradio-based web interface for MLX-VLM.
- **Model Management**: `ModelState` class handles loading/unloading models to manage GPU memory.
- **Model Discovery**: `get_cached_vlm_models()` scans the Hugging Face cache for models with `vision_config` to populate the dropdown.
- **Features**: 
    - Streaming generation.
    - Multi-modal input (text + images).
    - Adjustable parameters (temperature, max tokens, top_p).
    - Dark/Light theme toggle.

## `mlx_vlm/video_generate.py`
CLI tool for video understanding (Beta).
- **Video Processing**:
    - `VideoFrameExtractor`: Uses OpenCV (`cv2`) to extract frames at a specified FPS.
    - `smart_resize`: Intelligent resizing logic to maintain aspect ratio within pixel limits.
    - `fetch_video`: Abstraction to handle video files or sequences of images.
- **Model Support**:
    - Supports native video models (like Qwen2.5-VL) by passing video inputs directly to the processor.
    - Supports image-sequence models by treating video frames as a series of images.

## `mlx_vlm/smolvlm_video_generate.py`
Specialized CLI for SmolVLM2 video understanding.
- Simplified pipeline tailored for SmolVLM2's processor capabilities.
