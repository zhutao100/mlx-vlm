# Prompt caching

## Current status

Prompt caching exists in the generation core as an **internal API**, not yet as a stable end-user workflow.

Implemented pieces:

- `PromptCacheMetadata`, `PromptCacheContext`, and `PromptCacheBundle` (`mlx_vlm/prompt_cache.py`)
- `generate_step(..., prompt_cache_bundle=...)` support (`mlx_vlm/generate.py`)
- tests for:
  - reusing cached cross-attention states,
  - reusing cached encoder outputs,
  - restoring LM state such as `rope_deltas`,
- rejecting invalid placeholder-token reuse when media is absent (`mlx_vlm/tests/`)

## What is currently implemented

### Bundle types

`PromptCacheBundle` stores:

- `kv_cache`
- `tokens_processed`
- optional multimodal `context`
- `model_state`
- `metadata`

### Generation integration

`generate_step()` can:

- reuse a bundle’s KV cache,
- pass cached `cross_attention_states` or `encoder_outputs` back into the language model,
- restore captured LM state before decoding,
- update the bundle during generation (`mlx_vlm/generate.py`).

## What is not surfaced yet

The audited codebase does **not** currently provide a documented, first-class end-user interface for:

- loading prompt caches from disk,
- saving prompt caches from CLI commands,
- reusing prompt caches via documented server request fields,
- session-level prompt cache management in the terminal chat / Gradio UI.

If you need prompt caching today, treat it as a Python-level integration point.

## Related planning docs

Future-work notes live under:

- [`dev_plans/prompt_caching/prompt_caching_mvp.md`](dev_plans/prompt_caching/prompt_caching_mvp.md)
- [`dev_plans/prompt_caching/prompt_caching_phased_plan.md`](dev_plans/prompt_caching/prompt_caching_phased_plan.md)
