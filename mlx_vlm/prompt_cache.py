from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

PROMPT_CACHE_FORMAT = "mlx_vlm.prompt_cache"
PROMPT_CACHE_FORMAT_VERSION = 1

PromptCacheContextKind = Literal["cross_attention_states", "encoder_outputs"]


@dataclass(slots=True)
class PromptCacheMetadata:
    """
    Metadata for validating and debugging prompt cache reuse.

    This is intentionally schema-light in Phase 1 to keep the bundle flexible
    across model families. Later phases can tighten validation rules and add
    persistence without changing the in-memory object shape.
    """

    format: str = PROMPT_CACHE_FORMAT
    format_version: int = PROMPT_CACHE_FORMAT_VERSION

    # Optional, user/system-provided identifiers for compatibility checks.
    model: dict[str, Any] = field(default_factory=dict)
    processor: dict[str, Any] = field(default_factory=dict)
    media: list[dict[str, Any]] = field(default_factory=list)
    kv_cache: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": self.format,
            "format_version": self.format_version,
            "model": dict(self.model),
            "processor": dict(self.processor),
            "media": list(self.media),
            "kv_cache": dict(self.kv_cache),
        }

    def to_json(self) -> str:
        return json.dumps(
            self.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PromptCacheMetadata":
        return cls(
            format=str(data.get("format", PROMPT_CACHE_FORMAT)),
            format_version=int(data.get("format_version", PROMPT_CACHE_FORMAT_VERSION)),
            model=dict(data.get("model", {})),
            processor=dict(data.get("processor", {})),
            media=list(data.get("media", [])),
            kv_cache=dict(data.get("kv_cache", {})),
        )

    @classmethod
    def from_json(cls, text: str) -> "PromptCacheMetadata":
        return cls.from_dict(json.loads(text))


@dataclass(slots=True)
class PromptCacheContext:
    """
    Model-family specific context needed for decoding beyond the KV cache.

    Examples:
      - decoder-only + cross-attn models: `cross_attention_states`
      - encoder-decoder models: `encoder_outputs`
    """

    kind: PromptCacheContextKind
    data: Any


@dataclass(slots=True)
class PromptCacheBundle:
    """
    A first-class prompt cache bundle for multimodal generation.

    - `kv_cache` is the per-layer cache structure passed as `cache=...`.
    - `context` holds model-specific multimodal tensors required for decoding
      (e.g. cross-attention states or encoder outputs).
    - `tokens_processed` tracks how many prompt tokens the cache represents.
    """

    kv_cache: list[Any]
    tokens_processed: int = 0
    context: PromptCacheContext | None = None
    metadata: PromptCacheMetadata = field(default_factory=PromptCacheMetadata)

    def __post_init__(self) -> None:
        if self.tokens_processed < 0:
            raise ValueError("tokens_processed must be >= 0")
