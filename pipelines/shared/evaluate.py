"""Shared evaluation metric utilities used by all three scoring pipelines.

Provides AUROC, AUPRC, F1 (with threshold tuning on a validation split),
Expected Calibration Error (ECE), and latency computation helpers."""

from sklearn.metrics import roc_auc_score, average_precision_score, f1_score
from netcal.metrics import ECE


def compute_auroc(scores, labels):
    """Compute the Area Under the ROC Curve.

    Args:
        scores: Predicted probability scores.
        labels: Ground-truth binary labels.

    Returns:
        AUROC as a float.
    """
    return roc_auc_score(labels, scores)


def compute_auprc(scores, labels):
    """Compute the Area Under the Precision-Recall Curve.

    Args:
        scores: Predicted probability scores.
        labels: Ground-truth binary labels.

    Returns:
        AUPRC as a float.
    """
    return average_precision_score(labels, scores)


def compute_f1_at_best_threshold(val_scores, val_labels,
                                 test_scores, test_labels):
    """Find the best classification threshold on val, then compute F1 on test.

    Args:
        val_scores: Predicted scores for the validation set.
        val_labels: Ground-truth binary labels for the validation set.
        test_scores: Predicted scores for the test set.
        test_labels: Ground-truth binary labels for the test set.

    Returns:
        A tuple of (f1_score, best_threshold) for the test set.
    """
    thresholds = sorted(set(val_scores))
    best_t, best_f1 = 0.5, 0.0
    for t in thresholds:
        preds = [1 if s >= t else 0 for s in val_scores]
        f = f1_score(val_labels, preds, zero_division=0)
        if f > best_f1:
            best_f1, best_t = f, t
    test_preds = [1 if s >= best_t else 0 for s in test_scores]
    return f1_score(test_labels, test_preds, zero_division=0), best_t


def compute_ece(probs, labels, n_bins=10):
    """Compute Expected Calibration Error.

    Args:
        probs: Predicted probabilities.
        labels: Ground-truth binary labels.
        n_bins: Number of calibration bins.

    Returns:
        ECE as a float.
    """
    ece = ECE(n_bins)
    return ece.measure(probs, labels)


def compute_latency(start_time, end_time, n_queries):
    """Compute average latency per query in milliseconds.

    Args:
        start_time: Start timestamp in seconds.
        end_time: End timestamp in seconds.
        n_queries: Total number of queries processed.

    Returns:
        Average latency per query in milliseconds.
    """
    return (end_time - start_time) * 1000 / n_queries
