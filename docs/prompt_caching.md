# Prompt Caching (Image + Video) — MVP Scope

This page documents the intended *minimum viable product (MVP)* scope for adding **multimodal prompt caching** (image + video) to MLX-VLM (feature request: `Blaizzy/mlx-vlm#149`).

## Problem Statement

Repeated or multi-turn interactions with the same visual input (image/video) are expensive because they re-run:

- vision/video preprocessing and encoding
- multimodal prefill over the prompt tokens

The goal of prompt caching is to reuse previously computed **prefix state** so follow-up questions can start decoding quickly.

## Definitions

- **KV cache**: the per-layer attention key/value state used by the text decoder during generation.
- **Multimodal context**: model-dependent tensors derived from media and used during decoding, e.g.:
  - `cross_attention_states` (decoder-only + cross-attn)
  - `encoder_outputs` (encoder-decoder)
- **Prompt cache bundle**: a single object containing KV cache + optional multimodal context + metadata needed for validation.

## MVP Goals (Phase 0 Decision)

The MVP targets the most common user workflow: **ask multiple questions about the same media**.

- **In-process session caching first** (no disk persistence required for MVP):
  - cache lives in memory for a chat/server session
  - reused across turns to avoid recomputing prefill and media encoding
- **Supports image and video** *as multimodal prefixes*:
  - media is introduced once (initial turn)
  - subsequent turns are **text-only continuations** (no new media added)
- **Strict correctness over silent reuse**:
  - reuse is allowed only when the new prompt is a strict suffix-append of the cached prompt tokens
  - on mismatch: reset cache (or error if configured)

## MVP Non-Goals (Explicitly Out of Scope)

These are intentionally deferred to later phases to keep the first implementation low-risk:

- **Cross-process / disk cache** (save/load `.safetensors`) as a user-facing feature
- **Branching prompt reuse** (reuse same cached prefix for multiple divergent suffixes)
- **Per-media feature cache** (cache vision features keyed only by media hash and reuse across different prompts)
- **Adding new images/videos after cache reuse begins**
  - e.g. “turn 1 has image A, turn 3 adds image B” is not guaranteed to hit the cache in MVP
- **Cache reuse across different preprocessing policies**
  - resizing, patching, frame sampling policy changes invalidate cache
- **Cache portability across model revisions/adapters**
  - different model/config/tokenizer/processor versions invalidate cache by default

## Compatibility Rules (MVP)

The cache is considered valid only if all of the following match:

- model identity (repo/path) and revision (or equivalent)
- relevant model config signature (layers/heads/head_dim and any cache-relevant params)
- processor/preprocess signature (image resize policy; for video: fps/max_frames/stride or explicit frame indices)
- the cached prompt tokens are an exact prefix of the current prompt tokens

## Follow-On Work (Post-MVP)

Once the in-process session caching is stable:

- add disk persistence (`--prompt-cache-in/--prompt-cache-out`) with strict validation
- add per-media feature caching (vision/video embeddings) to enable reuse across different prompts
- add robust keying for local files and URLs (trade-offs documented for video fingerprinting)

