# Semantic Atlas Demo

Semantic Atlas turns two text axes into a 3x3 image grid. Pick a preset, press
**Generate 3x3 grid**, and the renderer samples each cell from interpolated
text-conditioning embeddings instead of nine separate prompts.

## Structure

- `web`: Next.js UI.
- `renderer`: FastAPI renderer and server-sent event stream.
- `data/ideas.json`: the five shared presets.

## Run

Start the mock renderer:

```bash
cd renderer
uv sync
RENDER_BACKEND=mock uv run semantic-atlas-demo-renderer
```

Start the web app:

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Flux2 Klein

Real generation is optional and requires local model files. Set the paths in
your shell; `.env.example` lists the variables.

```bash
cd renderer
uv sync --group local-models
export KLEIN_4B_MODEL_PATH=/absolute/path/to/flux-2-klein-4b.safetensors
export FLUX2_TEXT_ENCODER_MODEL=/absolute/path/to/qwen3-transformers-model
ATLAS_GRID_BATCH_SIZE=3 RENDER_BACKEND=flux2_klein DEVICE=auto RELOAD=0 uv run semantic-atlas-demo-renderer
```

`FLUX2_TEXT_ENCODER_MODEL` must be a Transformers model directory or repo id, not
just a `.safetensors` file. Set `AE_MODEL_PATH` only when the VAE file is
BFL-compatible.

## Settings

- `RENDER_BACKEND=mock|auto|sdxl_mps|flux2_klein`
- `ATLAS_GRID_BATCH_SIZE=3`: visible progress; `9` can be faster but updates at once.
- `DEVICE=auto|mps|cuda|cpu`

## Tests

```bash
npm run test:core
```

Model weights, generated images, and machine-specific paths are not committed.
