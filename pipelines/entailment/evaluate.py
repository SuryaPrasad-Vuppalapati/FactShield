"""
pipelines/entailment/evaluate.py
Loads task2_scores from Hub, merges with FaithBench labels,
and prints AUROC / AUPRC / F1 / ECE for every (summarizer, dataset, method) combo.

Usage:
    python3 -m pipelines.entailment.evaluate
    python3 -m pipelines.entailment.evaluate --summarizer bart --dataset cnndm --method minicheck
"""
import argparse
import os
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


def evaluate(summarizer=None, dataset_name=None, method=None):
    """Evaluate entailment pipeline results against FaithBench hallucination labels.

    Loads task2_scores from HuggingFace Hub, filters by the provided criteria,
    aggregates sentence-level scores to document-level, then computes AUROC,
    AUPRC, F1 (threshold tuned on a validation split), and ECE.

    Args:
        summarizer: Optional summarizer filter ('bart', 't5', 'pegasus').
        dataset_name: Optional dataset filter ('cnndm', 'xsum', 'faithbench').
        method: Optional method filter ('summac_zs', 'summac_conv', 'minicheck', 'alignscore').

    Returns:
        A pandas DataFrame with one row per (summarizer, dataset, method) combination.
    """
    t2 = load_dataset('factshield-team/results', 'task2_scores')['train'].to_pandas()
    labels = load_dataset('factshield-team/faithbench-labels')['train'].to_pandas()

    # apply filters first
    if summarizer:
        t2 = t2[t2['summarizer'] == summarizer]
    if method:
        t2 = t2[t2['method'] == method]

    # only faithbench has labels
    fb_t2 = t2[t2['dataset'] == 'faithbench']

    # aggregate sentence-level → doc-level (mean score per doc)
    doc_scores = (
        fb_t2.groupby(['doc_id', 'summarizer', 'dataset', 'method'])['score']
        .mean()
        .reset_index()
    )

    merged = doc_scores.merge(labels[['doc_id', 'label_binary_worst']], on='doc_id')

    if merged.empty:
        print("  No labeled data found — only faithbench docs have labels")
        return pd.DataFrame()

    rows = []
    for (summ, ds, meth), grp in merged.groupby(['summarizer', 'dataset', 'method']):
        if len(grp) < 10:
            print(f"  [skip] {summ}/{ds}/{meth} — not enough labeled samples ({len(grp)})")
            continue

        val, test = train_test_split(grp, test_size=0.5, random_state=42)

        auroc = compute_auroc(test['score'], test['label_binary_worst'])
        auprc = compute_auprc(test['score'], test['label_binary_worst'])
        f1, thresh = compute_f1_at_best_threshold(
            val['score'].tolist(), val['label_binary_worst'].tolist(),
            test['score'].tolist(), test['label_binary_worst'].tolist(),
        )
        ece = compute_ece(test['score'].values, test['label_binary_worst'].values)

        rows.append({
            'summarizer': summ, 'dataset': ds, 'method': meth,
            'AUROC': round(auroc, 4), 'AUPRC': round(auprc, 4),
            'F1': round(f1, 4), 'ECE': round(ece, 4),
            'threshold': round(thresh, 4), 'n_test': len(test),
        })
        print(f"  {summ}/{ds}/{meth}  AUROC={auroc:.4f}  AUPRC={auprc:.4f}"
              f"  F1={f1:.4f}  ECE={ece:.4f}  thresh={thresh:.4f}")

    return pd.DataFrame(rows)


def main():
    """CLI entry point for the entailment evaluation script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--summarizer', default=None)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--method', default=None,
                        help="summac_zs | summac_conv | minicheck | alignscore")
    args = parser.parse_args()

    print("=== Pipeline 2 — Entailment evaluation ===")
    df = evaluate(args.summarizer, args.dataset, args.method)
    if not df.empty:
        print("\nSummary table:")
        print(df.sort_values('AUROC', ascending=False).to_string(index=False))


if __name__ == '__main__':
    main()
