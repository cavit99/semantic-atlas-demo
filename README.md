# Semantic Atlas Demo

An interactive demo of two-axis semantic control for image generation.

Pick one of five scene presets, press **Generate grid**, and watch a 3x3 field
render from two visual axes. The repo does not ship pre-rendered grids; each
cell is generated at request time by interpolating text-conditioning embeddings
before the image model runs.

## 10-Second Demo Script

"Each preset has a neutral scene and two axes. We encode the neutral prompt and
the axis endpoints with Qwen, blend those vectors for each x/y coordinate, then
Flux2 Klein renders the nine points. The result is a live map of meaning, not
nine separately written prompts."

## What It Shows

- Five curated scene presets chosen for visible, compositional axis movement.
- Manual generation: selecting a preset opens the workspace; inference starts
  only when the operator presses **Generate grid**.
- A 3x3 field where x runs left to right and y runs bottom to top.
- Progressive rendering over server-sent events, with configurable grid batch
  size for speed versus visible progress.
- A clean backend boundary: the frontend asks for `ideaId + x/y + worldSeed`;
  the renderer owns all model, embedding, batching, and image details.

## Project Shape

```text
semantic-atlas-demo/
  data/ideas.json     five shared demo presets
  web/                Next.js + React frontend
  renderer/           FastAPI renderer service
```

The request path is intentionally simple:

```text
browser -> Next.js API proxy -> FastAPI /grid job -> SSE progress/cell events -> browser
```

## Run With Mock Images

Use this path for UI work and fast presentation checks.

Terminal 1:

```bash
cd renderer
uv sync
RENDER_BACKEND=mock uv run semantic-atlas-demo-renderer
```

Terminal 2:

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Run With Local Flux2 Klein

Use this path for the real demo on Apple Silicon or CUDA. It uses the same UI and
job API as mock mode.

```bash
cd renderer
uv sync --group local-models
export KLEIN_4B_MODEL_PATH=/absolute/path/to/flux-2-klein-4b.safetensors
export FLUX2_TEXT_ENCODER_MODEL=/absolute/path/to/qwen3-transformers-model
ATLAS_GRID_BATCH_SIZE=3 RENDER_BACKEND=flux2_klein DEVICE=auto RELOAD=0 uv run semantic-atlas-demo-renderer
```

For Qwen, `FLUX2_TEXT_ENCODER_MODEL` may point to a Transformers model directory
or repo id. A single `qwen_3_4b.safetensors` file is not enough by itself because
the tokenizer and config files are also required.

Only set `AE_MODEL_PATH` when the file has BFL-compatible key names. Otherwise
leave it unset and let the BFL loader use its normal VAE source.

For a public-safe environment template, see `.env.example`. The application does
not commit model weights or machine-specific paths.

## Grid Batching

`ATLAS_GRID_BATCH_SIZE` controls how many cells the renderer samples together.

- `3` is the recommended demo setting: one visible batch at a time.
- `9` can be faster, but all cells usually appear together.
- `1` gives the clearest progress feedback and the slowest total render.

If a Flux batch runs out of memory, the renderer clears the device cache and
falls back to smaller per-cell rendering.

## Backend Modes

```bash
RENDER_BACKEND=mock         # procedural live images for frontend development
RENDER_BACKEND=auto         # tries a local cached model path, otherwise mock
RENDER_BACKEND=sdxl_mps     # experimental Apple Silicon Diffusers path
RENDER_BACKEND=flux2_klein  # Flux2 Klein 4B with custom embedding interpolation
```

The important production-facing idea is that model backends stay behind one job
API, so the demo can move from mock to local MPS to rented CUDA without
changing the frontend.

## Key Files

- `data/ideas.json`: the five curated presets, scenes, axis labels, and endpoint
  prompts.
- `web/components/IdeaPicker.tsx`: preset chooser.
- `web/components/LiveGrid.tsx`: manual generation, progress display, and 3x3
  grid.
- `renderer/src/semantic_atlas_demo_renderer/interpolation.py`: axis blending in
  conditioning space.
- `renderer/src/semantic_atlas_demo_renderer/renderers/flux2_klein.py`: local
  Flux2 Klein/Qwen adapter and batch rendering.
