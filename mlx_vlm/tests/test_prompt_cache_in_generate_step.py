"""Tests for PromptCacheBundle integration in mlx_vlm.generate.generate_step."""

from types import SimpleNamespace

import mlx.core as mx

from mlx_vlm.generate import generate_step
from mlx_vlm.prompt_cache import PromptCacheBundle, PromptCacheContext


class _EmbeddingOutput:
    def __init__(self, inputs_embeds: mx.array):
        self.inputs_embeds = inputs_embeds

    def to_dict(self) -> dict[str, mx.array]:
        return {"inputs_embeds": self.inputs_embeds}


class CrossAttentionLanguageModel:
    def __init__(
        self,
        *,
        require_context_in_call: bool,
        return_context_in_output: bool,
        output_context: object | None = None,
    ):
        self.layers = [object(), object()]
        self.calls: list[dict[str, object]] = []
        self._require_context_in_call = require_context_in_call
        self._return_context_in_output = return_context_in_output
        self._output_context = output_context

    def __call__(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        if self._require_context_in_call:
            assert "cross_attention_states" in kwargs

        seq_len = 1
        if args:
            input_ids = args[0]
            seq_len = int(input_ids.shape[1])
        elif "inputs" in kwargs:
            seq_len = int(kwargs["inputs"].shape[1])

        logits = mx.concatenate([mx.ones((1, seq_len, 1)), mx.zeros((1, seq_len, 7))], axis=-1)
        return SimpleNamespace(
            logits=logits,
            cross_attention_states=(self._output_context if self._return_context_in_output else None),
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

        seq_len = 1
        if args:
            input_ids = args[0]
            seq_len = int(input_ids.shape[1])
        elif "inputs" in kwargs:
            seq_len = int(kwargs["inputs"].shape[1])

        logits = mx.concatenate([mx.ones((1, seq_len, 1)), mx.zeros((1, seq_len, 7))], axis=-1)
        return SimpleNamespace(
            logits=logits,
            cross_attention_states=None,
            encoder_outputs=(kwargs["encoder_outputs"] if self._return_context_in_output else None),
        )


def test_generate_step_uses_cached_cross_attention_states_when_pixel_values_none():
    lm = CrossAttentionLanguageModel(require_context_in_call=True, return_context_in_output=False)

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace()

        def get_input_embeddings(self, input_ids, pixel_values=None, **_kwargs):
            seq_len = int(input_ids.shape[1])
            return _EmbeddingOutput(mx.zeros((1, seq_len, 1), dtype=mx.float32))

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
    sentinel = object()
    lm = CrossAttentionLanguageModel(
        require_context_in_call=False,
        return_context_in_output=True,
        output_context=sentinel,
    )

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace()

        def get_input_embeddings(self, input_ids, pixel_values=None, **_kwargs):
            seq_len = int(input_ids.shape[1])
            return _EmbeddingOutput(mx.zeros((1, seq_len, 1), dtype=mx.float32))

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

    assert bundle.context is not None
    assert bundle.context.kind == "cross_attention_states"
    assert bundle.context.data is sentinel


def test_generate_step_uses_cached_encoder_outputs_when_pixel_values_none():
    lm = EncoderDecoderLanguageModel(return_context_in_output=False)

    class Model:
        def __init__(self):
            self.language_model = lm
            self.config = SimpleNamespace()

        def get_input_embeddings(self, input_ids, pixel_values=None, **_kwargs):
            seq_len = int(input_ids.shape[1])
            return _EmbeddingOutput(mx.zeros((1, seq_len, 1), dtype=mx.float32))

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
