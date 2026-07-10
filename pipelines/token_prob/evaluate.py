"""Evaluation script for the token probability pipeline (Pipeline 3).

Loads task3_scores from HuggingFace Hub, filters to FaithBench docs with
hallucination labels, and computes AUROC, AUPRC, F1, and ECE metrics.
Optionally prints logistic regression feature importance.

Usage::

    python3 -m pipelines.token_prob.evaluate
    python3 -m pipelines.token_prob.evaluate --summarizer bart --dataset faithbench
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
from pipelines.token_prob.classifier import load_model_from_hub, FEATURE_COLS

load_dotenv()
login(token=os.environ['HF_TOKEN'])


def evaluate(summarizer=None, dataset_name=None):
    """Evaluate token probability pipeline results against FaithBench labels.

    Args:
        summarizer: Optional summarizer filter ('bart', 't5', 'pegasus').
        dataset_name: Optional dataset filter ('cnndm', 'xsum', 'faithbench').

    Returns:
        A pandas DataFrame with one row per (summarizer, dataset) combination.
    """
    t3 = load_dataset('factshield-team/results', 'task3_scores')['train'].to_pandas()

    if summarizer:
        t3 = t3[t3['summarizer'] == summarizer]
    if dataset_name:
        t3 = t3[t3['dataset'] == dataset_name]

    # label_binary_worst already in t3 from run.py — just filter faithbench
    merged = t3[t3['dataset'] == 'faithbench'].dropna(subset=['label_binary_worst'])

    if merged.empty:
        print("  No labeled data found")
        return pd.DataFrame()

    rows = []
    for (summ, ds), grp in merged.groupby(['summarizer', 'dataset']):
        if len(grp) < 10:
            print(f"  [skip] {summ}/{ds} — not enough labeled samples ({len(grp)})")
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
            'summarizer': summ, 'dataset': ds,
            'AUROC': round(auroc, 4), 'AUPRC': round(auprc, 4),
            'F1': round(f1, 4), 'ECE': round(ece, 4),
            'threshold': round(thresh, 4), 'n_test': len(test),
        })
        print(f"  {summ}/{ds}  AUROC={auroc:.4f}  AUPRC={auprc:.4f}"
              f"  F1={f1:.4f}  ECE={ece:.4f}  thresh={thresh:.4f}")

    return pd.DataFrame(rows)


def show_feature_importance():
    """Print logistic regression coefficients from the saved classifier."""
    try:
        clf = load_model_from_hub()
        base = clf.calibrated_classifiers_[0].estimator
        coefs = pd.Series(base.coef_[0], index=FEATURE_COLS)
        print("\nFeature coefficients (higher = more predictive of hallucination):")
        print(coefs.sort_values(ascending=False).to_string())
    except Exception as e:
        print(f"  [skip] could not load classifier: {e}")


def main():
    """CLI entry point for the token probability evaluation script."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--summarizer', default=None)
    parser.add_argument('--dataset', default=None)
    parser.add_argument('--no-feature-importance', action='store_true')
    args = parser.parse_args()

    print("=== Pipeline 3 — Token probability evaluation ===")
    df = evaluate(args.summarizer, args.dataset)
    if not df.empty:
        print("\nSummary table:")
        print(df.sort_values('AUROC', ascending=False).to_string(index=False))

    if not args.no_feature_importance:
        show_feature_importance()


if __name__ == '__main__':
    main()
