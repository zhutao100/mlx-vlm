import importlib
import threading

import mlx.core as mx
import pytest


def test_generation_stream_is_thread_local():
    if not mx.metal.is_available():
        pytest.skip("Metal kernels are unavailable on this host")

    mod = importlib.import_module("mlx_vlm.generate")

    main_stream = mod._get_generation_stream()
    mx.synchronize(main_stream)

    streams = []
    errors = []

    def worker():
        try:
            stream = mod._get_generation_stream()
            mx.synchronize(stream)
            streams.append(stream)
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert not errors
    assert streams
    assert streams[0] is not main_stream
