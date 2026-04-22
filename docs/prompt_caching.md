# Prompt caching

## Current status

`PromptCacheBundle` is an **internal Python API** for append-only multimodal generation. It is separate from upstream's `PromptCacheState` conversation-prefix reuse and Automatic Prefix Caching (APC), which already provide their own session/server workflows and disk storage.

Implemented pieces:

- `PromptCacheMetadata`, `PromptCacheContext`, and `PromptCacheBundle` (`mlx_vlm/prompt_cache.py`)
- `generate_step(..., prompt_cache_bundle=...)` support (`mlx_vlm/generate/ar.py`)
- `stream_generate(..., prompt_cache_bundle=...)` support (`mlx_vlm/generate/dispatch.py`)
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
- update the bundle during generation.

`stream_generate()` forwards the bundle without creating a competing KV cache. Bundle use is mutually exclusive with `prompt_cache`, `prompt_cache_state`, and `apc_manager`; choose one cache owner for a request.

Reuse requires suffix-only input IDs without image/video placeholder tokens when `pixel_values=None`. Only `rope_deltas` is currently captured as language-model state; the bundle does not provide general model-state serialization or automatic compatibility validation.

## Bundle Workflow Limits

- No bundle-specific CLI flags, server request fields, or disk format.
- No automatic common-prefix trimming; callers supply append-only suffixes.
- `tokens_processed` is caller-maintained metadata, not a generation counter.
- Upstream APC/session caches are independent implementations, not serialized `PromptCacheBundle` objects.

## Related planning docs

Future-work notes live under:

- [`dev_plans/prompt_caching/prompt_caching_mvp.md`](dev_plans/prompt_caching/prompt_caching_mvp.md)
- [`dev_plans/prompt_caching/prompt_caching_phased_plan.md`](dev_plans/prompt_caching/prompt_caching_phased_plan.md)
