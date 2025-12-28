# Code Quality Report (mlx-vlm)

## Executive Summary

The core `mlx_vlm/` package is generally well-structured and implements a strong multimodal inference pipeline (model loading/dispatch, prompt formatting, streaming generation, conversion/quantization, and multiple user-facing entry points like CLI, server, and UI). On re-evaluation, several **cross-file correctness issues** stand out in the “core” tools:

- Multiple CLIs use inverted argparse flags (notably `--verbose` with `action="store_false"`), which changes default behavior and can lead to “no output by default” in some scripts.
- Some entry points call `load(...)` with non-existent kwargs (`processor_kwargs`, `processor_config`), which will likely error because `utils.load` forwards `**kwargs` to `AutoProcessor.from_pretrained`.
- Batch generation has a likely padding/attention mismatch: `_generate_batch` uses padded token ids but does not use `attention_mask` to compute true per-sample lengths/left-padding.
- `trainer/lora.py:replace_lora_with_linear` appears to have a quantized-layer merge bug (uses `group_size/bits` attributes from an `nn.Linear` instance).

The largest code-quality risks in the analyzed scope remain concentrated in `computer_use/`: extensive copy/paste duplication, undeclared dependencies, and multiple uses of `eval()` to parse model output (critical security issue).

**Scope note (per request):** This report intentionally skips `.github/`, `docs/`, `mlx_vlm/models/`, and `mlx_vlm/tests/` for now.

## Project Structure Evaluation

- **Directory organization:** Clear separation between core library (`mlx_vlm/`), examples (`examples/`), and a separate demo app (`computer_use/`). This keeps the main library focused.
- **Separation of concerns:** Within `mlx_vlm/`, responsibilities are mostly cleanly split (`prompt_utils.py` for formatting, `tokenizer_utils.py` for streaming detokenization, `generate.py` for generation, `convert.py` for conversion/quantization, `trainer/` for training).
- **Dependency structure:** The root `requirements.txt` is a “kitchen sink” dependency set (server/training/video/audio all included). Consider splitting into optional extras to keep the default install smaller and reduce transitive risk.

## Code Duplication Analysis

- **High duplication (needs refactor):** `computer_use/gui_agent.py` vs `computer_use/gui_agent_voice.py`, and `computer_use/autonomous_gui_agent.py` vs `computer_use/autonomous_gui_agent_voice.py` share large blocks of identical code (prompts, action implementations, parsing, main loops). This strongly increases maintenance cost and spreads security fixes across files.
- **Moderate duplication:** Video CLIs (`mlx_vlm/smolvlm_video_generate.py` vs `mlx_vlm/video_generate.py`) overlap conceptually; the latter is a generalized implementation while the former is model-specific. Consider consolidating once model support stabilizes.
- **Copy/paste CLI bugs:** multiple `mlx_vlm/*` scripts repeat the same argparse mistake (`action="store_false"` for “enable” flags). This is a good candidate for consolidation into shared CLI helpers to prevent drift.
- **Good centralization already present:** `mlx_vlm/evals/utils.py` centralizes inference, reducing duplication across benchmarks; `mlx_vlm/prompt_utils.py` centralizes model prompt formats well.

## Standard Library Opportunities

- **Replace `pandas` for CSV logging:** `computer_use/utils.py` logs navigation history to CSV; this can be implemented with `csv.DictWriter` (and `pathlib`) to remove a heavy dependency and simplify installation.
- **Replace `eval()` for parsing model output:** Use `ast.literal_eval()` at minimum, or prefer a JSON schema + `json.loads()` and strict validation. This is both a security and correctness improvement.
- **Path handling:** Replace hardcoded absolute paths (noted in `computer_use/autonomous_gui_agent_voice.py`) with `pathlib.Path` relative to the repository/module.

## File-by-File Summary (Analyzed Scope)

For detailed per-file notes, see `.llm_analysis/_notes/`. Processed file list is tracked in `.llm_analysis/_progress.md`.

- **Root/config/tooling:** `.gitignore`, `pyproject.toml`, `requirements.txt`, `.pre-commit-config.yaml`, `mkdocs.yml`, `update_changelog.py`, `README.md`, `CONTRIBUTING.md`, `LICENSE`, `AGENTS.md`.
- **`computer_use/` (demo app):**
  - `utils.py` (image annotation + navigation history logging; dependency + coordinate-system issues flagged).
  - `gui_agent.py`, `gui_agent_voice.py` (GUI automation agents; large duplication; `eval()` parsing risk; undeclared deps).
  - `autonomous_gui_agent.py`, `autonomous_gui_agent_voice.py` (two-model autonomous agent; duplication; `eval()` risk; hardcoded path flagged in voice variant).
  - `requirements.txt`, `README.md`, `navigation_history.csv`, `audio/*.wav` (7), `screenshots/*.png` (27).
- **`dev/`:** `load_q.py` (developer helper).
- **`examples/`:**
  - Scripts: `utils.py` (visualization helpers; `matplotlib` dependency), `omni.py`, `qwen3_omni_demo.py`.
  - Notebooks: `interleaved_text_images.ipynb`, `multi_image_generation.ipynb`, `object_detection.ipynb`, `object_pointing.ipynb`, `object_pointing_molmo2.ipynb`, `ocr_with_region.ipynb`, `text_extraction.ipynb`, `video_understanding.ipynb`.
  - Media: `images/*` (8), `videos/fastmlx_local_ai_hub.mp4`.
- **`mlx_vlm/` (core library):**
  - Core entry points: `__main__.py`, `chat.py`, `chat_ui.py`, `server.py`, `generate.py`, `video_generate.py`, `smolvlm_video_generate.py`, `convert.py`, `lora.py`, `LORA.MD`.
  - Core utilities: `utils.py` (loading/dispatch + multimodal input prep), `prompt_utils.py`, `sample_utils.py`, `tokenizer_utils.py`, `deprecation.py`, `version.py`, `__init__.py`.
  - Evals: `evals/*.py` (MMMU/MMStar/OCRBench/MathVista + shared `evals/utils.py`).
  - Training: `trainer/*` (training loop + LoRA implementation and helpers).

## Recommendations (Priority Ordered)

1. **Eliminate `eval()` in `computer_use/` immediately** and replace with JSON (preferred) or `ast.literal_eval()` + strict schema validation.
2. **Refactor `computer_use/` to remove copy/paste duplication** by extracting shared prompts, action implementations, and command processing into a shared module (keep only UI loop differences in each script).
3. **Fix core CLI correctness issues:**
   - Replace inverted argparse flags (e.g., `--verbose` should likely be `store_true`).
   - Fix incorrect `load(...)` kwarg usage (`processor_kwargs`/`processor_config` → `trust_remote_code=True`).
4. **Harden batch generation correctness:** use `attention_mask` to compute per-sample prompt lengths / left-padding (or disable tokenizer padding and let the batch generator do consistent padding/masking).
5. **Fix `trainer/lora.py` LoRA merge for quantized layers:** ensure `replace_lora_with_linear` preserves quantization settings correctly (or explicitly document that quantized layers aren’t supported).
6. **Fix dependency hygiene and scope:** either add missing `computer_use/` deps (e.g., `pyautogui`, `pyperclip`, `pynput`, etc.) and document them, or split optional features into extras (`[server]`, `[ui]`, `[train]`, `[examples]`, `[computer_use]`).
7. **Replace `pandas` CSV logging with stdlib** (or add `pandas` explicitly if it must remain).
8. **Validate and document version constraints** (notably `transformers>=4.57.0`), and consider pinning/CI-testing known-good dependency sets.
9. **Manage complexity hotspots with docs:** add internal documentation for complex areas (`BatchGenerator`, multimodal `prepare_inputs`) to improve contributor onboarding.
10. **Consider future modularization of `mlx_vlm/utils.py`** if it continues to grow (split by responsibility while keeping a stable public API).
