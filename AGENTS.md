When you see this instruction, you're in a customized fork repo branch.

# Changes convention

Changes in this branch are drop-in diff commits staying on top of the upstream branch.

The long-term maintenance pattern is: over time, keep calling `git pull origin main` to rebase the branch commits on top of the latest upstream code.

Thus, the design of the changes target to minimize the potentials of future rebase conflicts.

# Rebase Maintenance

- Keep conflict resolutions and compatibility fixes in the existing custom commits; drop commits whose behavior upstream fully supersedes.
- Generation lives in `mlx_vlm/generate/`: bundle integration belongs in `ar.py` and `dispatch.py`; keep the public `GenerateKwargs` schema in sync.
- Use the native thread-local stream in `generate/common.py` and local helpers in `quant_utils.py`; do not restore `generate.py` or the removed `mlx_lm` dependency.
- Check upstream native loaders before retaining unsupported-quantizer rejections; BitNet is supported. Preserve checkpoint aliases, mixed/1-bit quantization, direct NVFP4 declarations, quantized vision loading, and tokenizer truncation.
- Run focused fork regression files (`test_fork_*.py`, `test_prompt_cache*.py`, `test_stream_generate_prompt_cache_bundle.py`) and affected upstream tests. Keep model downloads and full-model inference out of host validation.
