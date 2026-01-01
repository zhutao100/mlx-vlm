# Prompt Caching (Image + Video)

**Goal**
- Add *multimodal* prompt caching so repeated / multi-turn runs can reuse **(1)** text KV cache **and** **(2)** the *vision/video-derived context* required for decoding (e.g., `cross_attention_states` / `encoder_outputs`), with optional disk persistence and strict compatibility checks.

**Current Anchors In Repo**
- KV cache plumbing exists: `mlx_vlm/models/cache.py:1` (`make_prompt_cache` delegates to `model.make_cache()` or `KVCache`/`RotatingKVCache`).
- Generation already accepts `prompt_cache`, but CLI doesn’t load/persist it: `mlx_vlm/generate.py:209` (`generate_step(..., prompt_cache=...)`) and `mlx_vlm/generate.py:1268` (TODO “Load prompt cache from file”).
- Multimodal decode requires extra tensors beyond KV: `mlx_vlm/generate.py:330` (threads `outputs.cross_attention_states` / `outputs.encoder_outputs` into the decode loop).

---

## Phase 0 — Decide MVP Scope (and explicitly document it)
- MVP behavior: cache makes *subsequent turns fast* when **no new media is introduced after the cached prefix** (text-only continuation). This covers “ask multiple questions about the same image/video” once the media is already in-context.
- Defer/optional for later: caching across *branching prompts* (same prefix, different suffix) and caching that supports *adding new images/videos after load* (requires more model/processor-specific handling).

---

## Phase 1 — Define the Cache “Bundle” Type (KV + multimodal context + metadata)
Add a single internal representation so the rest of the code stays model-agnostic.

- Add a new module, e.g. `mlx_vlm/prompt_cache.py` (new), defining:
  - `PromptCacheBundle`
    - `kv_cache: list[Any]` (existing per-layer caches)
    - `context: VisionContext | None` (see below)
    - `model_state: dict[str, Any]` (non-KV per-session LM state, e.g. M-RoPE deltas)
    - `tokens_processed: int` (how many prompt tokens the KV represents)
    - `metadata: PromptCacheMetadata` (validation + debugging)
  - `VisionContext`
    - `kind: Literal[\"cross_attention_states\",\"encoder_outputs\",\"none\"]`
    - `data: Any` (a PyTree of `mx.array`; supports array or list/tuple of arrays)
  - `PromptCacheMetadata` (store as JSON)
    - model identifiers: `model_id`, `revision`, optional `adapter_hash`
    - model shape signature: num layers, heads/head_dim (when available)
    - processor/preprocess signature: image resize policy, processor class name + key config
    - media signature(s): image/video fingerprints + frame sampling params (see Phase 6)
    - `format_version` (so future changes can be handled safely)

Key design point: `VisionContext` is the “adapter” layer that avoids generation code turning into model-specific branching.

---

## Phase 2 — Make `generate_step` Cache-Aware for Multimodal Context
Today `generate_step` only *discovers* context from the first forward pass and then uses it inside the same call. We need it to optionally *reuse* a previously stored context across turns/runs.

### Model pattern reality check (drives Phase 2.1)
Not all VLM families expose `cross_attention_states` or `encoder_outputs`. In this repo there are (at least) three practical categories:

- **Context-tensor models**: require cached `cross_attention_states` or `encoder_outputs` for correct decode when media inputs are not resent.
- **Embedding-injection models**: image/video influence is “baked into” the prefix KV cache; no extra decode-time tensors exist.
- **Embedding-injection + M-RoPE models** (e.g. Qwen*, GLM4V*): correctness depends on mutable per-instance LM state like `language_model._rope_deltas`, which must be treated as part of the cache bundle for safe reuse across sessions/processes.

- Update `mlx_vlm/generate.py:209` (`generate_step`) to accept **either**:
  - `prompt_cache_bundle: PromptCacheBundle | None` (preferred), **or**
  - keep existing `prompt_cache: list[Any] | None` and add `prefill_context: VisionContext | None`
- Change decode kwargs selection (currently at `mlx_vlm/generate.py:334`) to:
  - prefer `outputs.cross_attention_states` / `outputs.encoder_outputs` when present,
  - otherwise fall back to provided cached `prefill_context` (so text-only continuation can still “see” the earlier image/video).
- Ensure the *returned/updated* state is accessible:
  - either return an updated `PromptCacheBundle` from `stream_generate` / `generate`, or provide an explicit “session” wrapper for chat/server.

Acceptance criteria for this phase:
- A follow-up generation call with `pixel_values=None` can still decode with the original image/video context if the cached `VisionContext` is provided.

### Phase 2.1 — Capture/Restore LM Instance State + Safety Guard
To support embedding-injection families (especially M-RoPE variants) without relying on a single global model instance:

- Capture/restore **LM instance state** into/from `PromptCacheBundle.model_state`:
  - initial supported key: `rope_deltas` (mirrors `language_model._rope_deltas` used by Qwen*/GLM4V*).
- Add a **safety guard** when reusing a cached prefix with `pixel_values=None`:
  - if the provided `input_ids` include image/video placeholder token ids (from `model.config`), reject the call with a clear error
  - rationale: embedding-injection models must not recompute placeholder tokens without media inputs (hunyuan_vl, deepseekocr, Qwen*, GLM4V*).

---

## Phase 3 — In-Process Session Caching (Chat + Server) Without Disk (lowest risk)
This is the quickest path to delivering value and matches the research’s “start in-process” recommendation.

### Chat CLI(s)
- Update `mlx_vlm/generate.py:1246` (`--chat` loop) and/or `mlx_vlm/chat.py:1` to keep a per-session object:
  - `session.bundle` persists across turns
  - On each new user turn:
    - build the full prompt as today via `apply_chat_template` (`mlx_vlm/prompt_utils.py:397`)
    - tokenize full prompt
    - compute suffix tokens vs `session.bundle.tokens_processed` (strict prefix check; if mismatch, reset session)
    - call `generate_step` with only suffix tokens + `session.bundle`
- When `/image ...` (or equivalent) changes media, reset session bundle.

### Server
- Add an in-memory session cache in `mlx_vlm/server.py:1` keyed by `(model_cache_key, session_id)`:
  - store `PromptCacheBundle` + last-known prompt token hash/prefix length
  - TTL/LRU eviction to prevent unbounded growth
  - behavior on mismatch: configurable “reset or error”
- Expose session control minimally (pick one):
  - a `session_id` field in request payload, or a header, or reuse an existing OpenAI-compatible field if present.

---

## Phase 4 — Disk Persistence (KV + VisionContext) + CLI Wiring
Once in-memory works, add persistence. Use `.safetensors` to match ecosystem expectations.

### Serialization / IO
- Implement `save_prompt_cache_bundle(path, bundle)` / `load_prompt_cache_bundle(path)` in `mlx_vlm/prompt_cache.py`:
  - store arrays with `mx.save_safetensors`
  - store a single JSON metadata blob in safetensors metadata, e.g. `metadata[\"mlx_vlm_prompt_cache\"] = json.dumps(...)`
  - flatten/unflatten `VisionContext.data` with `mlx.utils.tree_flatten/tree_unflatten`
  - KV cache:
    - reuse mlx-lm’s pattern (`state`, `meta_state`, class name) but with a **local class registry** (because `mlx_lm.models.cache.load_prompt_cache` can’t reconstruct mlx-vlm-local cache classes)
- Compatibility checks on load:
  - exact model id/revision (or explicit `--cache-allow-model-mismatch`)
  - layer count + cache class list
  - kv quantization settings consistency (if KV is quantized)

### CLI
- Update `mlx_vlm/generate.py:33` arg parser to add:
  - `--prompt-cache-in PATH`
  - `--prompt-cache-out PATH`
  - `--cache-strict/--cache-reset-on-mismatch`
- Wire non-chat path TODO at `mlx_vlm/generate.py:1268`:
  - if `--prompt-cache-in` provided, load bundle and run as “append tokens onto cache”
  - if `--prompt-cache-out` provided, save the updated bundle at end (or additionally provide “save right after prefill” once the API separates prefill cleanly)

Also mirror these flags into `mlx_vlm/video_generate.py:1` and `mlx_vlm/smolvlm_video_generate.py:1` for parity.

---

## Phase 5 — Token Boundary / Prefix-Match Strategy (avoid silent corruption)
To safely “append” onto an existing KV cache you must guarantee the new prompt is a continuation of the cached prompt.

- Store in `PromptCacheBundle`:
  - `tokens_processed`
  - `prompt_prefix_hash` (hash of the cached token ids, or at least last N tokens + length)
- On reuse:
  - tokenize the intended prompt (or the minimal append chunk)
  - assert cached tokens are an exact prefix; if not:
    - strict mode: error
    - reset mode: discard cache and recompute (and optionally overwrite `--prompt-cache-out`)

---

## Phase 6 — Media Key Scheme + Video-Specific Validations (for “image + video” correctness)
Even if you cache full prompt state, you want metadata that prevents accidental reuse with different effective media preprocessing.

- Implement a small helper module (new), e.g. `mlx_vlm/media_fingerprint.py`:
  - Image:
    - prefer sha256 of original bytes for local files/URLs
    - include preprocess signature: resize shape, processor image settings that affect tokenization/patching
  - Video:
    - include frame sampling policy (fps/max_frames/stride/indices), resize policy
    - fingerprint options:
      - “full”: sha256 of entire file (slow)
      - “fast”: (size, mtime, sampled byte ranges) + selected frame timestamps/indices (document trade-off)
- Store this in cache metadata; on load, validate when the user provides media again.

---

## Phase 7 — Tests (prove correctness + invalidation)
Add tests under `mlx_vlm/tests/` (keep them CPU/mocked where possible):

- Deterministic equality (temperature=0):
  - baseline: run without cache
  - cached: run with a prefilled `PromptCacheBundle` + continuation
  - assert identical generated token ids
- Multimodal context reuse:
  - mock a model whose logits depend on `cross_attention_states` to ensure missing context breaks equivalence, but cached context restores it
- Invalidation:
  - change preprocess signature (resize or video frame policy) ⇒ cache rejected/reset
  - change model id/revision ⇒ cache rejected/reset

---

## Phase 8 — Docs & Support Matrix
- Update architecture docs to mention prompt caching and what’s stored: `docs/PROJECT_ARCHITECTURE.md:1`
- Add a short “Prompt caching” doc page describing:
  - in-memory session caching vs disk
  - recommended usage for image/video chat
  - limitations (e.g., “no new media after cache” in MVP)
  - file size expectations + tips (`--max-kv-size`, KV quantization)

---

## Optional Phase 9 — Per-Media Feature Caching (Option B / Hybrid)
If you want cache reuse *across different prompts referencing the same media*, add a separate feature cache keyed by media fingerprint:
- Cache vision encoder outputs / projected embeddings (model-dependent), then rebuild prompt KV for new text quickly.
- This likely needs per-model adapters around `get_input_embeddings` (already used in batch path at `mlx_vlm/generate.py:1162`).

---

**Deliverable Milestones**
- M1: In-memory session caching works for image/video chats (no disk) and reuses `VisionContext` correctly.
- M2: `.safetensors` save/load of full `PromptCacheBundle` with strict validation.
- M3: CLI/server flags wired; tests passing; docs updated.
