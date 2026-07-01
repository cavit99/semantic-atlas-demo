# Semantic Atlas Demo

A live-only hack-event demo of Semantic Atlas.

The demo presents 5 curated atlas ideas. Selecting one starts live inference for a
3x3 semantic field: x runs left-to-right, y runs bottom-to-top. No grids or
images are pre-rendered into the repo.

## Shape

- `web/`: Next.js + React frontend.
- `renderer/`: FastAPI renderer service with progressive grid jobs.
- `data/ideas.json`: the 5 curated atlas ideas shared by both services.

The frontend never talks in prompt-embedding terms. Its API is:

```text
ideaId + x/y + worldSeed -> image
```

The renderer owns model-specific details and can run different backends:

- `mock`: procedural live images for frontend development.
- `auto`: uses a local model backend if dependencies/cache are available; otherwise mock.
- `sdxl_mps`: optional local Apple Silicon Diffusers path.
- `flux2_klein`: target Flux2 Klein 4B adapter for CUDA production work.

## Run

Start the renderer:

```bash
cd /Users/caviterginsoy/Coding/semantic-atlas-demo/renderer
uv sync
uv run semantic-atlas-demo-renderer
```

Start the web app:

```bash
cd /Users/caviterginsoy/Coding/semantic-atlas-demo/web
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

## Backend Modes

Default:

```bash
RENDER_BACKEND=auto uv run semantic-atlas-demo-renderer
```

Force mock:

```bash
RENDER_BACKEND=mock uv run semantic-atlas-demo-renderer
```

Target Flux2 Klein 4B:

```bash
uv sync --group local-models
RENDER_BACKEND=flux2_klein DEVICE=auto uv run semantic-atlas-demo-renderer
```

When present, the renderer automatically points BFL's loader at the local
ComfyUI Flux transformer instead of downloading it:

```text
/Users/caviterginsoy/ComfyUI/models/diffusion_models/flux-2-klein-4b.safetensors
```

The local `qwen_3_4b.safetensors` file is wrapped with Qwen3 tokenizer/config
files under `~/.cache/semantic-atlas-demo/qwen3-4b`. The ComfyUI
`flux2-vae.safetensors` file uses Diffusers key names, so `AE_MODEL_PATH` should
only be set to a BFL-compatible `ae.safetensors`; otherwise the BFL loader will
use its normal `ae.safetensors` source.

Experimental local MPS path:

```bash
RENDER_BACKEND=sdxl_mps DEVICE=mps uv run semantic-atlas-demo-renderer
```

The model backends are intentionally behind the same job API, so the event demo
can move from mock to MPS to CUDA without changing the frontend.
