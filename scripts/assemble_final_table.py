"""Assemble and publish the final evaluation results table.

Loads task1, task2, and task3 scores from HuggingFace Hub, filters to
FaithBench (the only labeled dataset), normalises method names, computes
AUROC and AUPRC per (method, summarizer, dataset) combination, and pushes
the sorted final_table config to factshield-team/results.

Usage::

    python scripts/assemble_final_table.py
"""
import os
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from datasets import load_dataset, Dataset
from huggingface_hub import login
from pipelines.shared.evaluate import compute_auroc, compute_auprc
from sklearn.model_selection import train_test_split

load_dotenv()
login(token=os.environ['HF_TOKEN'])

HUB_RESULTS = 'factshield-team/results'

print("Loading task1 (selfcheck)...")
t1 = load_dataset(HUB_RESULTS, 'task1_scores')['train'].to_pandas()

print("Loading task2 (entailment)...")
t2 = load_dataset(HUB_RESULTS, 'task2_scores')['train'].to_pandas()

print("Loading task3 (token_prob)...")
t3 = load_dataset(HUB_RESULTS, 'task3_scores')['train'].to_pandas()

print("Loading FaithBench labels...")
labels = load_dataset('factshield-team/faithbench-labels')['train'].to_pandas()

t1_doc = (
    t1.groupby(['doc_id', 'summarizer', 'dataset', 'score_mode'])['score']
    .mean().reset_index()
)
t1_doc['method'] = 'selfcheck_' + t1_doc['score_mode']
t1_doc = t1_doc.drop(columns=['score_mode'])

t2_doc = (
    t2.groupby(['doc_id', 'summarizer', 'dataset', 'method'])['score']
    .mean().reset_index()
)

t3_doc = t3[['doc_id', 'summarizer', 'dataset', 'score', 'method']].copy()

all_results = pd.concat([t1_doc, t2_doc, t3_doc], ignore_index=True)

fb_results = all_results[all_results['dataset'] == 'faithbench']
merged = fb_results.merge(labels[['doc_id', 'label_binary_worst']], on='doc_id')

print(f"\nMerged rows: {len(merged)}")

rows = []
for (method, summ, ds), grp in merged.groupby(['method', 'summarizer', 'dataset']):
    if len(grp) < 10:
        continue

    grp = grp[np.isfinite(grp['score'])]
    if len(grp) < 10:
        print(f"  [skip] {method}/{summ}/{ds} — not enough finite scores")
        continue

    val, test = train_test_split(grp, test_size=0.5, random_state=42)

    try:
        auroc = compute_auroc(test['score'], test['label_binary_worst'])
        auprc = compute_auprc(test['score'], test['label_binary_worst'])
    except Exception as e:
        print(f"  [skip] {method}/{summ}/{ds} — {e}")
        continue

    rows.append({
        'method': method,
        'summarizer': summ,
        'dataset': ds,
        'AUROC': round(auroc, 4),
        'AUPRC': round(auprc, 4),
        'n_samples': len(test),
    })

final_table = pd.DataFrame(rows).sort_values(
    ['dataset', 'summarizer', 'AUROC'], ascending=[True, True, False]
)

print("\n=== Final Results Table ===")
print(final_table.to_string(index=False))

Dataset.from_pandas(final_table, preserve_index=False).push_to_hub(
    HUB_RESULTS,
    config_name='final_table',
    private=True
)
print("\n✓ final_table pushed to factshield-team/results")
