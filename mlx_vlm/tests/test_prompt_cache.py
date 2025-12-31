"""Tests for prompt cache bundle types in mlx_vlm.prompt_cache."""

import pytest

from mlx_vlm.prompt_cache import (
    PROMPT_CACHE_FORMAT,
    PROMPT_CACHE_FORMAT_VERSION,
    PromptCacheBundle,
    PromptCacheContext,
    PromptCacheMetadata,
)


class TestPromptCacheMetadata:
    def test_defaults(self):
        meta = PromptCacheMetadata()
        assert meta.format == PROMPT_CACHE_FORMAT
        assert meta.format_version == PROMPT_CACHE_FORMAT_VERSION
        assert meta.model == {}
        assert meta.processor == {}
        assert meta.media == []
        assert meta.kv_cache == {}

    def test_round_trip_dict(self):
        meta = PromptCacheMetadata(
            model={"id": "mlx-community/foo", "revision": "main"},
            processor={"class": "AutoProcessor"},
            media=[{"kind": "image", "path": "img.png"}],
            kv_cache={"max_kv_size": 2048},
        )

        restored = PromptCacheMetadata.from_dict(meta.to_dict())
        assert restored == meta

    def test_round_trip_json(self):
        meta = PromptCacheMetadata(
            model={"id": "mlx-community/foo", "revision": "main"},
            processor={"resize_shape": [336, 336]},
        )

        restored = PromptCacheMetadata.from_json(meta.to_json())
        assert restored == meta


class TestPromptCacheBundle:
    def test_tokens_processed_must_be_non_negative(self):
        with pytest.raises(ValueError, match="tokens_processed must be >= 0"):
            PromptCacheBundle(kv_cache=[], tokens_processed=-1)

    def test_bundle_accepts_optional_context(self):
        ctx = PromptCacheContext(kind="cross_attention_states", data=object())
        bundle = PromptCacheBundle(kv_cache=[object()], tokens_processed=0, context=ctx)
        assert bundle.context is ctx
