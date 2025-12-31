"""Tests for PromptCacheBundle integration in mlx_vlm.generate.generate_step."""

from types import SimpleNamespace

import mlx.core as mx

from mlx_vlm.generate import generate_step
from mlx_vlm.prompt_cache import PromptCacheBundle, PromptCacheContext


class CrossAttentionLanguageModel:
    def __init__(self, *, return_context_in_output: bool):
        self.layers = [object(), object()]
        self.calls: list[dict[str, object]] = []
        self._return_context_in_output = return_context_in_output

    def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        assert "cross_attention_states" in kwargs

        seq_len = 1
        if args:
            input_ids = args[0]
            seq_len = int(input_ids.shape[1])

        logits = mx.concatenate(
            [mx.ones((1, seq_len, 1)), mx.zeros((1, seq_len, 7))], axis=-1
        )
        return SimpleNamespace(
            logits=logits,
            cross_attention_states=(
                kwargs["cross_attention_states"]
                if self._return_context_in_output
                else None
            ),
            encoder_outputs=None,
        )


class EncoderDecoderLanguageModel:
    def __init__(self, *, return_context_in_output: bool):
        self.layers = [object(), object()]
        self.calls: list[dict[str, object]] = []
        self._return_context_in_output = return_context_in_output

    def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        assert "encoder_outputs" in kwargs

        decoder_input_ids = kwargs.get(
            "decoder_input_ids", mx.array([[0]], dtype=mx.int32)
        )
        seq_len = int(decoder_input_ids.shape[1])
        logits = mx.concatenate(
            [mx.ones((1, seq_len, 1)), mx.zeros((1, seq_len, 7))], axis=-1
        )
        return SimpleNamespace(
            logits=logits,
            cross_attention_states=None,
            encoder_outputs=(
                kwargs["encoder_outputs"] if self._return_context_in_output else None
            ),
        )


def test_generate_step_uses_cached_cross_attention_states_when_pixel_values_none():
    lm = CrossAttentionLanguageModel(return_context_in_output=False)

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace()

        def __call__(self, *_args, **_kwargs):
            raise AssertionError("Top-level model call should be bypassed")

    model = Model()
    input_ids = mx.array([[1, 2, 3]], dtype=mx.int32)
    mask = mx.ones((1, 3), dtype=mx.int32)

    sentinel = object()
    bundle = PromptCacheBundle(
        kv_cache=[],
        context=PromptCacheContext(kind="cross_attention_states", data=sentinel),
    )

    gen = generate_step(
        input_ids=input_ids,
        model=model,
        pixel_values=None,
        mask=mask,
        prompt_cache_bundle=bundle,
        max_tokens=1,
    )
    next(gen)

    assert len(bundle.kv_cache) == len(lm.layers)
    assert bundle.context is not None
    assert bundle.context.kind == "cross_attention_states"
    assert bundle.context.data is sentinel

    assert len(lm.calls) == 2  # prefill + one decode step
    for call in lm.calls:
        assert call["kwargs"]["cross_attention_states"] is sentinel


def test_generate_step_captures_cross_attention_states_into_bundle():
    lm = CrossAttentionLanguageModel(return_context_in_output=True)
    sentinel = object()

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace()
            self.called = False

        def __call__(self, input_ids, pixel_values, cache=None, mask=None, **kwargs):
            self.called = True
            seq_len = int(input_ids.shape[1])
            logits = mx.concatenate(
                [mx.ones((1, seq_len, 1)), mx.zeros((1, seq_len, 7))], axis=-1
            )
            return SimpleNamespace(
                logits=logits,
                cross_attention_states=sentinel,
                encoder_outputs=None,
            )

    model = Model()
    input_ids = mx.array([[1, 2, 3]], dtype=mx.int32)
    mask = mx.ones((1, 3), dtype=mx.int32)
    pixel_values = mx.zeros((1, 3, 2, 2), dtype=mx.float32)

    bundle = PromptCacheBundle(kv_cache=[])
    gen = generate_step(
        input_ids=input_ids,
        model=model,
        pixel_values=pixel_values,
        mask=mask,
        prompt_cache_bundle=bundle,
        max_tokens=1,
    )
    next(gen)

    assert model.called is True
    assert bundle.context is not None
    assert bundle.context.kind == "cross_attention_states"
    assert bundle.context.data is sentinel


def test_generate_step_uses_cached_encoder_outputs_when_pixel_values_none():
    lm = EncoderDecoderLanguageModel(return_context_in_output=False)

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace(decoder_start_token_id=1)

        def __call__(self, *_args, **_kwargs):
            raise AssertionError("Top-level model call should be bypassed")

    model = Model()
    input_ids = mx.array([[1, 2, 3]], dtype=mx.int32)
    mask = mx.ones((1, 3), dtype=mx.int32)

    sentinel = object()
    bundle = PromptCacheBundle(
        kv_cache=[],
        context=PromptCacheContext(kind="encoder_outputs", data=sentinel),
    )

    gen = generate_step(
        input_ids=input_ids,
        model=model,
        pixel_values=None,
        mask=mask,
        prompt_cache_bundle=bundle,
        max_tokens=1,
    )
    next(gen)

    assert len(bundle.kv_cache) == len(lm.layers)
    assert bundle.context is not None
    assert bundle.context.kind == "encoder_outputs"
    assert bundle.context.data is sentinel

    assert len(lm.calls) == 2
    for call in lm.calls:
        assert call["kwargs"]["encoder_outputs"] is sentinel
