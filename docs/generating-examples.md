# Generating Pre-computed Examples

The app ships five pre-computed inference results (`src/constants/examples/ex0.js` – `ex4.js`) used as demo inputs and as the mobile fallback (where the full ONNX model isn't loaded). This guide explains how to regenerate or add new ones.

## Prerequisites

Python 3.8+ with PyTorch and Hugging Face Transformers:

```bash
pip install torch transformers
```

## What the script does

`src/utils/model/generate_examples.py` loads GPT-2 (downloaded automatically from Hugging Face on first run), runs a forward pass for each prompt, and writes one JS file per example containing:

- the prompt, tokens, and token IDs
- full vocab logits for the last token position
- attention matrices for all 12 layers × 12 heads (5 intermediate stages each)
- top-50 token probabilities (temperature 1.25, top-k 10)

## Adding or changing examples

1. Open `src/utils/model/generate_examples.py` and edit the `PROMPTS` list:

   ```python
   PROMPTS = [
       'A labrador is a type of',   # ex0
       'A',                          # ex1
       'Y G H Y G',                  # ex2
       'When Alice and Bob went out, Alice gave a drink to',  # ex3
       'When Alice and Bob went out, Bob gave a drink to',    # ex4
   ]
   ```

   Keep prompts short — the app enforces a 12-token display limit.

2. Run the script from the repo root:

   ```bash
   python src/utils/model/generate_examples.py
   ```

   This overwrites `src/constants/examples/ex0.js` – `ex{N-1}.js` and regenerates `index.js`. First run will download the GPT-2 weights (~500 MB) from Hugging Face.

3. If you change the **number** of examples (not just the prompts), update the app to match:

   - `src/constants/examples/index.js` — regenerated automatically by the script
   - `src/store/index.ts` — check if the example count is hardcoded
   - `src/components/InputForm.svelte` — the example selector UI

4. Rebuild and redeploy:

   ```bash
   npm run build
   npm run deploy
   ```

## Notes

- Sampling parameters (temperature, top-k) are hardcoded in the script. Changing them only affects the `probabilities` and `sampled` fields, not the attention matrices.
- The script always picks `rank 0` (argmax) as `sampled` — the live app does actual sampling at runtime.
- Generated files are large (~21,000 lines each for a 7-token prompt) due to the full attention matrix data. Don't edit them by hand.
