# Prompt caching phased plan

This page tracks likely follow-on work after the currently implemented prompt-cache internals.

## Current anchors in the repo

Implemented now:

- `mlx_vlm/prompt_cache.py` — bundle / metadata / context types,
- `mlx_vlm/generate.py` — bundle-aware `generate_step()` path,
- `mlx_vlm/tests/test_prompt_cache_in_generate_step.py` — cached multimodal context reuse,
- `mlx_vlm/tests/test_prompt_cache_model_state_in_generate_step.py` — LM-state restore and safety checks.

## Remaining phases

### Phase 1 — stable Python-level session abstraction

- wrap `PromptCacheBundle` in a higher-level session helper,
- document append-only reuse semantics clearly,
- expose a small supported example in docs/tests.

### Phase 2 — CLI workflow

- add explicit cache load/save flags to the generation CLI,
- validate cache/model/processor compatibility,
- document failure behavior on mismatch.

### Phase 3 — server workflow

- add an explicit request/session concept for cache reuse,
- keep eviction and lifetime rules simple and documented,
- avoid silent cross-model cache reuse.

### Phase 4 — persistence and validation

- define a durable on-disk format,
- persist both KV cache and multimodal context,
- validate model identity, processor settings, and media assumptions.

### Phase 5 — broader reuse

- branching continuations,
- media-feature caching separate from full prompt-prefix caching,
- better ergonomics for long-running multimodal sessions.
