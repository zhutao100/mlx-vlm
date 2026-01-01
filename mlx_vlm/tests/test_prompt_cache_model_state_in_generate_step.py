"""Tests for LM model_state capture/restore in mlx_vlm.generate.generate_step."""

from types import SimpleNamespace

import mlx.core as mx

from mlx_vlm.generate import generate_step
from mlx_vlm.prompt_cache import PromptCacheBundle


class FakeCache:
    def __init__(self, offset: int):
        self.offset = offset


class RopeDeltasLanguageModel:
    def __init__(self):
        self.layers = [object(), object()]
        self._rope_deltas = "WRONG"

    def __call__(self, input_ids, cache=None, **_kwargs):
        seq_len = int(input_ids.shape[1])
        vocab_size = 2
        prefer_zero = self._rope_deltas == "EXPECTED"
        logits = mx.zeros((1, seq_len, vocab_size), dtype=mx.float32)
        logits[..., 0 if prefer_zero else 1] = 1.0
        return SimpleNamespace(
            logits=logits, cross_attention_states=None, encoder_outputs=None
        )


class EmbeddingInjectionModel:
    def __init__(self, language_model):
        self.language_model = language_model
        self.config = SimpleNamespace(image_token_id=999)

    def __call__(self, input_ids, pixel_values, cache=None, mask=None, **kwargs):
        return self.language_model(input_ids, cache=cache, mask=mask, **kwargs)


def test_generate_step_restores_and_captures_rope_deltas_state():
    lm = RopeDeltasLanguageModel()
    model = EmbeddingInjectionModel(lm)
    input_ids = mx.array([[1, 2, 3]], dtype=mx.int32)
    mask = mx.ones((1, 3), dtype=mx.int32)

    bundle = PromptCacheBundle(
        kv_cache=[FakeCache(offset=10)],
        model_state={"rope_deltas": "EXPECTED"},
    )

    gen = generate_step(
        input_ids=input_ids,
        model=model,
        pixel_values=None,
        mask=mask,
        prompt_cache_bundle=bundle,
        max_tokens=2,
    )

    first_token, _ = next(gen)
    assert first_token == 0
    assert lm._rope_deltas == "EXPECTED"
    assert bundle.model_state["rope_deltas"] == "EXPECTED"


def test_generate_step_rejects_media_placeholders_when_reusing_cache_without_pixel_values():
    lm = RopeDeltasLanguageModel()
    model = EmbeddingInjectionModel(lm)
    input_ids = mx.array([[999, 2, 3]], dtype=mx.int32)
    mask = mx.ones((1, 3), dtype=mx.int32)

    bundle = PromptCacheBundle(
        kv_cache=[FakeCache(offset=10)],
    )

    gen = generate_step(
        input_ids=input_ids,
        model=model,
        pixel_values=None,
        mask=mask,
        prompt_cache_bundle=bundle,
        max_tokens=1,
    )

    try:
        next(gen)
        raise AssertionError("Expected ValueError due to placeholder tokens")
    except ValueError as exc:
        assert "append-only suffix tokens" in str(exc)
