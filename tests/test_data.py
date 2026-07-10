"""Integration tests verifying dataset splits and FaithBench labels on HuggingFace Hub.

Checks split size ratios, label integrity, and seed reproducibility.
"""
from datasets import load_dataset
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_split_sizes():
    """Assert train split is approximately 70% of the total CNN/DM dataset."""
    splits = load_dataset('factshield-team/cache', 'cnndm_splits')
    total = len(splits['train']) + len(splits['val']) + len(splits['test'])
    assert abs(len(splits['train']) / total - 0.70) < 0.02


def test_faithbench_labels():
    """Assert FaithBench labels dataset has 800 rows with valid binary labels."""
    labels = load_dataset('factshield-team/faithbench-labels')['train']
    df = labels.to_pandas()
    assert len(df) == 800
    assert df['label_binary_worst'].isin([0, 1]).all()
    assert df['label_binary_best'].isin([0, 1]).all()
    assert df['doc_id'].notna().all()


def test_seed_reproducibility():
    """Assert that identical seeds produce identical split ordering."""
    from pipelines.shared.splitter import make_splits
    cnndm = load_dataset('cnn_dailymail', '3.0.0')
    s1 = make_splits(cnndm, seed=42)
    s2 = make_splits(cnndm, seed=42)
    assert list(s1['train']['id']) == list(s2['train']['id'])
