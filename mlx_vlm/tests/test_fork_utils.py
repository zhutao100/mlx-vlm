"""Regression coverage for the fork's loading and input normalization."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import mlx.core as mx
import mlx.nn as nn
import numpy as np
import pytest
from mlx.utils import tree_flatten

from mlx_vlm.utils import (
    get_class_predicate,
    load_model,
    normalize_fixed_quantization_config,
    prepare_inputs,
)


def test_quantization_overrides_require_compatible_modules_and_weights():
    config = {
        "group_size": 64,
        "bits": 4,
        "language_model": {"group_size": 32, "bits": 4},
    }
    module = nn.Linear(32, 8)
    predicate = get_class_predicate(quantization=config)
    assert predicate("language_model", module) == config["language_model"]
    assert predicate("language_model", nn.Linear(48, 8)) is False
    assert predicate("language_model", SimpleNamespace(weight=mx.zeros((8, 32)))) is False
    predicate = get_class_predicate(quantization=config, weights={})
    assert predicate("language_model", module) is False


def test_quantized_vision_checkpoint_takes_precedence_over_skip_vision():
    module = nn.Linear(64, 8)
    assert get_class_predicate(skip_vision=True)("vision_model", module) is False
    predicate = get_class_predicate(
        skip_vision=True, weights={"vision_model.scales": mx.ones((8, 1))}
    )
    assert predicate("vision_model", module) is True


def test_quantization_predicate_preserves_checkpoint_aliases():
    override = {"group_size": 32, "bits": 4}
    config = {"group_size": 64, "bits": 4, "packed.proj": override}
    model = SimpleNamespace(quantization_path_aliases=lambda path: ["packed.proj"])
    predicate = get_class_predicate(quantization_config=config, model=model)
    assert predicate("language_model.proj", nn.Linear(32, 8)) == override
    override["group_size"] = 0
    assert predicate("language_model.proj", nn.Linear(32, 8)) is False


@pytest.mark.parametrize("mode,group_size,bits", [("mxfp4", 32, 4), ("nvfp4", 16, 4), ("mxfp8", 32, 8)])
def test_normalize_fixed_quantization_config(mode, group_size, bits):
    config = {
        "mode": mode,
        "group_size": 64,
        "bits": 2,
        "fixed": {"mode": mode, "group_size": 64, "bits": 2},
        "affine": {"mode": "affine", "group_size": 128, "bits": 8},
    }
    assert normalize_fixed_quantization_config(config) is config
    assert (config["group_size"], config["bits"]) == (group_size, bits)
    assert (config["fixed"]["group_size"], config["fixed"]["bits"]) == (group_size, bits)
    assert config["affine"] == {"mode": "affine", "group_size": 128, "bits": 8}


@pytest.mark.parametrize("quant_method", ["awq", "gptq"])
def test_load_model_rejects_unsupported_quant_method(tmp_path, quant_method):
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "model_type": "qwen3_5",
                "quantization_config": {"quant_method": quant_method, "group_size": 128, "bits": 4},
            }
        )
    )
    with pytest.raises(ValueError, match=f"Quantization method '{quant_method}' is not supported"):
        load_model(tmp_path, lazy=True)


@pytest.mark.skipif(not mx.metal.is_available(), reason="BitNet's native kernel requires Metal")
@pytest.mark.parametrize("nested", [False, True], ids=["top-level", "text-config"])
def test_load_model_native_bitnet_checkpoint(tmp_path, nested):
    from mlx_vlm.models.bitnet import Model, ModelConfig

    config = {
        "model_type": "bitnet",
        "hidden_size": 16,
        "num_hidden_layers": 1,
        "intermediate_size": 32,
        "num_attention_heads": 4,
        "num_key_value_heads": 2,
        "rms_norm_eps": 1e-5,
        "vocab_size": 32,
    }
    source = Model(ModelConfig.from_dict(config))
    projection = source.layers[0].self_attn.q_proj
    projection.weight = mx.full(projection.weight.shape, 0x66, dtype=mx.uint8)
    projection.weight_scale = mx.array([0.5])
    quantization = {"quantization_config": {"quant_method": "bitnet"}}
    config.update({"text_config": quantization} if nested else quantization)
    (tmp_path / "config.json").write_text(json.dumps(config))
    mx.save_safetensors(str(tmp_path / "model.safetensors"), dict(tree_flatten(source.parameters())))

    loaded = load_model(tmp_path)
    assert isinstance(loaded, Model)
    loaded_projection = loaded.layers[0].self_attn.q_proj
    assert loaded_projection.weight.dtype == mx.uint8
    assert mx.array_equal(loaded_projection.weight, projection.weight).item()
    assert mx.array_equal(loaded_projection.weight_scale, projection.weight_scale).item()
    tokens = mx.array([[1, 2]], dtype=mx.int32)
    expected = source(tokens).logits
    actual = loaded(tokens).logits
    assert actual.shape == (1, 2, 32)
    assert mx.all(mx.isfinite(actual)).item()
    assert mx.allclose(actual, expected).item()


@pytest.mark.parametrize("nested", [False, True], ids=["top-level", "text-config"])
def test_load_model_direct_nvfp4_checkpoint(tmp_path, nested):
    class TinyModel(nn.Module):
        def __init__(self, config):
            super().__init__()
            self.config = config
            self.proj = nn.Linear(32, 4, bias=False)

    source = TinyModel(SimpleNamespace())
    nn.quantize(source, group_size=16, bits=4, mode="nvfp4")
    mx.save_safetensors(str(tmp_path / "model.safetensors"), dict(tree_flatten(source.parameters())))
    quantization = {"quantization_config": {"quant_method": "nvfp4"}}
    config = {"model_type": "test"}
    config.update({"text_config": quantization} if nested else quantization)
    (tmp_path / "config.json").write_text(json.dumps(config))
    architecture = SimpleNamespace(
        Model=TinyModel,
        ModelConfig=SimpleNamespace(from_dict=lambda _: SimpleNamespace()),
    )
    with patch("mlx_vlm.utils.get_model_and_args", return_value=(architecture, "test")):
        loaded = load_model(tmp_path)
    assert isinstance(loaded.proj, nn.QuantizedLinear)
    assert (loaded.proj.group_size, loaded.proj.bits, loaded.proj.mode) == (16, 4, "nvfp4")
    inputs = mx.ones((1, 32), dtype=mx.bfloat16)
    assert mx.array_equal(loaded.proj(inputs), source.proj(inputs)).item()


class MinimalProcessor:
    def __init__(self):
        self.tokenizer = SimpleNamespace(pad_token=None, eos_token="[EOS]")

    def __call__(self, text, images=None, audio=None, padding=False, return_tensors="mlx"):
        return {"input_ids": mx.array([1, 2, 3]), "attention_mask": mx.array([1, 1, 1])}


@pytest.mark.parametrize("images", [(), [], "", np.array([])])
def test_prepare_inputs_normalizes_empty_media_and_dict_tokenizer_output(images):
    result = prepare_inputs(MinimalProcessor(), prompts="test", images=images)
    assert result["input_ids"].tolist() == [[1, 2, 3]]
    assert result["attention_mask"].shape == (1, 3)


def test_prepare_inputs_accepts_audio_path(tmp_path):
    audio_path = tmp_path / "dummy.wav"
    with patch("mlx_vlm.utils.load_audio", return_value=np.zeros(8, dtype=np.float32)) as load_audio:
        result = prepare_inputs(MinimalProcessor(), prompts="test", audio=audio_path)
    load_audio.assert_called_once_with(audio_path, sr=16000)
    assert isinstance(result["input_ids"], mx.array)
