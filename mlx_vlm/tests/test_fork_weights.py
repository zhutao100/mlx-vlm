"""Weight-index metadata and index-only export contracts."""

import json

import mlx.core as mx
import mlx.nn as nn
import pytest

from mlx_vlm.utils import save_weights


@pytest.mark.parametrize("index_only", [False, True])
def test_save_weights_metadata_and_index_only(tmp_path, index_only):
    model = nn.Module()
    model.proj = nn.Linear(8, 4)
    save_weights(tmp_path, model, index_only=index_only)
    index = json.loads((tmp_path / "model.safetensors.index.json").read_text())
    assert index["metadata"]["total_parameters"] == 36
    assert index["metadata"]["total_size"] == 36 * 4
    assert index["weight_map"] == {
        "proj.bias": "model.safetensors",
        "proj.weight": "model.safetensors",
    }
    shard = tmp_path / "model.safetensors"
    assert shard.exists() is not index_only
    if not index_only:
        weights = mx.load(str(shard))
        assert weights["proj.weight"].shape == (4, 8)
