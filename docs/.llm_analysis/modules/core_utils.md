# Core Utilities Analysis

## `mlx_vlm/utils.py`
This is the foundational utility module for the library.
- **Model Loading**: 
    - `load()`: Main entry point. Loads model and processor (tokenizer + image processor). Handles LoRA adapter application.
    - `load_model()`: Low-level model loading. Handles quantization, weight loading (from `.safetensors`), and configuration updates.
    - `get_model_and_args()`: Dynamic import of model architecture based on `model_type` from config. Uses `MODEL_REMAPPING` to map varied model names (e.g., "llava_qwen2" -> "fastvlm") to internal modules.
- **Data Processing**:
    - `process_image()`, `load_image()`: Handles image loading (URL/file/base64) and resizing.
    - `load_audio()`, `resample_audio()`: Audio loading and resampling.
    - `prepare_inputs()`: Complex logic to prepare inputs (text, images, audio) for the model. Handles padding, special tokens, and constructing `model_inputs` dict with `pixel_values` and `attention_mask`.
- **Quantization**:
    - `quantize_model()`: Quantizes models while respecting `skip_vision` flags to avoid quantizing vision encoders/projectors if needed.
    - `get_class_predicate()`: Helper to decide which layers to quantize.
- **Hub Integration**: `upload_to_hub()`, `fetch_from_hub()`.

## `mlx_vlm/prompt_utils.py`
Critical module for handling the diverse formatting requirements of different VLMs.
- **`MessageFormat` Enum**: Defines supported message formats (e.g., `LIST_WITH_IMAGE`, `IMAGE_TOKEN_NEWLINE`, `PROMPT_ONLY`).
- **`MODEL_CONFIG`**: Maps model types (e.g., "qwen2_vl", "llava") to `MessageFormat`.
- **`MessageFormatter`**:
    - Formats user prompts into the structure expected by the specific model.
    - Handles insertion of `<image>` tokens, multi-image support, and audio/video message formatting.
- **`apply_chat_template()`**: Applies the tokenizer's chat template to the formatted messages.

## `mlx_vlm/tokenizer_utils.py`
- Implements streaming detokenizers (`NaiveStreamingDetokenizer`, `SPMStreamingDetokenizer`, `BPEStreamingDetokenizer`) to handle real-time text generation decoding.
- `load_tokenizer()`: Auto-detects the correct detokenizer based on `tokenizer.json`.

## `mlx_vlm/sample_utils.py`
- Implements `top_p_sampling` for generation.
