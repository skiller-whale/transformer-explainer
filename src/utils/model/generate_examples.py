"""
Generate pre-computed example JS files for the transformer explainer.
Usage: python generate_examples.py
Outputs: src/constants/examples/ex0.js ... ex4.js + index.js
"""

import sys
import os
import math
import json
import torch
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(__file__))
from model import GPT

from transformers import GPT2Tokenizer

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '../../constants/examples')

PROMPTS = [
    'A labrador is a type of',
    'A',
    'Y G H Y G H Y G',
    'When Alice and Bob went out, Alice gave a drink to',
    'When Alice and Bob went out, Bob gave a drink to',
]

def format_float(x):
    if x == float('-inf'):
        return '-Infinity'
    if x == float('inf'):
        return 'Infinity'
    return float(f'{x:.6g}')

def tensor_to_nested_list(t):
    # t shape: (T, T) - squeeze batch dim first if needed
    if t.dim() == 3:
        t = t[0]
    return [[format_float(v.item()) for v in row] for row in t]

def flat_list(t):
    return [format_float(v.item()) for v in t.flatten()]

def js_value(v):
    """Recursively convert Python value to JS literal string."""
    if isinstance(v, list):
        if len(v) == 0:
            return '[]'
        # Check if it's a flat list of numbers or nested
        if isinstance(v[0], list):
            inner = ',\n\t\t\t\t'.join(
                '[' + ', '.join(str(x) for x in row) + ']'
                for row in v
            )
            return '[\n\t\t\t\t' + inner + '\n\t\t\t]'
        else:
            return '[' + ', '.join(str(x) for x in v) + ']'
    elif isinstance(v, str):
        return json.dumps(v)
    elif isinstance(v, bool):
        return 'true' if v else 'false'
    elif v is None:
        return 'null'
    else:
        return str(v)

def generate_example(model, tokenizer, prompt, idx):
    print(f'  Tokenizing: {repr(prompt)}')
    token_ids = tokenizer.encode(prompt)
    tokens = [tokenizer.decode([tid]) for tid in token_ids]
    print(f'  Tokens ({len(token_ids)}): {tokens}')

    input_tensor = torch.tensor([token_ids], dtype=torch.long)

    with torch.no_grad():
        outputs = model(input_tensor)

    # logits: last token position, full vocab
    logits = outputs['linear']['output'][0, -1].tolist()
    logits = [format_float(x) for x in logits]

    # attention outputs for all layers and heads
    n_layer = model.config.n_layer
    n_head = model.config.n_head

    attn_outputs = {}
    for i in range(n_layer):
        block_attn = model.transformer.h[i].attn
        for j in range(n_head):
            head_dict = block_attn.dict[f'head_{j}']
            for key in ['attn', 'attn_scaled', 'attn_masked', 'attn_softmax', 'attn_dropout']:
                t = head_dict[key]  # shape: (1, T, T)
                js_key = f'block_{i}_attn_head_{j}_{key}'
                data = tensor_to_nested_list(t)
                attn_outputs[js_key] = {'data': data}

    # Build top-50 probabilities (temperature=1, top-k=10)
    logit_tensor = torch.tensor(logits)
    top50 = torch.topk(logit_tensor, 50)
    top50_logits = top50.values.tolist()
    top50_ids = top50.indices.tolist()

    temperature = 1.25
    scaled = [l / temperature for l in top50_logits]
    k = 10

    filtered = [s if i < k else float('-inf') for i, s in enumerate(scaled)]
    max_f = max(x for x in filtered if x != float('-inf'))
    exp_f = [math.exp(x - max_f) if x != float('-inf') else 0.0 for x in filtered]
    sum_exp = sum(exp_f)
    probs = [e / sum_exp for e in exp_f]

    probabilities = []
    for rank, (tid, logit, sl, fl, ex, pr) in enumerate(
        zip(top50_ids, top50_logits, scaled, filtered, exp_f, probs)
    ):
        tok = tokenizer.decode([tid])
        probabilities.append({
            'tokenId': tid,
            'logit': format_float(logit),
            'scaledLogit': format_float(sl),
            'topKLogit': format_float(fl) if fl != float('-inf') else None,
            'rank': rank,
            'token': tok,
            'expLogit': format_float(ex),
            'probability': format_float(pr),
        })

    # sampled: pick rank 0 deterministically for the pre-computed file
    sampled = probabilities[0]

    # --- write JS file ---
    lines = []
    lines.append(f'export const ex{idx} = {{')
    lines.append(f'\tprompt: {json.dumps(prompt)},')
    lines.append(f'\ttokens: {json.dumps(tokens)},')
    lines.append(f'\ttokenIds: {json.dumps(token_ids)},')

    # logits
    lines.append(f'\tlogits: [')
    chunk = 4
    for c in range(0, len(logits), chunk):
        lines.append('\t\t' + ', '.join(str(x) for x in logits[c:c+chunk]) + ',')
    lines.append(f'\t],')

    # outputs
    lines.append(f'\toutputs: {{')
    for key, val in attn_outputs.items():
        lines.append(f'\t\t{key}: {{')
        lines.append(f'\t\t\tdata: [')
        for row in val['data']:
            lines.append('\t\t\t\t[' + ', '.join((x if isinstance(x, str) else str(x)) for x in row) + '],')
        lines.append(f'\t\t\t]')
        lines.append(f'\t\t}},')
    lines.append(f'\t}},')

    # probabilities
    lines.append(f'\tprobabilities: [')
    for p in probabilities:
        lines.append(f'\t\t{{')
        lines.append(f'\t\t\ttokenId: {p["tokenId"]},')
        lines.append(f'\t\t\tlogit: {p["logit"]},')
        lines.append(f'\t\t\tscaledLogit: {p["scaledLogit"]},')
        lines.append(f'\t\t\ttopKLogit: {"null" if p["topKLogit"] is None else p["topKLogit"]},')
        lines.append(f'\t\t\trank: {p["rank"]},')
        lines.append(f'\t\t\ttoken: {json.dumps(p["token"])},')
        lines.append(f'\t\t\texpLogit: {p["expLogit"]},')
        lines.append(f'\t\t\tprobability: {p["probability"]}')
        lines.append(f'\t\t}},')
    lines.append(f'\t],')

    # sampled
    lines.append(f'\tsampled: {{')
    lines.append(f'\t\ttokenId: {sampled["tokenId"]},')
    lines.append(f'\t\tlogit: {sampled["logit"]},')
    lines.append(f'\t\tscaledLogit: {sampled["scaledLogit"]},')
    lines.append(f'\t\ttopKLogit: {sampled["topKLogit"]},')
    lines.append(f'\t\trank: {sampled["rank"]},')
    lines.append(f'\t\ttoken: {json.dumps(sampled["token"])},')
    lines.append(f'\t\texpLogit: {sampled["expLogit"]},')
    lines.append(f'\t\tprobability: {sampled["probability"]}')
    lines.append(f'\t}}')
    lines.append('};')

    out_path = os.path.join(OUTPUT_DIR, f'ex{idx}.js')
    with open(out_path, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'  Written: {out_path}')

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('Loading GPT-2 tokenizer...')
    tokenizer = GPT2Tokenizer.from_pretrained('gpt2')

    print('Loading GPT-2 model...')
    model = GPT.from_pretrained('gpt2')
    model.eval()

    for idx, prompt in enumerate(PROMPTS):
        print(f'\nGenerating ex{idx}: {repr(prompt)}')
        generate_example(model, tokenizer, prompt, idx)

    # write index.js
    index_path = os.path.join(OUTPUT_DIR, 'index.js')
    with open(index_path, 'w') as f:
        for i in range(len(PROMPTS)):
            f.write(f"import {{ex{i}}} from './ex{i}';\n")
        f.write('\n')
        names = ', '.join(f'ex{i}' for i in range(len(PROMPTS)))
        f.write(f'export {{ {names} }};\n')
    print(f'\nWritten: {index_path}')
    print('\nDone.')

if __name__ == '__main__':
    main()
