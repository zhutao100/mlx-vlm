# Partial Summary 0 (Previously Processed Files)

This summary compresses findings from the already-analyzed non-model, non-test code in the repository (core library, tooling, examples, and `computer_use`). Direct per-file notes live in `.llm_analysis/_notes/`.

## Project Structure (high level)

- Core package: `mlx_vlm/` (loading/dispatch, generation, prompts, server, chat UI, trainer, evals).
- Demos: `examples/` (notebooks + small Python scripts).
- Separate app: `computer_use/` (GUI-agent demo, optional voice mode).
- Build/tooling: `pyproject.toml`, `requirements.txt`, pre-commit config, changelog helper.

## Strengths

- `mlx_vlm/utils.py` + `mlx_vlm/generate.py` implement a fairly complete and ergonomic inference pipeline (model loading, multimodal input preparation, batching optimizations, streaming generation).
- `mlx_vlm/chat_ui.py` provides a feature-rich Gradio UI with thoughtful UX (model switching, streaming, persistence, stats).
- Training code under `mlx_vlm/trainer/` is reasonably structured (dataclass config, clear training loop, LoRA integration).

## Quality Risks / Issues Flagged

- Dependency hygiene:
  - `computer_use/utils.py` uses `pandas` for CSV writing, but it is not listed in `computer_use/requirements.txt` (likely runtime error).
  - `mlx_vlm/chat_ui.py` depends on `gradio` and Hugging Face tooling; these appear to be “extras” and should be documented/packaged as optional dependencies.
  - `requirements.txt` pins `transformers>=4.57.0`, which looks unusually high and may be a typo or requires explanation.
- “Kitchen sink” growth: `mlx_vlm/utils.py` is central and large; it’s currently organized, but is a natural hotspot for future bloat.
- Complexity hotspots: `BatchGenerator` / batching logic in generation is necessarily complex; contributor onboarding could benefit from extra internal docs or diagrams.
- Small correctness ambiguity: `computer_use/utils.py:draw_point` docstring vs implementation disagree on coordinate system (normalized vs pixel coordinates).

## Deferred Areas (per user request)

- Skipped for now: `.github/`, `docs/`, `mlx_vlm/models/`, `mlx_vlm/tests/`.
