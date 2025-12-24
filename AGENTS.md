# Project context
- Some core libraries in this project were implemented referring to the `mlx-lm` project, which
  - is accessible locally at `~/workspace/custom-builds/mlx-lm`
  - is hosted at `https://github.com/ml-explore/mlx`
  - refer to it when analyzing the core library implementations in this project.

# Useful resources
- For analyzing `.safetensors` file structure, you can use the python script `~/bin/stls.py`
  - use `--format toon` to ouput in the LLM friendly format "TOON"
  - if the script is not present, it's downloadable via `curl https://gist.githubusercontent.com/zhutao100/cc481d2cd248aa8769e1abb3887facc8/raw/89d644c490bcf5386cb81ebcc36c92471f578c60/stls.py > ~/bin/stls.py`
- To analyze/test the project with a real model, check whether there are supported multimodals available at `~/.cache/huggingface/hub/`, e.g. model dirs with prefix `models--mlx-community--Qwen3-VL`
