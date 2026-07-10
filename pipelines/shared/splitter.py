"""Dataset splitting script (Phase 1 - Data ingestion).

Creates reproducible 70/15/15 train/val/test splits with seed=42 for CNN/DailyMail,
XSum, and FaithBench datasets, saves them locally, and pushes all split configs
to the factshield-team/cache HuggingFace Hub.
"""
import os
import random
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from datasets import DatasetDict, Dataset, load_from_disk
from huggingface_hub import login

load_dotenv()
login(token=os.environ['HF_TOKEN'])

SEED = 42
random.seed(SEED)
np.random.seed(SEED)


def make_splits(dataset, split_key='test', n_sample=2000, seed=SEED):
    """Create reproducible train/val/test splits from a single split of a dataset.

    Samples n_sample documents from the chosen split, then divides them into
    70% train, 15% val, 15% test.

    Args:
        dataset: A HuggingFace DatasetDict.
        split_key: Which split key of the dataset to sample from (e.g., 'test').
        n_sample: Maximum number of documents to sample.
        seed: Random seed for reproducibility.

    Returns:
        A DatasetDict with 'train', 'val', and 'test' keys.
    """
    base = dataset[split_key]
    n_sample = min(n_sample, len(base))
    sampled = base.shuffle(seed=seed).select(range(n_sample))
    first_split = sampled.train_test_split(test_size=0.30, seed=seed)
    val_test = first_split['test'].train_test_split(test_size=0.50, seed=seed)
    return DatasetDict({
        'train': first_split['train'],
        'val': val_test['train'],
        'test': val_test['test'],
    })


def make_splits_from_dataset(dataset, seed=SEED):
    """Create reproducible train/val/test splits from a full Dataset (no pre-split).

    Args:
        dataset: A HuggingFace Dataset (not DatasetDict).
        seed: Random seed for reproducibility.

    Returns:
        A DatasetDict with 'train', 'val', and 'test' keys.
    """
    first_split = dataset.train_test_split(test_size=0.30, seed=seed)
    val_test = first_split['test'].train_test_split(test_size=0.50, seed=seed)
    return DatasetDict({
        'train': first_split['train'],
        'val': val_test['train'],
        'test': val_test['test'],
    })


cnndm = load_from_disk('data/raw/cnndm')
xsum = load_from_disk('data/raw/xsum')
faithbench_df = pd.read_csv('data/raw/faithbench.csv')

cnndm_splits = make_splits(cnndm, split_key='test', n_sample=2000)
xsum_splits = make_splits(xsum, split_key='test', n_sample=2000)

faithbench_ds = Dataset.from_pandas(faithbench_df, preserve_index=False)
fb_splits = make_splits_from_dataset(faithbench_ds)

print(f"CNN/DM splits:     {cnndm_splits}")
print(f"XSUM splits:       {xsum_splits}")
print(f"FaithBench splits: {fb_splits}")

os.makedirs('data/splits', exist_ok=True)
cnndm_splits.save_to_disk('data/splits/cnndm')
xsum_splits.save_to_disk('data/splits/xsum')
fb_splits.save_to_disk('data/splits/faithbench')
print("Splits saved to data/splits/")

cnndm_splits.push_to_hub('factshield-team/cache', config_name='cnndm_splits', private=True)
xsum_splits.push_to_hub('factshield-team/cache', config_name='xsum_splits', private=True)
fb_splits.push_to_hub('factshield-team/cache', config_name='faithbench_splits', private=True)
print("All splits pushed to factshield-team/cache")
