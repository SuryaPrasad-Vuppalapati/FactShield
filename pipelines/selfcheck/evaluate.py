"""Evaluation script for the SelfCheckGPT pipeline (Pipeline 1).

Loads task1_scores from HuggingFace Hub, filters to FaithBench (the only
labeled dataset), aggregates sentence-level scores to document-level,
and computes AUROC, AUPRC, F1, and ECE metrics.

Usage::

    python3 -m pipelines.selfcheck.evaluate
    python3 -m pipelines.selfcheck.evaluate --summarizer pegasus --mode nli
"""
import argparse
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login
from sklearn.model_selection import train_test_split
from pipelines.shared.evaluate import (
    compute_auroc, compute_auprc,
    compute_f1_at_best_threshold, compute_ece,
)

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def evaluate(summarizer=None, dataset_name=None, score_mode=None):
    """Evaluate SelfCheckGPT pipeline results against FaithBench hallucination labels.

    Args:
        summarizer: Optional summarizer filter ('bart', 't5', 'pegasus').
        dataset_name: Optional dataset filter ('cnndm', 'xsum', 'faithbench').
        score_mode: Optional score mode filter ('bert', 'nli', 'ngram').

    Returns:
        A pandas DataFrame with one row per (summarizer, dataset, score_mode) combination.
    """
    t1 = load_dataset('factshield-team/results', 'task1_scores')['train'].to_pandas()
    labels = load_dataset('factshield-team/faithbench-labels')['train'].to_pandas()

    if summarizer:
        t1 = t1[t1['summarizer'] == summarizer]
    if score_mode:
        t1 = t1[t1['score_mode'] == score_mode]

    fb_t1 = t1[t1['dataset'] == 'faithbench']

    doc_scores = (
        fb_t1.groupby(['doc_id', 'summarizer', 'dataset', 'score_mode'])['score']
        .mean()
        .reset_index()
    )

    merged = doc_scores.merge(labels[['doc_id', 'label_binary_worst']], on='doc_id')

    if merged.empty:
        print("  No labeled data found — only faithbench docs have labels")
        return pd.DataFrame()

    rows = []
    for (summ, ds, mode), grp in merged.groupby(['summarizer', 'dataset', 'score_mode']):
        if len(grp) < 10:
            print(f"  [skip] {summ}/{ds}/{mode} — not enough labeled samples ({len(grp)})")
            continue

        val, test = train_test_split(grp, test_size=0.5, random_state=42)

        # drop inf and nan scores
        val = val[np.isfinite(val['score'])]
        test = test[np.isfinite(test['score'])]

        if len(val) < 5 or len(test) < 5:
            print(f"  [skip] {summ}/{ds}/{mode} — not enough finite scores after cleaning")
            continue

        auroc = compute_auroc(test['score'], test['label_binary_worst'])
        auprc = compute_auprc(test['score'], test['label_binary_worst'])
        f1, thresh = compute_f1_at_best_threshold(
            val['score'].tolist(), val['label_binary_worst'].tolist(),
            test['score'].tolist(), test['label_binary_worst'].tolist(),
        )
        ece = compute_ece(test['score'].values, test['label_binary_worst'].values)

        rows.append({
            'summarizer': summ, 'dataset': ds, 'score_mode': mode,
            'AUROC': round(auroc, 4), 'AUPRC': round(auprc, 4),
            'F1': round(f1, 4), 'ECE': round(ece, 4),
            'threshold': round(thresh, 4), 'n_test': len(test),
        })
        print(f"  {summ}/{ds}/{mode}  AUROC={auroc:.4f}  AUPRC={auprc:.4f}"
              f"  F1={f1:.4f}  ECE={ece:.4f}  thresh={thresh:.4f}")

    return pd.DataFrame(rows)


def main():
    """CLI entry point for the SelfCheckGPT evaluation script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--summarizer', default=None)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--mode', default=None,
                        help="bert | nli | ngram")
    args = parser.parse_args()

    print("=== Pipeline 1 — SelfCheckGPT evaluation ===")
    df = evaluate(args.summarizer, args.dataset, args.mode)
    if not df.empty:
        print("\nSummary table:")
        print(df.sort_values('AUROC', ascending=False).to_string(index=False))


if __name__ == '__main__':
    main()
