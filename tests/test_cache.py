"""Integration tests verifying all 27 generation cache configs on HuggingFace Hub.

Parametrized over all model × dataset combinations, checking that summaries,
k-sample, and token-score cache configs exist and have the correct structure.
"""
import os
import pytest
import numpy as np
from dotenv import load_dotenv
from datasets import load_dataset
from huggingface_hub import login

load_dotenv()
if not os.environ.get('HF_TOKEN'):
    pytest.skip("HF_TOKEN not set", allow_module_level=True)
login(token=os.environ['HF_TOKEN'])

MODELS = ['bart', 't5', 'pegasus']
DATASETS = ['cnndm', 'xsum', 'faithbench']
EXPECTED_TRAIN = {'cnndm': 1400, 'xsum': 1400, 'faithbench': 560}


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_summaries_exist(model, dataset):
    """Assert that the summary cache for this model/dataset pair is non-empty."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_summaries')['train']
    assert len(ds) == EXPECTED_TRAIN[dataset]


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_summaries_columns(model, dataset):
    """Assert that the summary cache has doc_id, source_text, and summary columns."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_summaries')['train']
    assert 'doc_id' in ds.column_names
    assert 'source_text' in ds.column_names
    assert 'summary' in ds.column_names


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_summaries_no_empty(model, dataset):
    """Assert that no summary in the cache is empty or whitespace-only."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_summaries')['train']
    df = ds.to_pandas()
    assert df['summary'].notna().all()
    assert (df['summary'].str.strip() != '').all()


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_k_samples_exist(model, dataset):
    """Assert that the k-samples cache for this model/dataset pair is non-empty."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_k_samples')['train']
    assert len(ds) == EXPECTED_TRAIN[dataset]


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_k_samples_columns(model, dataset):
    """Assert that the k-samples cache has doc_id and at least 5 summary columns."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_k_samples')['train']
    assert 'doc_id' in ds.column_names
    assert 'summary_k1' in ds.column_names
    k_cols = [c for c in ds.column_names if c.startswith('summary_k')]
    assert len(k_cols) >= 5, f"Expected at least 5 samples, got {len(k_cols)}"


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_token_scores_exist(model, dataset):
    """Assert that the token-scores cache for this model/dataset pair is non-empty."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_token_scores')['train']
    assert len(ds) == EXPECTED_TRAIN[dataset]


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_token_scores_columns(model, dataset):
    """Assert that the token-scores cache has doc_id, token_logprobs, and seq_len."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_token_scores')['train']
    assert 'doc_id' in ds.column_names
    assert 'token_logprobs' in ds.column_names
    assert 'seq_len' in ds.column_names


@pytest.mark.parametrize("model,dataset", [
    (m, d) for m in MODELS for d in DATASETS
])
def test_token_scores_logprobs_valid(model, dataset):
    """Assert log-probs match seq_len and are all <= 0 (valid log-probabilities)."""
    ds = load_dataset('factshield-team/cache', f'{model}_{dataset}_token_scores')['train']
    df = ds.to_pandas()
    row = df.iloc[0]
    lp = np.frombuffer(row['token_logprobs'], dtype=np.float32)
    assert len(lp) == row['seq_len']
    assert np.all(lp <= 0), "log probs should be <= 0"
