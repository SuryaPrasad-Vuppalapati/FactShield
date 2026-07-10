"""Token log-probability feature extraction utilities.

Converts raw token log-probabilities (stored as float32 bytes) into five
uncertainty features used by the logistic regression hallucination classifier:
perplexity, mean entropy, max entropy, tail mean NLL, and sequence length."""

import math
import numpy as np
import pandas as pd


def compute_perplexity(log_probs: np.ndarray) -> float:
    """Compute the perplexity of a token sequence from log probabilities.

    Args:
        log_probs: Array of token log probabilities (negative values).

    Returns:
        Perplexity as a positive float.
    """
    return math.exp(-float(np.mean(log_probs)))


def compute_entropy(log_probs: np.ndarray) -> tuple[float, float]:
    """Compute mean and max token-level entropy from log probabilities.

    Args:
        log_probs: Array of token log probabilities.

    Returns:
        A tuple of (mean_entropy, max_entropy) as floats.
    """
    probs = np.exp(log_probs)
    entropy_per_token = -(probs * log_probs)
    return float(np.mean(entropy_per_token)), float(np.max(entropy_per_token))


def extract_features(row) -> dict:
    """Extract the five uncertainty features from a single DataFrame row.

    Args:
        row: A dict-like row with 'token_logprobs' (bytes) and 'seq_len' (int).

    Returns:
        A dict with keys: perplexity, mean_entropy, max_entropy,
        tail_mean_nll, sent_length.
    """
    log_probs = np.frombuffer(row['token_logprobs'], dtype=np.float32)
    perplexity = compute_perplexity(log_probs)
    mean_ent, max_ent = compute_entropy(log_probs)
    tail_mean_nll = float(-np.mean(log_probs[-5:]))
    return {
        'perplexity': perplexity,
        'mean_entropy': mean_ent,
        'max_entropy': max_ent,
        'tail_mean_nll': tail_mean_nll,
        'sent_length': int(row['seq_len']),
    }


def extract_features_vectorized(df) -> "pd.DataFrame":
    """Extract five uncertainty features for all rows in a DataFrame.

    Vectorised implementation for efficiency; processes all rows in one pass
    without a Python-level loop over the feature functions.

    Args:
        df: A DataFrame with columns 'doc_id', 'token_logprobs', and 'seq_len'.

    Returns:
        A DataFrame with columns 'doc_id', 'seq_len', 'perplexity',
        'mean_entropy', 'max_entropy', 'tail_mean_nll', and 'sent_length'.
    """

    log_probs_list = [
        np.frombuffer(b, dtype=np.float32)
        for b in df['token_logprobs']
    ]

    perplexity = np.array([math.exp(-float(np.mean(lp))) for lp in log_probs_list])
    probs_list = [np.exp(lp) for lp in log_probs_list]
    entropy_list = [-(p * lp) for p, lp in zip(probs_list, log_probs_list)]
    mean_entropy = np.array([float(np.mean(e)) for e in entropy_list])
    max_entropy = np.array([float(np.max(e)) for e in entropy_list])
    tail_mean_nll = np.array([float(-np.mean(lp[-5:])) for lp in log_probs_list])

    out = df[['doc_id', 'seq_len']].copy()
    out['perplexity'] = perplexity
    out['mean_entropy'] = mean_entropy
    out['max_entropy'] = max_entropy
    out['tail_mean_nll'] = tail_mean_nll
    out['sent_length'] = df['seq_len'].values
    return out
