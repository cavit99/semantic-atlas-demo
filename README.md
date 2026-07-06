# Semantic Atlas Demo

Semantic Atlas turns two text axes into a navigable 5x5 image field. Pick a
preset, press **Generate 5x5 atlas**, and the renderer samples each cell from
interpolated text-conditioning embeddings instead of separate hand-written
prompts.

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
RENDER_BACKEND=flux2_klein DEVICE=auto RELOAD=0 uv run semantic-atlas-demo-renderer
```

On CUDA, the renderer uses the Flux2 package default FP8 Qwen text encoder. On
MPS or CPU, it uses `Qwen/Qwen3-4B` instead because the FP8 encoder path is not
supported there. Set `FLUX2_TEXT_ENCODER_MODEL` only when you want to override
that with a Transformers model directory or repo id; a single `.safetensors`
file is not enough. Set `AE_MODEL_PATH` only when the file is BFL-compatible.

## Settings

- `RENDER_BACKEND=mock|auto|flux2_klein`
- `RENDERER_URL`: web-to-renderer service base URL; defaults to `http://127.0.0.1:8791`
- Batch size is selectable in the UI. The default is `25`.
- `DEVICE=auto|mps|cuda|cpu`
- `RELOAD=0|1`
- `FLUX2_TEXT_ENCODER_MODEL`: optional Qwen Transformers directory or repo id.

## Tests

```bash
npm run test:core
```

Model weights, generated images, and machine-specific paths are not committed.

## License

CC BY-NC 4.0. Commercial use is not permitted without prior written permission.
