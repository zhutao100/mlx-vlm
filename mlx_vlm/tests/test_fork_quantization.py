"""Conversion keeps fixed-mode parameters despite conflicting caller defaults."""

from types import SimpleNamespace
from unittest.mock import patch

import mlx.nn as nn
import pytest

from mlx_vlm.convert import convert


@pytest.mark.parametrize("mode,group_size,bits", [("mxfp4", 32, 4), ("nvfp4", 16, 4), ("mxfp8", 32, 8)])
def test_convert_normalizes_fixed_mode_before_quantization(tmp_path, mode, group_size, bits):
    source = tmp_path / "source"
    source.mkdir()
    model = nn.Module()
    model.language_model = nn.Linear(64, 8)
    with (
        patch("mlx_vlm.convert.fetch_from_hub", return_value=(model, {}, SimpleNamespace())),
        patch("mlx_vlm.convert._preserve_existing_deepseek_v4_quantization") as preserve,
    ):
        convert(
            str(source),
            str(tmp_path / "converted"),
            quantize=True,
            q_mode=mode,
            q_group_size=128,
            q_bits=2,
        )
    assert preserve.call_args.args[2:] == (group_size, bits, mode)
    layer = model.language_model
    assert (layer.group_size, layer.bits, layer.mode) == (group_size, bits, mode)
