# Experiment Log

No experiments have been run in this repository yet.

## 2026-06-30 20:56 +08:00 - Initial Environment Survey

Commit: `b12406a docs: initialize reconcile opsd project`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`

Commands summarized:

```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu --format=csv,noheader,nounits
/data/conda/bin/conda run -n mjy python -V
/data/conda/bin/conda run -n mjy python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.device_count())"
find -L /data/LLM -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | sort
```

GPU before:

```text
GPU 0: NVIDIA H100 PCIe, 81559 MiB total, about 75315 MiB used
GPU 1: NVIDIA H100 PCIe, 81559 MiB total, about 40173 MiB used
GPU 2: NVIDIA H100 PCIe, 81559 MiB total, about 61823 MiB used
GPU 3: NVIDIA H100 PCIe, 81559 MiB total, about 75447 MiB used
```

Result:

- Environment is usable for planning.
- Do not start training until a fresh GPU availability check is done.
- The target `mjy` environment has core training packages but lacks `bitsandbytes`, `deepspeed`, and `flash-attn`.

Next step:

- Prepare Pro literature/context packet and choose first smoke experiment after planning.

## 2026-06-30 21:33 +08:00 - Remote GitHub And Dependency Setup

Commit before action: `44a66b3 docs: scope first stage to small thinking models`
Branch: `main`
Machine: `node-128-46`
Project path: `/data03/liang/mjy/reconcile_opsd`
Conda env: `/data/conda/envs/mjy`

Actions:

- Configured clean GitHub remote URL: `https://github.com/Jiayi-Mao1027/OPD.git`.
- Found local server proxy at `127.0.0.1:7890/7891`.
- Pushed `main` to GitHub using the local proxy.
- Installed `bitsandbytes==0.49.2`.
- Installed `deepspeed==0.19.2`.
- Built and installed `flash-attn==2.8.3.post1`.
- Restored `packaging==25.0` after a transient upgrade conflicted with mlflow packages.

Environment notes:

```bash
export CUDA_HOME=/usr/local/cuda-12.2
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:${LD_LIBRARY_PATH:-}
```

Without those CUDA exports, deepspeed import can fail because the default shell does not expose `nvcc`.

Result:

- GitHub push succeeded.
- `bitsandbytes` import succeeded.
- `deepspeed` import succeeded with `CUDA_HOME=/usr/local/cuda-12.2`.
- `flash-attn` built successfully with `/usr/local/cuda-12.2/bin/nvcc`.
