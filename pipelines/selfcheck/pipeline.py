"""SelfCheckGPT consistency scoring pipeline (Pipeline 1).

Loads K-sample summaries from HuggingFace Hub and scores each sentence in the
primary summary for consistency across the K samples using BERTScore, NLI, or
Ngram scorers."""

import os
import time
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def run_pipeline(model_name='bart', dataset_name='cnndm', K=5, score_mode='all'):
    """Run the SelfCheckGPT consistency scoring pipeline.

    Args:
        model_name: Summarizer name ('bart', 't5', or 'pegasus').
        dataset_name: Dataset name ('cnndm', 'xsum', or 'faithbench').
        K: Number of stochastic samples used per document.
        score_mode: Scoring mode — 'bert', 'nli', 'ngram', or 'all'.

    Returns:
        A tuple of (results, elapsed) where results is a list of sentence-level
        score dicts and elapsed is total runtime in seconds.
    """
    from pipelines.selfcheck.scorer import (
        score_bert_batch, score_nli_batch, score_ngram_batch
    )

    k_cache = load_dataset(
        'factshield-team/cache',
        f'{model_name}_{dataset_name}_k_samples'
    )['train']
    k_df = k_cache.to_pandas()

    modes = ['bert', 'nli', 'ngram'] if score_mode == 'all' else [score_mode]
    results = []
    start = time.time()

    for idx, (_, row) in enumerate(k_df.iterrows()):
        samples = [row[f'summary_k{k}'] for k in range(1, K + 1)]

        samples = [s for s in samples if s and isinstance(s, str) and s.strip()]

        if len(samples) < 2:
            print(f"  [skip] doc {row['doc_id']} — not enough valid samples ({len(samples)})")
            continue

        primary = samples[0]
        others = samples[1:]
        sentences = [s.strip() for s in primary.split('.') if s.strip()]

        if not sentences:
            print(f"  [skip] doc {row['doc_id']} — no sentences in primary summary")
            continue

        mode_scores: dict[str, list[float]] = {}
        for mode in modes:
            if mode == 'bert':
                mode_scores[mode] = score_bert_batch(sentences, others)
            elif mode == 'nli':
                mode_scores[mode] = score_nli_batch(sentences, others)
            else:
                mode_scores[mode] = score_ngram_batch(sentences, others)

        for i, sent in enumerate(sentences):
            for mode in modes:
                results.append({
                    'doc_id': row['doc_id'],
                    'sent_id': i,
                    'summarizer': model_name,
                    'dataset': dataset_name,
                    'K': K,
                    'score_mode': mode,
                    'score': mode_scores[mode][i],
                })

        if (idx + 1) % 100 == 0:
            elapsed_so_far = time.time() - start
            print(f"  [{idx + 1}/{len(k_df)}] docs processed — {elapsed_so_far:.1f}s elapsed")

    elapsed = time.time() - start
    print(f"{len(results)} sentence scores in {elapsed:.1f}s")
    return results, elapsed
