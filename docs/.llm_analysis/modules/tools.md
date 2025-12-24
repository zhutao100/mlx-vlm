# Tools & Training Analysis

## `mlx_vlm/convert.py`
Utilities for converting Hugging Face models to MLX format.
- **Conversion Logic**:
    - `convert()`: Main function. Downloads model from Hub, optionally quantizes, and saves to MLX format.
    - **Quantization**:
        - Supports standard `affine` and `mxfp4` modes.
        - **Mixed-Precision**: Implements `mixed_quant_predicate_builder` to support complex recipes (e.g., `mixed_4_6`) where sensitive layers (like `down_proj` or specific indices) are kept at higher precision.
    - **Artifacts**: Copies python scripts and config JSONs to the output directory to ensure the model is self-contained.
    - **Hub Upload**: Can upload the converted model directly to HF Hub.

## `mlx_vlm/lora.py`
Fine-tuning script using LoRA (Low-Rank Adaptation).
- **Workflow**:
    1.  **Load Model**: Uses `load()` to get the base model.
    2.  **Prepare Dataset**: Loads from HF Datasets, checks for `messages` and `images` columns, and applies chat templates.
    3.  **Setup LoRA**: 
        - If `adapter_path` is provided, resumes training.
        - Else, targets linear layers in `model.language_model` using `find_all_linear_names`.
    4.  **Train**: Uses `Trainer` class (wrapper around optimization loop) to fine-tune.
    5.  **Save**: Saves adapters to disk.
- **Key Parameters**: `lora_rank`, `lora_alpha`, `lora_dropout`, `learning_rate`.
