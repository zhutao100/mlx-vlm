# Training & Evaluation Analysis

## Training (`mlx_vlm/trainer/`)
- **`Trainer` Class**:
    - Implements standard supervised fine-tuning loops.
    - **Loss**: Cross-entropy. Supports `train_on_completions` (masking user prompts so only assistant responses are trained).
    - **Optimization**: Uses `mlx.optimizers`. Supports gradient clipping and checkpointing.
- **LoRA Support (`utils.py`)**:
    - `get_peft_model`: Injects `LoRaLayer` adapters into the model.
    - `find_all_linear_names`: Automatically identifies target layers (usually in the LLM part), skipping vision towers and projectors by default.
    - `freeze_model`: Freezes base model parameters to ensure efficient fine-tuning.
- **Data Loading**:
    - `Dataset` class wraps Hugging Face Datasets.
    - Handles chat template application and input preparation (tokenization, image processing).

## Evaluation (`mlx_vlm/evals/`)
- **Benchmarks**:
    - `MMMU`: Massive Multi-discipline Multimodal Understanding.
    - Scripts handle dataset loading, inference, answer extraction (regex-based for multiple choice), and scoring.
- **Utils**:
    - `inference()`: Wrapper around the core `generate` function to simplify evaluation scripts.
