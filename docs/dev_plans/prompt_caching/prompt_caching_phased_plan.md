# Prompt caching phased plan

This page tracks likely follow-on work after the currently implemented prompt-cache internals.

## Current anchors in the repo

Implemented now:

- `mlx_vlm/prompt_cache.py` — bundle / metadata / context types,
- `mlx_vlm/generate.py` — bundle-aware `generate_step()` path,
- `mlx_vlm/tests/test_prompt_cache_in_generate_step.py` — cached multimodal context reuse,
- `mlx_vlm/tests/test_prompt_cache_model_state_in_generate_step.py` — LM-state restore and safety checks.

## Model patterns

Not all VLM families expose `cross_attention_states` or `encoder_outputs`. In practice there are a few categories that drive what a prompt-cache bundle must store:

- **Context-tensor models**: require cached `cross_attention_states` or `encoder_outputs` for correct decode when media inputs are not resent.
- **Embedding-injection models**: media influence is “baked into” the prefix KV cache; no extra decode-time tensors exist.
- **Embedding-injection + M-RoPE models** (e.g. Qwen*, GLM4V*): correctness depends on mutable per-instance LM state like `language_model._rope_deltas`, which must be captured/restored for safe reuse across sessions/processes.

For safety, reuse must reject media placeholder tokens in `input_ids` when `pixel_values=None` (otherwise embedding-injection families may silently produce incorrect results).

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
