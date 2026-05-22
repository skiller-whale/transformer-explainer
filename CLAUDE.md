# Transformer Explainer — CLAUDE.md

Interactive browser-based visualization of GPT-2, published at IEEE VIS 2024. Users type text and watch real-time inference flow through each transformer layer: embeddings → QKV projections → multi-head attention → MLP → output logits. Everything runs client-side; no backend.

## Tech Stack

- **SvelteKit 2 + Svelte 5** (static adapter — deployed to GitHub Pages)
- **TypeScript** (strict mode)
- **Vite 5** + Tailwind CSS 3 + Sass
- **ONNX Runtime Web** — runs GPT-2 inference in-browser
- **Xenova/transformers** — GPT-2 tokenizer (WASM)
- **D3.js + D3-Sankey** — flow diagrams, data visualizations
- **GSAP** — data flow animations

## Running the Project

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # static output → ./build/
npm run preview    # preview production build
npm run check      # TypeScript / Svelte type checking
npm run lint       # ESLint + Prettier
```

Deploy to GitHub Pages: `npm run deploy`

No automated test suite. Testing is manual/visual; the five pre-computed examples (`src/constants/examples/`) serve as regression anchors.

## Directory Layout

```
src/
  routes/           # Single route: +page.svelte (main viz), +layout.svelte (topbar, GTM)
  components/       # All Svelte components (~7,400 LOC)
    Embedding.svelte, QKV.svelte, Attention.svelte, HeadStack.svelte,
    AttentionMatrix.svelte, Mlp.svelte, LinearSoftmax.svelte  ← core transformer ops
    Sankey.svelte, ProbabilityBars.svelte, BlockTransition.svelte  ← visualizations
    InputForm.svelte, Temperature.svelte, Sampling.svelte  ← UI controls
    Popovers/       # Educational popovers (one per operation type)
    common/         # Primitives: VectorCanvas, Matrix, TokenVector, Slider, ...
    textbook/       # Integrated tutorial panel
  store/
    index.ts        # All Svelte stores (model data, UI state, interaction state)
  utils/
    data.ts         # Core inference: runModel(), getProbabilities(), sampling
    animation.ts    # GSAP timeline animations for data flow
    fetchChunks.js  # Downloads/caches 63 ONNX chunks in IndexedDB
    mock_data.ts    # Cached demo data for mobile / before model loads
    model/          # Python scripts for exporting GPT-2 to ONNX (offline use)
  constants/
    examples/       # Pre-computed inference results for 5 demo inputs (ex0–ex4)
    gradient.ts     # D3 color maps
  types/
    global.d.ts     # Cross-component types: Flow, ModelData, Probability, Sampling, etc.
static/
  model-v2/         # 63 ONNX model chunk files (~630 MB total)
```

## Data Flow

```
User input (InputForm)
  → store: inputText / selectedExampleIdx
    → +page.svelte listener
      → runModel() [utils/data.ts]
          tokenize (Xenova WASM)
          ONNX inference (fetched chunks, cached in IndexedDB)
          extract logits + all intermediate layer outputs
      → getProbabilities() [utils/data.ts]
          temperature scaling → top-k or top-p filtering → softmax
      → store updates (modelData, tokens, predictedToken)
        → reactive component re-renders (Embedding, QKV, Attention, Mlp, LinearSoftmax, ...)
          → GSAP flow animation (Sankey paths, gradients, vector movement)
```

Temperature/sampling changes only re-run `getProbabilities()` — not full inference.

## Key Design Decisions

**Model chunking**: The 630 MB GPT-2 ONNX model is split into 63 ~10 MB chunks. `fetchChunks.js` downloads and caches them in IndexedDB. First visit is slow; subsequent visits use cache.

**Mobile fallback**: On mobile, the model is not downloaded (too memory-intensive). The app serves pre-computed cached examples instead.

**Component-per-operation**: Each transformer operation has its own Svelte component. This makes the educational mapping explicit but creates a deep component tree. Components use `setContext('block-id', id)` to know which transformer block they belong to.

**SVG + Canvas hybrid**: Vectors and matrices render via Canvas (`VectorCanvas.svelte`); layout and flow use SVG. GSAP animates both.

**Static generation**: SvelteKit adapter-static prerenders to HTML+JS. No server. Base path is `/transformer-explainer/` for GitHub Pages.

**Input limit**: 12 tokens max (enforced for display clarity, not model capacity).

## Modifying the Model

If you need to swap or update the GPT-2 model:
1. `src/utils/model/export_to_onnx.py` — PyTorch → ONNX
2. `src/utils/model/chunk.py` — split ONNX into chunks
3. `src/utils/model/quantize.py` — optional quantization
4. Drop new chunks into `static/model-v2/` and update chunk count in `fetchChunks.js`
