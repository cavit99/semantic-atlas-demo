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

When present, the renderer automatically points BFL's loader at these local
ComfyUI files instead of downloading the diffusion model or VAE:

```text
/Users/caviterginsoy/ComfyUI/models/diffusion_models/flux-2-klein-4b.safetensors
/Users/caviterginsoy/ComfyUI/models/vae/flux2-vae.safetensors
```

The Qwen text encoder still needs a Transformers-compatible model directory or
repo id because the tokenizer/config are required. A single `qwen_3_4b.safetensors`
file is not enough for the BFL loader by itself.

Experimental local MPS path:

```bash
RENDER_BACKEND=sdxl_mps DEVICE=mps uv run semantic-atlas-demo-renderer
```

The model backends are intentionally behind the same job API, so the event demo
can move from mock to MPS to CUDA without changing the frontend.
