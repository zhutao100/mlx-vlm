import importlib

import mlx.core as mx
import pytest

from mlx_vlm.prompt_cache import PromptCacheBundle


class _StoppingCriteria:
    def __call__(self, token: int) -> bool:
        return False


class _Tokenizer:
    def __init__(self) -> None:
        self.stopping_criteria = _StoppingCriteria()


class _Detokenizer:
    def __init__(self) -> None:
        self.last_segment = ""

    def reset(self) -> None:
        self.last_segment = ""

    def add_token(self, token: int, *, skip_special_token_ids=None) -> None:
        self.last_segment = f"token_{token}"

    def finalize(self) -> None:
        self.last_segment = ""


class _Processor:
    def __init__(self) -> None:
        self.tokenizer = _Tokenizer()
        self.detokenizer = _Detokenizer()


class _Config:
    model_type = "test_model"


class _Model:
    config = _Config()

    def parameters(self):
        return {}


def test_stream_generate_prompt_cache_bundle_does_not_conflict(monkeypatch):
    mod = importlib.import_module("mlx_vlm.generate.dispatch")

    def fake_generate_step(input_ids, model, pixel_values, mask, **kwargs):
        assert kwargs.get("prompt_cache_bundle") is not None
        assert "prompt_cache" not in kwargs
        yield 1, None

    monkeypatch.setattr(mod, "generate_step", fake_generate_step)

    processor = _Processor()
    model = _Model()

    input_ids = mx.array([[1]], dtype=mx.int32)
    mask = mx.ones_like(input_ids)
    bundle = PromptCacheBundle(kv_cache=[], tokens_processed=0)

    results = list(
        mod.stream_generate(
            model,
            processor,
            "hi",
            input_ids=input_ids,
            pixel_values=None,
            mask=mask,
            prompt_cache_bundle=bundle,
            max_tokens=2,
        )
    )

    assert results


@pytest.mark.parametrize("cache_option", ["prompt_cache_state", "apc_manager"])
def test_stream_generate_rejects_other_cache_owners_with_bundle(cache_option):
    mod = importlib.import_module("mlx_vlm.generate")
    with pytest.raises(ValueError, match=f"Provide only one of {cache_option} or prompt_cache_bundle"):
        next(mod.stream_generate(
            _Model(),
            _Processor(),
            "hi",
            prompt_cache_bundle=PromptCacheBundle(kv_cache=[]),
            **{cache_option: object()},
        ))
