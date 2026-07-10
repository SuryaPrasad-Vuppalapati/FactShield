"""Entailment scoring pipeline (Pipeline 2).

Loads cached beam-search summaries from HuggingFace Hub, then runs each
(source, sentence) pair through one or more entailment/NLI scorers in a
single batched forward pass per method."""

import time
from datasets import load_dataset
from pipelines.entailment.scorer import (
    score_summac_zs_batch,
    score_summac_conv_batch,
    score_minicheck_batch,
    score_alignscore_batch,
)

# Map method name → batch scorer function
BATCH_SCORERS = {
    'summac_zs': score_summac_zs_batch,
    'summac_conv': score_summac_conv_batch,
    'minicheck': score_minicheck_batch,
    'alignscore': score_alignscore_batch,
}


def run_pipeline(model_name='bart', dataset_name='cnndm', methods=None):
    """Score all summaries in the cache using the specified entailment methods.

    M4 optimisation: accumulates ALL (source, sentence) pairs across the
    entire dataset, then calls each model scorer exactly once per method
    instead of once per sentence.

    Args:
        model_name: Summarizer name ('bart', 't5', or 'pegasus').
        dataset_name: Dataset name ('cnndm', 'xsum', or 'faithbench').
        methods: List of method keys to use. Defaults to ['summac_zs', 'summac_conv'].

    Returns:
        A tuple of (results, elapsed) where results is a list of dicts with
        keys 'doc_id', 'sent_id', 'summarizer', 'dataset', 'method', 'score',
        and elapsed is the total runtime in seconds.
    """
    if methods is None:
        methods = ['summac_zs', 'summac_conv']

    cache = load_dataset(
        'factshield-team/cache',
        f'{model_name}_{dataset_name}_summaries'
    )['train']
    df = cache.to_pandas()

    # ── Step 1: flatten every doc → sentences, keep metadata ─────────────────
    all_sources: list[str] = []
    all_sentences: list[str] = []
    all_meta: list[dict] = []

    for _, row in df.iterrows():
        sentences = [s.strip() for s in row['summary'].split('.') if s.strip()]
        source = row['source_text']
        for i, sent in enumerate(sentences):
            all_sources.append(source)
            all_sentences.append(sent)
            all_meta.append({
                'doc_id': row['doc_id'],
                'sent_id': i,
                'summarizer': model_name,
                'dataset': dataset_name,
            })

    print(f"  {len(all_sentences)} (source, sentence) pairs across {len(df)} docs")

    # ── Step 2: one batch call per method ────────────────────────────────────
    results = []
    start = time.time()

    for method in methods:
        if method not in BATCH_SCORERS:
            raise ValueError(f"Unknown method: {method}. "
                             f"Choose from {list(BATCH_SCORERS)}")

        print(f"  scoring with {method}...")
        method_start = time.time()
        scores = BATCH_SCORERS[method](all_sources, all_sentences)
        print(f"  ✓ {method} done in {time.time() - method_start:.1f}s")

        for meta, score in zip(all_meta, scores):
            results.append({**meta, 'method': method, 'score': score})

    elapsed = time.time() - start
    print(f"✓ {len(results)} scores in {elapsed:.1f}s")
    return results, elapsed
