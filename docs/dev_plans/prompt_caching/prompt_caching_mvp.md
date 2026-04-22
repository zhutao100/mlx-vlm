# Prompt caching MVP scope

This page is a planning note, not a statement of shipped CLI/server behavior.

## Current implementation baseline

Already implemented in the codebase:

- prompt-cache bundle types in `mlx_vlm/prompt_cache.py`,
- generation-time reuse/capture in `mlx_vlm/generate/ar.py` and streaming dispatch in `mlx_vlm/generate/dispatch.py`,
- tests for cached multimodal context and LM state restoration in `mlx_vlm/tests/test_prompt_cache*.py`.

## Practical MVP target

Bundle-specific follow-on work:

- reuse prompt-cache bundles for **append-only follow-up turns** against the same media,
- first as an in-process Python / session concept,
- then as a documented CLI/server workflow.

Upstream `PromptCacheState` and APC already cover separate conversation/server reuse paths. Reuse those interfaces where possible instead of adding a second session or disk-cache mechanism.

## Out of scope for the first surfaced workflow

- general-purpose cross-process cache portability,
- branching prompt reuse across divergent continuations,
- adding new media after reuse has started,
- silent compatibility fallback across different models / adapters / preprocess settings.
